from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse
from extensions import db
from models.user import User
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Mot de passe', validators=[DataRequired()])
    submit = SubmitField('Se connecter')

class RegisterForm(FlaskForm):
    username = StringField('Nom d\'utilisateur', validators=[
        DataRequired(),
        Length(min=3, max=80, message="Le nom d'utilisateur doit contenir entre 3 et 80 caractères")
    ])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Mot de passe', validators=[
        DataRequired(),
        Length(min=6, message="Le mot de passe doit contenir au moins 6 caractères")
    ])
    password_confirm = PasswordField('Confirmer le mot de passe', validators=[
        DataRequired(),
        EqualTo('password', message='Les mots de passe doivent correspondre')
    ])
    submit = SubmitField('S\'inscrire')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Ce nom d\'utilisateur est déjà pris.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Cette adresse email est déjà enregistrée.')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Si un parent est connecté, le déconnecter
    if current_user.is_authenticated:
        from models.parent import Parent
        if isinstance(current_user, Parent):
            logout_user()
            session.clear()
        else:
            return redirect(url_for('planning.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        # Vérifier d'abord si c'est un email de parent
        from models.parent import Parent
        parent_check = Parent.query.filter_by(email=form.email.data).first()
        if parent_check:
            flash('Cet email appartient à un compte parent. Veuillez utiliser la connexion parent.', 'error')
            return render_template('auth/login.html', form=form)
        
        # Ensuite vérifier l'enseignant
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            session.clear()  # Nettoyer la session pour éviter les conflits
            session['user_type'] = 'teacher'  # Marquer comme enseignant dans la session
            login_user(user, remember=True)
            next_page = request.args.get('next')
            if not next_page or urlparse(next_page).netloc != '':
                # Déterminer où rediriger en fonction de l'état de configuration
                if not user.school_year_start or not user.day_start_time:
                    next_page = url_for('setup.initial_setup')
                elif user.classrooms.count() == 0:
                    next_page = url_for('setup.manage_classrooms')
                elif not user.setup_completed:
                    next_page = url_for('setup.manage_holidays')
                elif not user.schedule_completed:
                    next_page = url_for('schedule.weekly_schedule')
                else:
                    next_page = url_for('planning.dashboard')
            return redirect(next_page)
        else:
            flash('Email ou mot de passe incorrect.', 'error')

    return render_template('auth/login.html', form=form)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('planning.dashboard'))

    form = RegisterForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        session['user_type'] = 'teacher'  # Marquer comme enseignant dans la session
        login_user(user, remember=True)
        flash('Inscription réussie ! Bienvenue sur TeacherPlanner.', 'success')
        return redirect(url_for('setup.initial_setup'))
    else:
        # Afficher les erreurs de validation pour déboguer
        if form.errors:
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'{field}: {error}', 'error')

    return render_template('auth/register.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    session.pop('user_type', None)  # Retirer le type d'utilisateur de la session
    logout_user()
    flash('Vous avez été déconnecté avec succès.', 'info')
    return redirect(url_for('auth.login'))
