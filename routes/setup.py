from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from extensions import db
from models.user import User, Holiday, Break
from models.classroom import Classroom
from flask_wtf import FlaskForm
from wtforms import StringField, DateField, TimeField, IntegerField, FieldList, FormField, BooleanField, SubmitField, SelectField, RadioField
from wtforms.validators import DataRequired, NumberRange
from datetime import datetime, time
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.vaud_holidays import get_vaud_holidays

setup_bp = Blueprint('setup', __name__, url_prefix='/setup')

class ClassroomForm(FlaskForm):
    name = StringField('Nom de la classe', validators=[DataRequired()])
    subject = StringField('Matière enseignée', validators=[DataRequired()])
    color = StringField('Couleur', validators=[DataRequired()], default='#4F46E5')

class ClassroomSetupForm(FlaskForm):
    setup_type = RadioField('Type de configuration', 
                           choices=[
                               ('master', 'Créer mes propres classes (maître de classe)'),
                               ('specialized', 'Me lier à un enseignant existant (enseignant spécialisé)')
                           ],
                           validators=[DataRequired()],
                           default='master')
    
    # Pour la création de classes (maître)
    classrooms = FieldList(FormField(ClassroomForm), min_entries=1)
    
    # Pour la liaison (spécialisé)
    access_code = StringField('Code d\'accès')
    master_teacher_name = StringField('Nom du maître de classe')
    
    submit = SubmitField('Valider')

class HolidayForm(FlaskForm):
    name = StringField('Nom des vacances/congé', validators=[DataRequired()])
    start_date = DateField('Date de début', validators=[DataRequired()])
    end_date = DateField('Date de fin', validators=[DataRequired()])

class BreakForm(FlaskForm):
    name = StringField('Nom de la pause', validators=[DataRequired()])
    start_time = TimeField('Heure de début', validators=[DataRequired()])
    end_time = TimeField('Heure de fin', validators=[DataRequired()])
    is_major_break = BooleanField('Grande pause (pas de pause intercours après)')

class InitialSetupForm(FlaskForm):
    # Copie de configuration
    copy_from_teacher = StringField('Copier la configuration d\'un enseignant (optionnel)', 
                                   description='Entrez le nom d\'utilisateur ou email d\'un enseignant existant')
    
    # Année scolaire
    school_year_start = DateField('Début de l\'année scolaire')
    school_year_end = DateField('Fin de l\'année scolaire')

    # Horaires
    day_start_time = TimeField('Heure de début des cours')
    day_end_time = TimeField('Heure de fin des cours')
    period_duration = IntegerField('Durée d\'une période (minutes)', validators=[
        NumberRange(min=30, max=120, message="La durée doit être entre 30 et 120 minutes")
    ])
    break_duration = IntegerField('Durée de la pause intercours (minutes)', validators=[
        NumberRange(min=5, max=30, message="La pause doit être entre 5 et 30 minutes")
    ])

    submit = SubmitField('Valider la configuration')
    
    def validate(self, extra_validators=None):
        """Validation personnalisée : les champs sont requis seulement si on ne copie pas"""
        initial_validation = super().validate(extra_validators)
        
        # Si on copie d'un autre enseignant, pas besoin de valider les autres champs
        if self.copy_from_teacher.data:
            return True
            
        # Sinon, vérifier que tous les champs sont remplis
        errors = False
        if not self.school_year_start.data:
            self.school_year_start.errors.append('Ce champ est requis.')
            errors = True
        if not self.school_year_end.data:
            self.school_year_end.errors.append('Ce champ est requis.')
            errors = True
        if not self.day_start_time.data:
            self.day_start_time.errors.append('Ce champ est requis.')
            errors = True
        if not self.day_end_time.data:
            self.day_end_time.errors.append('Ce champ est requis.')
            errors = True
        if not self.period_duration.data:
            self.period_duration.errors.append('Ce champ est requis.')
            errors = True
        if not self.break_duration.data:
            self.break_duration.errors.append('Ce champ est requis.')
            errors = True
            
        return initial_validation and not errors

@setup_bp.route('/initial', methods=['GET', 'POST'])
@login_required
def initial_setup():
    form = InitialSetupForm()

    if form.validate_on_submit():
        # Vérifier s'il faut copier la configuration d'un autre enseignant
        if form.copy_from_teacher.data:
            source_teacher = User.query.filter(
                (User.username == form.copy_from_teacher.data) | 
                (User.email == form.copy_from_teacher.data)
            ).first()
            
            if source_teacher and source_teacher.id != current_user.id:
                # Copier la configuration de base
                if source_teacher.school_year_start:
                    current_user.school_year_start = source_teacher.school_year_start
                    current_user.school_year_end = source_teacher.school_year_end
                    current_user.day_start_time = source_teacher.day_start_time
                    current_user.day_end_time = source_teacher.day_end_time
                    current_user.period_duration = source_teacher.period_duration
                    current_user.break_duration = source_teacher.break_duration
                    
                    # Copier les vacances
                    for holiday in source_teacher.holidays:
                        existing_holiday = Holiday.query.filter_by(
                            user_id=current_user.id,
                            name=holiday.name,
                            start_date=holiday.start_date
                        ).first()
                        if not existing_holiday:
                            new_holiday = Holiday(
                                user_id=current_user.id,
                                name=holiday.name,
                                start_date=holiday.start_date,
                                end_date=holiday.end_date
                            )
                            db.session.add(new_holiday)
                    
                    # Copier les pauses
                    for break_obj in source_teacher.breaks:
                        existing_break = Break.query.filter_by(
                            user_id=current_user.id,
                            name=break_obj.name,
                            start_time=break_obj.start_time
                        ).first()
                        if not existing_break:
                            new_break = Break(
                                user_id=current_user.id,
                                name=break_obj.name,
                                start_time=break_obj.start_time,
                                end_time=break_obj.end_time,
                                is_major_break=break_obj.is_major_break
                            )
                            db.session.add(new_break)
                    
                    try:
                        db.session.commit()
                        flash(f'Configuration copiée depuis {source_teacher.username} avec succès !', 'success')
                        return redirect(url_for('setup.manage_classrooms'))
                    except Exception as e:
                        db.session.rollback()
                        flash(f'Erreur lors de la copie : {str(e)}', 'error')
                else:
                    flash(f'L\'enseignant {source_teacher.username} n\'a pas encore de configuration complète.', 'warning')
            else:
                flash('Enseignant non trouvé ou vous ne pouvez pas copier votre propre configuration.', 'error')
        
        # Configuration manuelle (sans copie)
        # Mise à jour des informations utilisateur avec les données du formulaire
        current_user.school_year_start = form.school_year_start.data
        current_user.school_year_end = form.school_year_end.data
        current_user.day_start_time = form.day_start_time.data
        current_user.day_end_time = form.day_end_time.data
        current_user.period_duration = form.period_duration.data
        current_user.break_duration = form.break_duration.data

        try:
            db.session.commit()
            flash('Configuration initiale enregistrée avec succès !', 'success')
            return redirect(url_for('setup.manage_holidays'))  # Nouvelle route : Vacances en premier
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la sauvegarde : {str(e)}', 'error')

    # Pré-remplir si déjà configuré
    if current_user.school_year_start:
        form.school_year_start.data = current_user.school_year_start
        form.school_year_end.data = current_user.school_year_end
        form.day_start_time.data = current_user.day_start_time
        form.day_end_time.data = current_user.day_end_time
        form.period_duration.data = current_user.period_duration
        form.break_duration.data = current_user.break_duration

    return render_template('setup/initial_setup.html', form=form)

@setup_bp.route('/check-teacher', methods=['POST'])
@login_required
def check_teacher():
    """Vérifier si un enseignant existe et retourner ses paramètres"""
    
    username_or_email = request.json.get('username_or_email', '').strip()
    
    if not username_or_email:
        return jsonify({'exists': False})
    
    teacher = User.query.filter(
        ((User.username == username_or_email) | 
         (User.email == username_or_email)) &
        (User.id != current_user.id)
    ).first()
    
    if teacher and teacher.school_year_start:
        return jsonify({
            'exists': True,
            'data': {
                'school_year_start': teacher.school_year_start.strftime('%Y-%m-%d') if teacher.school_year_start else '',
                'school_year_end': teacher.school_year_end.strftime('%Y-%m-%d') if teacher.school_year_end else '',
                'day_start_time': teacher.day_start_time.strftime('%H:%M') if teacher.day_start_time else '',
                'day_end_time': teacher.day_end_time.strftime('%H:%M') if teacher.day_end_time else '',
                'period_duration': teacher.period_duration,
                'break_duration': teacher.break_duration
            }
        })
    elif teacher:
        return jsonify({
            'exists': True,
            'incomplete': True,
            'message': f"L'enseignant {teacher.username} n'a pas encore de configuration complète."
        })
    else:
        return jsonify({'exists': False})

@setup_bp.route('/classrooms', methods=['GET', 'POST'])
@login_required
def manage_classrooms():
    """Route pour gérer les classes après la configuration initiale"""
    # Utiliser un formulaire simple pour l'ajout de classes individuelles
    form = ClassroomForm()
    
    if request.method == 'POST':
        action_type = request.form.get('action_type')
        
        if action_type == 'create':
            # Création d'une nouvelle classe
            if form.validate_on_submit():
                classroom = Classroom(
                    user_id=current_user.id,
                    name=form.name.data,
                    subject=form.subject.data,
                    color=form.color.data or '#4F46E5'
                )
                db.session.add(classroom)
                try:
                    db.session.commit()
                    flash(f'Classe "{classroom.name}" créée avec succès !', 'success')
                    return redirect(url_for('setup.manage_classrooms'))
                except Exception as e:
                    db.session.rollback()
                    flash(f'Erreur lors de la création de la classe : {str(e)}', 'error')
                    
        elif action_type == 'join':
            # Rejoindre une classe existante
            access_code = request.form.get('access_code', '').strip().upper()
            master_teacher_name = request.form.get('master_teacher_name', '').strip()
            
            if not access_code or not master_teacher_name:
                flash('Code d\'accès et nom du maître de classe requis', 'error')
            else:
                from models.class_collaboration import TeacherAccessCode, TeacherCollaboration
                
                # Rechercher le code d'accès
                code_obj = TeacherAccessCode.query.filter_by(code=access_code).first()
                
                if not code_obj or not code_obj.is_valid():
                    flash('Code d\'accès invalide ou expiré', 'error')
                else:
                    # Vérifier que le nom du maître correspond
                    master_teacher = code_obj.master_teacher
                    if (master_teacher_name.lower() != master_teacher.username.lower() and 
                        master_teacher_name.lower() != master_teacher.email.lower()):
                        flash(f'Le nom ne correspond pas au maître de classe', 'error')
                    else:
                        # Vérifier qu'il n'y a pas déjà une collaboration
                        existing_collaboration = TeacherCollaboration.query.filter_by(
                            specialized_teacher_id=current_user.id,
                            master_teacher_id=master_teacher.id
                        ).first()
                        
                        if existing_collaboration:
                            flash('Vous collaborez déjà avec cet enseignant', 'error')
                        else:
                            # Créer la collaboration
                            collaboration = TeacherCollaboration(
                                specialized_teacher_id=current_user.id,
                                master_teacher_id=master_teacher.id,
                                access_code_id=code_obj.id
                            )
                            db.session.add(collaboration)
                            
                            # Utiliser le code
                            code_obj.use_code()
                            
                            try:
                                db.session.commit()
                                flash(f'Collaboration établie avec {master_teacher.username}', 'success')
                                # Rediriger vers la sélection de classe
                                return redirect(url_for('collaboration.select_class', collaboration_id=collaboration.id))
                            except Exception as e:
                                db.session.rollback()
                                flash(f'Erreur lors de la création de la collaboration : {str(e)}', 'error')
    
    # Récupérer toutes les classes (propres et liées)
    classrooms = current_user.classrooms.all()
    
    # Récupérer aussi les classes liées via collaboration
    from models.class_collaboration import TeacherCollaboration, SharedClassroom
    collaborations = TeacherCollaboration.query.filter_by(
        specialized_teacher_id=current_user.id
    ).all()
    
    linked_classrooms = []
    for collab in collaborations:
        shared = SharedClassroom.query.filter_by(
            collaboration_id=collab.id
        ).all()
        for s in shared:
            linked_classrooms.append({
                'classroom': s.derived_classroom,
                'master_teacher': collab.master_teacher,
                'is_linked': True
            })
    
    return render_template('setup/manage_classrooms.html', 
                         form=form, 
                         classrooms=classrooms,
                         linked_classrooms=linked_classrooms)

@setup_bp.route('/classrooms/<int:classroom_id>/become-master', methods=['GET', 'POST'])
@login_required
def become_class_master(classroom_id):
    """Devenir maître d'une classe"""
    if request.method == 'GET':
        # Pour les requêtes GET, simplement rediriger
        return redirect(url_for('setup.manage_classrooms'))
    
    classroom = Classroom.query.filter_by(id=classroom_id, user_id=current_user.id).first_or_404()
    
    from models.class_collaboration import ClassMaster, TeacherAccessCode
    
    # Vérifier si l'utilisateur est déjà maître de cette classe
    existing_master = ClassMaster.query.filter_by(
        classroom_id=classroom_id,
        master_teacher_id=current_user.id,
        school_year="2024-2025"  # À adapter selon l'année courante
    ).first()
    
    if existing_master:
        flash('Vous êtes déjà maître de cette classe.', 'info')
    else:
        # Créer l'enregistrement de maître de classe
        class_master = ClassMaster(
            classroom_id=classroom_id,
            master_teacher_id=current_user.id,
            school_year="2024-2025"
        )
        db.session.add(class_master)
        
        # Créer un code d'accès pour cette classe
        access_code = TeacherAccessCode(
            master_teacher_id=current_user.id,
            code=TeacherAccessCode.generate_code(6),
            max_uses=10  # Limité à 10 utilisations
        )
        db.session.add(access_code)
        
        try:
            db.session.commit()
            flash(f'Vous êtes maintenant maître de la classe "{classroom.name}". Code d\'accès généré: {access_code.code}', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la configuration : {str(e)}', 'error')
    
    return redirect(url_for('setup.manage_classrooms'))

@setup_bp.route('/classrooms/initial', methods=['GET', 'POST'])
@login_required
def manage_classrooms_initial():
    form = ClassroomSetupForm()
    
    if form.validate_on_submit():
        if form.setup_type.data == 'master':
            # Créer des classes en tant que maître
            for classroom_form in form.classrooms:
                if classroom_form.name.data and classroom_form.subject.data:
                    classroom = Classroom(
                        user_id=current_user.id,
                        name=classroom_form.name.data,
                        subject=classroom_form.subject.data,
                        color=classroom_form.color.data or '#4F46E5'
                    )
                    db.session.add(classroom)
            
            try:
                db.session.commit()
                # Marquer la configuration comme complète
                current_user.setup_completed = True
                db.session.commit()
                flash('Classes créées avec succès !', 'success')
                return redirect(url_for('schedule.weekly_schedule'))
            except Exception as e:
                db.session.rollback()
                flash(f'Erreur lors de la création des classes : {str(e)}', 'error')
                
        elif form.setup_type.data == 'specialized':
            # Se lier à un enseignant existant
            access_code = form.access_code.data.strip().upper()
            master_teacher_name = form.master_teacher_name.data.strip()
            
            if not access_code or not master_teacher_name:
                flash('Code d\'accès et nom du maître de classe requis', 'error')
            else:
                # Utiliser la logique de collaboration existante
                from models.class_collaboration import TeacherAccessCode, TeacherCollaboration
                
                # Rechercher le code d'accès
                code_obj = TeacherAccessCode.query.filter_by(code=access_code).first()
                
                if not code_obj or not code_obj.is_valid():
                    flash('Code d\'accès invalide ou expiré', 'error')
                else:
                    # Vérifier que le nom du maître correspond
                    master_teacher = code_obj.master_teacher
                    if (master_teacher_name.lower() != master_teacher.username.lower() and 
                        master_teacher_name.lower() != master_teacher.email.lower()):
                        flash(f'Le nom ne correspond pas. Maître de classe : {master_teacher.username}', 'error')
                    else:
                        # Vérifier qu'il n'y a pas déjà une collaboration
                        existing_collaboration = TeacherCollaboration.query.filter_by(
                            specialized_teacher_id=current_user.id,
                            master_teacher_id=master_teacher.id
                        ).first()
                        
                        if existing_collaboration:
                            flash('Vous collaborez déjà avec cet enseignant', 'error')
                        else:
                            # Créer la collaboration
                            collaboration = TeacherCollaboration(
                                specialized_teacher_id=current_user.id,
                                master_teacher_id=master_teacher.id,
                                access_code_id=code_obj.id
                            )
                            db.session.add(collaboration)
                            
                            # Utiliser le code
                            code_obj.use_code()
                            
                            try:
                                db.session.commit()
                                # Marquer la configuration comme complète
                                current_user.setup_completed = True
                                db.session.commit()
                                flash(f'Collaboration établie avec {master_teacher.username}', 'success')
                                return redirect(url_for('collaboration.select_class', collaboration_id=collaboration.id))
                            except Exception as e:
                                db.session.rollback()
                                flash(f'Erreur lors de la création de la collaboration : {str(e)}', 'error')

    # Pré-remplir avec une classe par défaut si première utilisation
    if not form.classrooms.data or len(form.classrooms.data) == 0:
        form.classrooms.append_entry()

    classrooms = current_user.classrooms.all()
    return render_template('setup/manage_classrooms.html', classrooms=classrooms, form=form)

@setup_bp.route('/classrooms/<int:id>/delete', methods=['POST'])
@login_required
def delete_classroom(id):
    classroom = Classroom.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(classroom)
    db.session.commit()
    flash(f'Classe "{classroom.name}" supprimée avec succès.', 'info')
    return redirect(url_for('setup.manage_classrooms'))

@setup_bp.route('/holidays', methods=['GET', 'POST'])
@login_required
def manage_holidays():
    if request.method == 'POST':
        form = HolidayForm()
        if form.validate_on_submit():
            holiday = Holiday(
                user_id=current_user.id,
                name=form.name.data,
                start_date=form.start_date.data,
                end_date=form.end_date.data
            )
            db.session.add(holiday)
            db.session.commit()
            flash(f'Période de vacances "{holiday.name}" ajoutée avec succès !', 'success')
        return redirect(url_for('setup.manage_holidays'))

    holidays = current_user.holidays.all()
    form = HolidayForm()
    return render_template('setup/manage_holidays.html', holidays=holidays, form=form)

@setup_bp.route('/holidays/<int:id>/delete', methods=['POST'])
@login_required
def delete_holiday(id):
    holiday = Holiday.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(holiday)
    db.session.commit()
    flash(f'Période de vacances "{holiday.name}" supprimée avec succès.', 'info')
    return redirect(url_for('setup.manage_holidays'))

@setup_bp.route('/breaks', methods=['GET', 'POST'])
@login_required
def manage_breaks():
    if request.method == 'POST':
        form = BreakForm()
        if form.validate_on_submit():
            break_obj = Break(
                user_id=current_user.id,
                name=form.name.data,
                start_time=form.start_time.data,
                end_time=form.end_time.data,
                is_major_break=form.is_major_break.data
            )
            db.session.add(break_obj)
            db.session.commit()
            flash(f'Pause "{break_obj.name}" ajoutée avec succès !', 'success')
        return redirect(url_for('setup.manage_breaks'))

    breaks = current_user.breaks.all()
    form = BreakForm()
    return render_template('setup/manage_breaks.html', breaks=breaks, form=form)

@setup_bp.route('/holidays/import_vaud', methods=['POST'])
@login_required
def import_vaud_holidays():
    """Importe automatiquement les vacances scolaires vaudoises"""
    if not current_user.school_year_start:
        flash('Veuillez d\'abord configurer l\'année scolaire.', 'warning')
        return redirect(url_for('setup.initial_setup'))

    # Récupérer les vacances pour l'année scolaire
    holidays = get_vaud_holidays(current_user.school_year_start)

    if not holidays:
        flash('Aucune donnée de vacances disponible pour cette année scolaire.', 'warning')
        return redirect(url_for('setup.manage_holidays'))

    # Supprimer les anciennes vacances si demandé
    if request.form.get('replace_existing') == 'true':
        Holiday.query.filter_by(user_id=current_user.id).delete()

    # Ajouter les nouvelles vacances
    for holiday_data in holidays:
        # Vérifier si cette période existe déjà
        existing = Holiday.query.filter_by(
            user_id=current_user.id,
            name=holiday_data['name'],
            start_date=holiday_data['start']
        ).first()

        if not existing:
            holiday = Holiday(
                user_id=current_user.id,
                name=holiday_data['name'],
                start_date=holiday_data['start'],
                end_date=holiday_data['end']
            )
            db.session.add(holiday)

    try:
        db.session.commit()
        flash(f'{len(holidays)} périodes de vacances importées avec succès !', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de l\'import : {str(e)}', 'error')

    return redirect(url_for('setup.manage_holidays'))

@setup_bp.route('/validate_setup', methods=['GET', 'POST'])
@login_required
def validate_setup():
    """Valide que la configuration de base est complète"""
    # Vérifier que toutes les informations de base sont présentes
    if not current_user.school_year_start or not current_user.day_start_time:
        flash('Veuillez compléter la configuration initiale.', 'warning')
        return redirect(url_for('setup.initial_setup'))

    if current_user.classrooms.count() == 0:
        flash('Veuillez ajouter au moins une classe.', 'warning')
        return redirect(url_for('setup.manage_classrooms'))

    # Marquer la configuration de base comme complète
    current_user.setup_completed = True
    db.session.commit()

    flash('Configuration de base validée ! Créez maintenant votre horaire type.', 'success')
    return redirect(url_for('schedule.weekly_schedule'))

@setup_bp.route('/breaks/<int:id>/delete', methods=['POST'])
@login_required
def delete_break(id):
    break_obj = Break.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(break_obj)
    db.session.commit()
    flash(f'Pause "{break_obj.name}" supprimée avec succès.', 'info')
    return redirect(url_for('setup.manage_breaks'))

@setup_bp.route('/holidays/next')
@login_required 
def holidays_next():
    """Navigation vers l'étape suivante après les vacances"""
    return redirect(url_for('setup.manage_breaks'))

@setup_bp.route('/breaks/next')
@login_required
def breaks_next():
    """Navigation vers l'étape suivante après les pauses"""
    # Lors de la configuration initiale, utiliser manage_classrooms
    if not current_user.setup_completed:
        return redirect(url_for('setup.manage_classrooms'))
    else:
        return redirect(url_for('setup.manage_classrooms'))
