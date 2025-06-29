from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from extensions import db
from models.user import User, Holiday, Break
from models.classroom import Classroom
from models.college import College, CollegeHoliday, CollegeBreak
from flask_wtf import FlaskForm
from wtforms import StringField, DateField, TimeField, IntegerField, FieldList, FormField, BooleanField, SubmitField, SelectField, RadioField
from wtforms.validators import DataRequired, NumberRange
from datetime import datetime, time
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.vaud_holidays import get_vaud_holidays

setup_bp = Blueprint('setup', __name__, url_prefix='/setup')

@setup_bp.route('/colleges/search', methods=['POST'])
@login_required
def search_colleges():
    """API pour l'autocomplétion des noms de collèges"""
    data = request.get_json()
    query = data.get('query', '').strip()
    
    if len(query) < 2:
        return jsonify({'colleges': []})
    
    # Rechercher les collèges qui commencent par la requête
    colleges = College.query.filter(
        College.name.ilike(f'{query}%')
    ).order_by(College.name).limit(10).all()
    
    results = []
    for college in colleges:
        results.append({
            'id': college.id,
            'name': college.name,
            'has_config': bool(college.school_year_start)  # Indique si le collège a une config complète
        })
    
    return jsonify({'colleges': results})

@setup_bp.route('/colleges/config', methods=['POST'])
@login_required
def get_college_config():
    """API pour récupérer la configuration d'un collège"""
    data = request.get_json()
    college_name = data.get('college_name', '').strip()
    
    if not college_name:
        return jsonify({'exists': False})
    
    college = College.query.filter_by(name=college_name).first()
    
    if college and college.school_year_start:
        return jsonify({
            'exists': True,
            'has_config': True,
            'data': college.to_dict()
        })
    elif college:
        return jsonify({
            'exists': True,
            'has_config': False,
            'message': 'Ce collège existe mais n\'a pas de configuration complète'
        })
    else:
        return jsonify({
            'exists': False,
            'message': 'Nouveau collège - vous pouvez créer sa configuration'
        })

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
    college_name = StringField('Nom du collège (optionnel)', 
                              description='Entrez le nom de votre collège pour copier sa configuration ou en créer un nouveau')
    
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
        
        # Si on copie d'un collège existant, pas besoin de valider les autres champs
        if self.college_name.data:
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
        # Vérifier s'il faut copier la configuration d'un collège
        if form.college_name.data:
            college_name = form.college_name.data.strip()
            college = College.query.filter_by(name=college_name).first()
            
            if college and college.school_year_start:
                # Copier la configuration du collège existant
                current_user.school_year_start = college.school_year_start
                current_user.school_year_end = college.school_year_end
                current_user.day_start_time = college.day_start_time
                current_user.day_end_time = college.day_end_time
                current_user.period_duration = college.period_duration
                current_user.break_duration = college.break_duration
                current_user.college_name = college_name  # Associer l'utilisateur au collège
                
                try:
                    db.session.commit()
                    flash(f'Configuration copiée depuis le collège "{college_name}" avec succès !', 'success')
                    return redirect(url_for('setup.manage_holidays'))
                except Exception as e:
                    db.session.rollback()
                    flash(f'Erreur lors de la copie : {str(e)}', 'error')
            else:
                # Nouveau collège ou collège sans configuration
                # On continue avec la configuration manuelle et on créera le collège plus tard
                current_user.college_name = college_name
        
        # Configuration manuelle (sans copie)
        # Mise à jour des informations utilisateur avec les données du formulaire
        current_user.school_year_start = form.school_year_start.data
        current_user.school_year_end = form.school_year_end.data
        current_user.day_start_time = form.day_start_time.data
        current_user.day_end_time = form.day_end_time.data
        current_user.period_duration = form.period_duration.data
        current_user.break_duration = form.break_duration.data

        # Créer ou mettre à jour le collège si spécifié
        if hasattr(current_user, 'college_name') and current_user.college_name:
            college = College.query.filter_by(name=current_user.college_name).first()
            if not college:
                # Créer un nouveau collège
                college = College(
                    name=current_user.college_name,
                    created_by_id=current_user.id,
                    school_year_start=form.school_year_start.data,
                    school_year_end=form.school_year_end.data,
                    day_start_time=form.day_start_time.data,
                    day_end_time=form.day_end_time.data,
                    period_duration=form.period_duration.data,
                    break_duration=form.break_duration.data
                )
                db.session.add(college)
            elif not college.school_year_start:
                # Mettre à jour un collège existant sans configuration
                college.school_year_start = form.school_year_start.data
                college.school_year_end = form.school_year_end.data
                college.day_start_time = form.day_start_time.data
                college.day_end_time = form.day_end_time.data
                college.period_duration = form.period_duration.data
                college.break_duration = form.break_duration.data

        try:
            db.session.commit()
            flash('Configuration initiale enregistrée avec succès !', 'success')
            return redirect(url_for('setup.manage_holidays'))
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
    
    # Récupérer les informations sur les classes dont l'utilisateur est maître
    from models.class_collaboration import TeacherCollaboration, SharedClassroom, ClassMaster
    master_classroom_ids = [cm.classroom_id for cm in ClassMaster.query.filter_by(master_teacher_id=current_user.id).all()]
    
    # Récupérer aussi les classes liées via collaboration
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
                         linked_classrooms=linked_classrooms,
                         master_classroom_ids=master_classroom_ids)

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
    
    # Supprimer d'abord les enregistrements ClassMaster associés
    from models.class_collaboration import ClassMaster, SharedClassroom
    
    # Vérifier s'il y a des classes dérivées (enseignants spécialisés qui utilisent cette classe)
    shared_classrooms = SharedClassroom.query.filter_by(original_classroom_id=classroom.id).count()
    if shared_classrooms > 0:
        flash(f'Impossible de supprimer la classe "{classroom.name}" car elle est partagée avec {shared_classrooms} enseignant(s) spécialisé(s).', 'error')
        return redirect(url_for('setup.manage_classrooms'))
    
    # Supprimer les enregistrements ClassMaster
    ClassMaster.query.filter_by(classroom_id=classroom.id).delete()
    
    # Ensuite supprimer la classe
    db.session.delete(classroom)
    db.session.commit()
    flash(f'Classe "{classroom.name}" supprimée avec succès.', 'info')
    return redirect(url_for('setup.manage_classrooms'))

@setup_bp.route('/holidays', methods=['GET', 'POST'])
@login_required
def manage_holidays():
    # Vérifier si l'utilisateur appartient à un collège et s'il faut copier les vacances
    if current_user.college_name and current_user.holidays.count() == 0:
        college = College.query.filter_by(name=current_user.college_name).first()
        if college and college.holidays.count() > 0:
            # Copier les vacances du collège
            for college_holiday in college.holidays:
                user_holiday = Holiday(
                    user_id=current_user.id,
                    name=college_holiday.name,
                    start_date=college_holiday.start_date,
                    end_date=college_holiday.end_date
                )
                db.session.add(user_holiday)
            
            try:
                db.session.commit()
                flash(f'Vacances copiées depuis le collège "{college.name}" avec succès !', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Erreur lors de la copie des vacances : {str(e)}', 'error')
    
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
            
            # Si l'utilisateur appartient à un collège, ajouter aussi au niveau du collège
            if current_user.college_name:
                college = College.query.filter_by(name=current_user.college_name).first()
                if college and current_user.id == college.created_by_id:
                    # Seulement si c'est le créateur du collège
                    college_holiday = CollegeHoliday(
                        college_id=college.id,
                        name=form.name.data,
                        start_date=form.start_date.data,
                        end_date=form.end_date.data
                    )
                    db.session.add(college_holiday)
            
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
    # Vérifier si l'utilisateur appartient à un collège et s'il faut copier les pauses
    if current_user.college_name and current_user.breaks.count() == 0:
        college = College.query.filter_by(name=current_user.college_name).first()
        if college and college.breaks.count() > 0:
            # Copier les pauses du collège
            for college_break in college.breaks:
                user_break = Break(
                    user_id=current_user.id,
                    name=college_break.name,
                    start_time=college_break.start_time,
                    end_time=college_break.end_time,
                    is_major_break=college_break.is_major_break
                )
                db.session.add(user_break)
            
            try:
                db.session.commit()
                flash(f'Pauses copiées depuis le collège "{college.name}" avec succès !', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Erreur lors de la copie des pauses : {str(e)}', 'error')
    
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
            
            # Si l'utilisateur appartient à un collège, ajouter aussi au niveau du collège
            if current_user.college_name:
                college = College.query.filter_by(name=current_user.college_name).first()
                if college and current_user.id == college.created_by_id:
                    # Seulement si c'est le créateur du collège
                    college_break = CollegeBreak(
                        college_id=college.id,
                        name=form.name.data,
                        start_time=form.start_time.data,
                        end_time=form.end_time.data,
                        is_major_break=form.is_major_break.data
                    )
                    db.session.add(college_break)
            
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
    college = None
    if current_user.college_name:
        college = College.query.filter_by(name=current_user.college_name).first()
    
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
            
            # Si c'est le créateur du collège, ajouter aussi au niveau du collège
            if college and current_user.id == college.created_by_id:
                college_holiday = CollegeHoliday(
                    college_id=college.id,
                    name=holiday_data['name'],
                    start_date=holiday_data['start'],
                    end_date=holiday_data['end']
                )
                db.session.add(college_holiday)

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
