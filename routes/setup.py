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

@setup_bp.route('/search-teachers', methods=['POST'])
@login_required
def search_teachers():
    """API pour l'autocomplétion des noms d'enseignants"""
    data = request.get_json()
    query = data.get('query', '').strip()
    
    if len(query) < 2:
        return jsonify({'teachers': []})
    
    # Rechercher les enseignants du même collège qui commencent par la requête
    teachers = User.query.filter(
        User.id != current_user.id,  # Exclure l'utilisateur actuel
        User.college_name == current_user.college_name,  # Même collège
        (User.username.ilike(f'{query}%') | User.email.ilike(f'{query}%'))  # Commence par la requête
    ).order_by(User.username).limit(10).all()
    
    results = []
    for teacher in teachers:
        # Vérifier s'il est maître de classe
        from models.class_collaboration import ClassMaster
        is_master = ClassMaster.query.filter_by(master_teacher_id=teacher.id).first() is not None
        
        results.append({
            'id': teacher.id,
            'username': teacher.username,
            'email': teacher.email,
            'display_name': f"{teacher.username} ({teacher.email})",
            'is_master': is_master
        })
    
    return jsonify({'teachers': results})

@setup_bp.route('/api/teacher-classes/<int:teacher_id>', methods=['GET'])
@login_required
def get_teacher_classes_by_id(teacher_id):
    """API pour récupérer les classes d'un enseignant par son ID"""
    print(f"DEBUG: get_teacher_classes_by_id called with teacher_id: {teacher_id}")
    
    # Vérifier que l'enseignant existe
    teacher = User.query.get(teacher_id)
    if not teacher:
        print(f"DEBUG: Teacher with ID {teacher_id} not found")
        return jsonify({'classes': [], 'error': 'Teacher not found'}), 404
    
    print(f"DEBUG: Found teacher: {teacher.username}")
    
    # Récupérer les classes où cet enseignant est maître de classe
    from models.class_collaboration import ClassMaster
    class_masters = ClassMaster.query.filter_by(master_teacher_id=teacher_id).all()
    
    print(f"DEBUG: Found {len(class_masters)} class master entries")
    
    # Grouper par classe principale (class_group)
    from collections import defaultdict
    groups = defaultdict(list)
    
    for cm in class_masters:
        classroom = cm.classroom
        group_name = classroom.class_group or classroom.name
        groups[group_name].append(classroom)
        print(f"DEBUG: Added classroom {classroom.name} to group {group_name}")
    
    results = []
    for group_name, classrooms in groups.items():
        # Prendre la première classe pour représenter le groupe
        primary_classroom = classrooms[0]
        subjects = [c.subject for c in classrooms]
        
        results.append({
            'id': primary_classroom.id,
            'name': group_name,
            'subject': ', '.join(subjects),
            'subjects': subjects,
            'color': primary_classroom.color,
            'classroom_ids': [c.id for c in classrooms]
        })
        print(f"DEBUG: Added result: {group_name} with subjects {subjects}")
    
    print(f"DEBUG: Returning {len(results)} classes")
    return jsonify({'classes': results})

@setup_bp.route('/get-teacher-classes', methods=['POST'])
@login_required
def get_teacher_classes():
    """API pour récupérer les classes d'un maître de classe"""
    data = request.get_json()
    teacher_name = data.get('teacher_name', '').strip()
    
    print(f"DEBUG: get_teacher_classes called with teacher_name: '{teacher_name}'")
    
    if not teacher_name:
        print("DEBUG: No teacher name provided")
        return jsonify({'classes': []})
    
    # Trouver l'enseignant (recherche exacte et avec correspondance partielle)
    teacher = User.query.filter(
        (User.username.ilike(teacher_name) | 
         User.email.ilike(teacher_name) |
         User.username.ilike(f'%{teacher_name}%') | 
         User.email.ilike(f'%{teacher_name}%')),
        User.id != current_user.id
    ).first()
    
    print(f"DEBUG: Found teacher: {teacher.username if teacher else 'None'}")
    
    if not teacher:
        print("DEBUG: Teacher not found")
        return jsonify({'classes': []})
    
    # Récupérer les classes dont il est maître
    from models.class_collaboration import ClassMaster
    class_masters = ClassMaster.query.filter_by(master_teacher_id=teacher.id).all()
    
    print(f"DEBUG: Found {len(class_masters)} class_masters for teacher {teacher.username}")
    
    # Grouper par class_group
    from collections import defaultdict
    groups = defaultdict(list)
    
    for cm in class_masters:
        classroom = cm.classroom
        group_name = classroom.class_group or classroom.name
        groups[group_name].append(classroom)
        print(f"DEBUG: Added classroom {classroom.name} to group {group_name}")
    
    results = []
    for group_name, classrooms in groups.items():
        # Prendre la première classe pour représenter le groupe
        primary_classroom = classrooms[0]
        subjects = [c.subject for c in classrooms]
        
        results.append({
            'group_name': group_name,
            'classroom_id': primary_classroom.id,
            'subjects': subjects,
            'subject_list': ', '.join(subjects),
            'color': primary_classroom.color
        })
        print(f"DEBUG: Added result: {group_name} with subjects {subjects}")
    
    print(f"DEBUG: Returning {len(results)} class groups")
    return jsonify({'classes': results})

@setup_bp.route('/send-invitation', methods=['POST'])
@login_required
def send_invitation():
    """Envoyer une invitation à un maître de classe"""
    from models.teacher_invitation import TeacherInvitation
    
    data = request.get_json()
    master_teacher_name = data.get('master_teacher_name', '').strip()
    target_classroom_id = data.get('target_classroom_id')
    class_name = data.get('class_name', '').strip()
    subject = data.get('subject', '').strip()
    color = data.get('color', '#4F46E5').strip()
    message = data.get('message', '').strip()
    
    if not master_teacher_name or not target_classroom_id or not class_name or not subject:
        return jsonify({
            'success': False,
            'message': 'Nom du maître, classe cible, nom de classe et matière requis'
        })
    
    # Trouver le maître de classe
    master_teacher = User.query.filter(
        (User.username.ilike(master_teacher_name) | User.email.ilike(master_teacher_name)),
        User.id != current_user.id
    ).first()
    
    if not master_teacher:
        return jsonify({
            'success': False,
            'message': 'Enseignant introuvable'
        })
    
    # Vérifier que c'est bien un maître de classe
    from models.class_collaboration import ClassMaster
    is_master = ClassMaster.query.filter_by(master_teacher_id=master_teacher.id).first()
    if not is_master:
        return jsonify({
            'success': False,
            'message': 'Cet enseignant n\'est pas maître de classe'
        })
    
    # Vérifier qu'il n'y a pas déjà une invitation en attente
    existing_invitation = TeacherInvitation.query.filter_by(
        requesting_teacher_id=current_user.id,
        target_master_teacher_id=master_teacher.id,
        target_classroom_id=target_classroom_id,
        status='pending'
    ).first()
    
    if existing_invitation:
        return jsonify({
            'success': False,
            'message': 'Une invitation est déjà en attente pour cette classe'
        })
    
    # Créer l'invitation
    invitation = TeacherInvitation(
        requesting_teacher_id=current_user.id,
        target_master_teacher_id=master_teacher.id,
        target_classroom_id=target_classroom_id,
        proposed_class_name=class_name,
        proposed_subject=subject,
        proposed_color=color,
        message=message
    )
    
    db.session.add(invitation)
    
    # Créer temporairement la classe pour que l'enseignant puisse l'utiliser
    temp_classroom = Classroom(
        user_id=current_user.id,
        name=class_name,
        subject=subject,
        color=color,
        is_temporary=True  # Flag pour indiquer que c'est temporaire
    )
    db.session.add(temp_classroom)
    
    try:
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'Invitation envoyée à {master_teacher.username}. Vous pouvez déjà utiliser la classe "{class_name}" dans votre horaire.'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Erreur lors de l\'envoi : {str(e)}'
        })

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
                # Extraire le nom de la classe (avant le tiret)
                import re
                match = re.match(r'^([^-]+?)(?:\s*-\s*.*)?$', form.name.data.strip())
                class_group = match.group(1).strip() if match else form.name.data
                
                classroom = Classroom(
                    user_id=current_user.id,
                    name=form.name.data,
                    subject=form.subject.data,
                    color=form.color.data or '#4F46E5',
                    class_group=class_group
                )
                db.session.add(classroom)
                try:
                    db.session.commit()
                    
                    # Si c'est la première classe de ce groupe, l'enseignant devient maître de classe
                    existing_classes_in_group = Classroom.query.filter_by(
                        user_id=current_user.id,
                        class_group=class_group
                    ).filter(Classroom.id != classroom.id).count()
                    
                    if existing_classes_in_group == 0:
                        # C'est la première classe de ce groupe - marquer comme maître
                        classroom.is_class_master = True
                        db.session.commit()
                    
                    flash(f'Classe "{classroom.name}" créée avec succès !', 'success')
                    return redirect(url_for('setup.manage_classrooms'))
                except Exception as e:
                    db.session.rollback()
                    flash(f'Erreur lors de la création de la classe : {str(e)}', 'error')
                    
        elif action_type == 'join':
            # Rejoindre une classe existante avec multiples disciplines
            print("DEBUG JOIN: Form data received:", dict(request.form))
            access_code = request.form.get('access_code', '').strip().upper()
            master_teacher_name = request.form.get('master_teacher_name', '').strip()
            target_classroom_id = request.form.get('join_target_classroom_id', '').strip()
            print(f"DEBUG JOIN: access_code='{access_code}', master_teacher_name='{master_teacher_name}', target_classroom_id='{target_classroom_id}'")
            
            # Récupérer les disciplines pour le code d'accès
            join_disciplines = []
            for key in request.form.keys():
                if key.startswith('join_disciplines[') and key.endswith('][class_name]'):
                    index = key.split('[')[1].split(']')[0]
                    class_name = request.form.get(f'join_disciplines[{index}][class_name]', '').strip()
                    subject = request.form.get(f'join_disciplines[{index}][subject]', '').strip()
                    color = request.form.get(f'join_disciplines[{index}][color]', '#4F46E5').strip()
                    
                    if class_name and subject:
                        join_disciplines.append({
                            'class_name': class_name,
                            'subject': subject,
                            'color': color
                        })
            
            print(f"DEBUG JOIN: Found {len(join_disciplines)} disciplines:", join_disciplines)
            
            if not access_code or not master_teacher_name or not target_classroom_id or not join_disciplines:
                print(f"DEBUG JOIN: Missing required fields - access_code: {bool(access_code)}, master_teacher_name: {bool(master_teacher_name)}, target_classroom_id: {bool(target_classroom_id)}, join_disciplines: {bool(join_disciplines)}")
                flash('Code d\'accès, maître de classe, classe cible et au moins une discipline requis', 'error')
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
                        # Vérifier que la classe cible existe et appartient au maître
                        target_classroom = Classroom.query.filter_by(
                            id=target_classroom_id,
                            user_id=master_teacher.id
                        ).first()
                        
                        if not target_classroom:
                            flash('Classe cible introuvable', 'error')
                        else:
                            # Vérifier s'il y a déjà une collaboration ou en créer une
                            existing_collaboration = TeacherCollaboration.query.filter_by(
                                specialized_teacher_id=current_user.id,
                                master_teacher_id=master_teacher.id
                            ).first()
                            
                            if not existing_collaboration:
                                # Créer une nouvelle collaboration
                                collaboration = TeacherCollaboration(
                                    specialized_teacher_id=current_user.id,
                                    master_teacher_id=master_teacher.id,
                                    access_code_id=code_obj.id
                                )
                                db.session.add(collaboration)
                                db.session.flush()  # Pour obtenir l'ID
                            else:
                                collaboration = existing_collaboration
                            
                            # Créer les classes pour chaque discipline
                            from models.class_collaboration import SharedClassroom
                            created_classes = []
                            
                            # Déterminer le nom de classe commun (sans la matière)
                            # Ex: "11VG2 - Histoire" -> "11VG2"
                            first_class_name = join_disciplines[0]['class_name']
                            if ' - ' in first_class_name:
                                potential_class_group = first_class_name.split(' - ')[0].strip()
                            else:
                                potential_class_group = first_class_name.strip()
                            
                            # Vérifier s'il existe déjà un class_group pour cette classe dans la collaboration
                            existing_classroom_in_group = Classroom.query.join(
                                SharedClassroom, 
                                Classroom.id == SharedClassroom.derived_classroom_id
                            ).filter(
                                SharedClassroom.collaboration_id == collaboration.id,
                                SharedClassroom.original_classroom_id == target_classroom.id,
                                Classroom.user_id == current_user.id,
                                Classroom.class_group.isnot(None)
                            ).first()
                            
                            if existing_classroom_in_group:
                                # Utiliser le class_group existant pour maintenir le regroupement
                                class_group = existing_classroom_in_group.class_group
                                print(f"DEBUG JOIN: Using existing class_group: '{class_group}' from existing collaboration")
                            else:
                                # Nouveau group
                                class_group = potential_class_group
                                print(f"DEBUG JOIN: Creating new class_group: '{class_group}'")
                            
                            for discipline in join_disciplines:
                                # Vérifier si une classe similaire existe déjà
                                existing_classroom = Classroom.query.filter_by(
                                    user_id=current_user.id,
                                    name=discipline['class_name'],
                                    subject=discipline['subject'],
                                    class_group=class_group
                                ).first()
                                
                                if existing_classroom:
                                    print(f"DEBUG JOIN: Using existing classroom for {discipline['subject']}")
                                    specialized_classroom = existing_classroom
                                else:
                                    # Créer la classe spécialisée avec regroupement
                                    specialized_classroom = Classroom(
                                        user_id=current_user.id,
                                        name=discipline['class_name'],
                                        subject=discipline['subject'],
                                        color=discipline['color'],
                                        class_group=class_group  # Regrouper toutes les disciplines
                                    )
                                    db.session.add(specialized_classroom)
                                    db.session.flush()  # Pour obtenir l'ID
                                    print(f"DEBUG JOIN: Created new classroom for {discipline['subject']}")
                                
                                # Vérifier si le lien de classe partagée existe déjà
                                existing_shared = SharedClassroom.query.filter_by(
                                    collaboration_id=collaboration.id,
                                    original_classroom_id=target_classroom.id,
                                    subject=discipline['subject']
                                ).first()
                                
                                if not existing_shared:
                                    # Créer le lien de classe partagée
                                    shared_classroom = SharedClassroom(
                                        collaboration_id=collaboration.id,
                                        original_classroom_id=target_classroom.id,
                                        derived_classroom_id=specialized_classroom.id,
                                        subject=discipline['subject']
                                    )
                                    db.session.add(shared_classroom)
                                    print(f"DEBUG JOIN: Created SharedClassroom for subject {discipline['subject']}")
                                else:
                                    print(f"DEBUG JOIN: SharedClassroom already exists for subject {discipline['subject']}, skipping")
                                created_classes.append(discipline['class_name'])
                            
                            # Utiliser le code
                            code_obj.use_code()
                            
                            try:
                                db.session.commit()
                                disciplines_list = ', '.join(created_classes)
                                flash(f'Collaboration établie avec {master_teacher.username} ! Classes créées : {disciplines_list}', 'success')
                                return redirect(url_for('setup.manage_classrooms'))
                            except Exception as e:
                                db.session.rollback()
                                flash(f'Erreur lors de la création des classes : {str(e)}', 'error')
        
        elif action_type == 'invite':
            # Envoyer une invitation multi-disciplines à un maître de classe
            master_teacher_name = request.form.get('invite_master_teacher_name', '').strip()
            target_classroom_id = request.form.get('target_classroom_id', '').strip()
            message = request.form.get('invite_message', '').strip()
            
            # Récupérer les disciplines
            disciplines = []
            for key in request.form.keys():
                if key.startswith('disciplines[') and key.endswith('][class_name]'):
                    index = key.split('[')[1].split(']')[0]
                    class_name = request.form.get(f'disciplines[{index}][class_name]', '').strip()
                    subject = request.form.get(f'disciplines[{index}][subject]', '').strip()
                    color = request.form.get(f'disciplines[{index}][color]', '#4F46E5').strip()
                    
                    if class_name and subject:
                        disciplines.append({
                            'class_name': class_name,
                            'subject': subject,
                            'color': color
                        })
            
            if not master_teacher_name or not target_classroom_id or not disciplines:
                flash('Nom du maître, classe cible et au moins une discipline requis', 'error')
            else:
                from models.teacher_invitation import TeacherInvitation
                from models.invitation_classroom import InvitationClassroom
                
                # Trouver le maître de classe
                master_teacher = User.query.filter(
                    (User.username.ilike(master_teacher_name) | User.email.ilike(master_teacher_name)),
                    User.id != current_user.id
                ).first()
                
                if not master_teacher:
                    flash('Enseignant introuvable', 'error')
                else:
                    # Vérifier que c'est bien un maître de classe
                    from models.class_collaboration import ClassMaster
                    is_master = ClassMaster.query.filter_by(master_teacher_id=master_teacher.id).first()
                    if not is_master:
                        flash('Cet enseignant n\'est pas maître de classe', 'error')
                    else:
                        # Vérifier qu'il n'y a pas déjà une invitation en attente pour ce maître
                        existing_pending_invitation = TeacherInvitation.query.filter_by(
                            requesting_teacher_id=current_user.id,
                            target_master_teacher_id=master_teacher.id,
                            status='pending'
                        ).first()
                        
                        if existing_pending_invitation:
                            flash('Une invitation est déjà en attente pour cet enseignant. Attendez sa réponse avant d\'en envoyer une nouvelle.', 'error')
                        else:
                            # Créer l'invitation principale (avec la première discipline comme référence)
                            first_discipline = disciplines[0]
                            invitation = TeacherInvitation(
                                requesting_teacher_id=current_user.id,
                                target_master_teacher_id=master_teacher.id,
                                target_classroom_id=target_classroom_id,
                                proposed_class_name=first_discipline['class_name'],
                                proposed_subject=first_discipline['subject'],
                                proposed_color=first_discipline['color'],
                                message=message
                            )
                            db.session.add(invitation)
                            db.session.flush()  # Pour obtenir l'ID de l'invitation
                            
                            # Créer les enregistrements pour chaque discipline
                            discipline_names = []
                            for discipline in disciplines:
                                invitation_classroom = InvitationClassroom(
                                    invitation_id=invitation.id,
                                    target_classroom_id=target_classroom_id,
                                    proposed_class_name=discipline['class_name'],
                                    proposed_subject=discipline['subject'],
                                    proposed_color=discipline['color']
                                )
                                db.session.add(invitation_classroom)
                                discipline_names.append(discipline['subject'])
                            
                            # Créer temporairement une classe pour que l'enseignant puisse l'utiliser (première discipline)
                            temp_classroom = Classroom(
                                user_id=current_user.id,
                                name=first_discipline['class_name'],
                                subject=first_discipline['subject'],
                                color=first_discipline['color'],
                                is_temporary=True  # Flag temporaire
                            )
                            db.session.add(temp_classroom)
                            
                            try:
                                db.session.commit()
                                subject_list = ", ".join(discipline_names)
                                flash(f'Invitation envoyée à {master_teacher.username} pour enseigner {len(disciplines)} discipline(s): {subject_list}. Vous pouvez déjà utiliser vos classes dans votre horaire.', 'success')
                                return redirect(url_for('setup.manage_classrooms'))
                            except Exception as e:
                                db.session.rollback()
                                flash(f'Erreur lors de l\'envoi : {str(e)}', 'error')
    
    # Récupérer toutes les classes (propres et liées)
    classrooms = current_user.classrooms.all()
    
    # Récupérer les informations sur les classes dont l'utilisateur est maître
    from models.class_collaboration import TeacherCollaboration, SharedClassroom, ClassMaster
    from models.teacher_invitation import TeacherInvitation
    
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
    
    # Récupérer les invitations reçues (en tant que maître)
    received_invitations = TeacherInvitation.query.filter_by(
        target_master_teacher_id=current_user.id,
        status='pending'
    ).all()
    
    # Récupérer les invitations envoyées (en tant qu'enseignant spécialisé)
    sent_invitations = TeacherInvitation.query.filter_by(
        requesting_teacher_id=current_user.id
    ).filter(TeacherInvitation.status.in_(['pending', 'accepted', 'rejected'])).all()
    
    return render_template('setup/manage_classrooms.html', 
                         form=form, 
                         classrooms=classrooms,
                         linked_classrooms=linked_classrooms,
                         master_classroom_ids=master_classroom_ids,
                         received_invitations=received_invitations,
                         sent_invitations=sent_invitations)

@setup_bp.route('/api/own-classes', methods=['GET'])
@login_required
def get_own_classes():
    """API pour récupérer les classes de l'utilisateur connecté"""
    try:
        # Récupérer toutes les classes de l'utilisateur
        classrooms = Classroom.query.filter_by(user_id=current_user.id).all()
        
        classes_data = []
        for classroom in classrooms:
            classes_data.append({
                'id': classroom.id,
                'name': classroom.name,
                'subject': classroom.subject,
                'color': classroom.color,
                'student_count': len(classroom.students) if classroom.students else 0
            })
        
        return jsonify({'classes': classes_data})
    except Exception as e:
        print(f"Erreur lors de la récupération des classes: {e}")
        return jsonify({'error': 'Erreur lors de la récupération des classes'}), 500

@setup_bp.route('/api/class-students/<int:class_id>', methods=['GET'])
@login_required
def get_class_students(class_id):
    """API pour récupérer les élèves d'une classe"""
    try:
        # Vérifier que l'utilisateur a accès à cette classe
        classroom = Classroom.query.get_or_404(class_id)
        
        # Vérifier les permissions
        if classroom.user_id != current_user.id:
            # Vérifier si c'est une classe partagée
            from models.class_collaboration import SharedClassroom
            shared = SharedClassroom.query.filter_by(
                original_classroom_id=class_id
            ).join(
                SharedClassroom.collaboration
            ).filter_by(specialized_teacher_id=current_user.id).first()
            
            if not shared:
                return jsonify({'error': 'Accès non autorisé'}), 403
        
        students_data = []
        for student in classroom.students:
            students_data.append({
                'id': student.id,
                'full_name': student.full_name,
                'first_name': student.first_name,
                'last_name': student.last_name
            })
        
        return jsonify({'students': students_data})
    except Exception as e:
        print(f"Erreur lors de la récupération des élèves: {e}")
        return jsonify({'error': 'Erreur lors de la récupération des élèves'}), 500

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
        # Récupérer toutes les classes du même groupe (même class_group ou même nom)
        group_name = classroom.class_group or classroom.name
        
        # Trouver toutes les classes de l'utilisateur avec le même nom de groupe
        group_classrooms = Classroom.query.filter_by(user_id=current_user.id).filter(
            (Classroom.class_group == group_name) if classroom.class_group 
            else (Classroom.name == group_name)
        ).all()
        
        # Créer un enregistrement de maître de classe pour TOUTES les classes du groupe
        classes_made_master = []
        for group_classroom in group_classrooms:
            # Vérifier si pas déjà maître
            existing = ClassMaster.query.filter_by(
                classroom_id=group_classroom.id,
                master_teacher_id=current_user.id,
                school_year="2024-2025"
            ).first()
            
            if not existing:
                class_master = ClassMaster(
                    classroom_id=group_classroom.id,
                    master_teacher_id=current_user.id,
                    school_year="2024-2025"
                )
                db.session.add(class_master)
                classes_made_master.append(f"{group_classroom.name} ({group_classroom.subject})")
        
        if classes_made_master:
            flash(f'Vous êtes maintenant maître de classe pour : {", ".join(classes_made_master)}', 'success')
        else:
            flash('Vous étiez déjà maître de toutes les classes de ce groupe.', 'info')
        
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

@setup_bp.route('/invitations/<int:invitation_id>/respond', methods=['POST'])
@login_required
def respond_to_invitation(invitation_id):
    """Répondre à une invitation (accepter/rejeter)"""
    from models.teacher_invitation import TeacherInvitation
    from models.class_collaboration import TeacherAccessCode, TeacherCollaboration
    
    invitation = TeacherInvitation.query.filter_by(
        id=invitation_id,
        target_master_teacher_id=current_user.id,
        status='pending'
    ).first_or_404()
    
    action = request.form.get('action')
    response_message = request.form.get('response_message', '').strip()
    
    if action == 'accept':
        # Accepter l'invitation
        invitation.accept(response_message)
        
        # Vérifier si une collaboration existe déjà
        existing_collaboration = TeacherCollaboration.query.filter_by(
            specialized_teacher_id=invitation.requesting_teacher_id,
            master_teacher_id=current_user.id
        ).first()
        
        if existing_collaboration:
            # Utiliser la collaboration existante
            collaboration = existing_collaboration
            print(f"DEBUG: Utilisation de la collaboration existante {collaboration.id}")
        else:
            # Créer automatiquement un code d'accès et une collaboration
            access_code = TeacherAccessCode(
                master_teacher_id=current_user.id,
                code=TeacherAccessCode.generate_code(6),
                max_uses=1  # Code à usage unique pour cette invitation
            )
            db.session.add(access_code)
            db.session.flush()  # Pour obtenir l'ID
            
            # Créer la collaboration
            collaboration = TeacherCollaboration(
                specialized_teacher_id=invitation.requesting_teacher_id,
                master_teacher_id=current_user.id,
                access_code_id=access_code.id
            )
            db.session.add(collaboration)
            
            # Marquer le code comme utilisé
            access_code.use_code()
            print(f"DEBUG: Nouvelle collaboration créée {collaboration.id}")
        
        # S'assurer que la collaboration est bien commitée pour avoir un ID
        db.session.flush()
        
        # Traiter toutes les classes de l'invitation (multi-disciplines)
        from models.invitation_classroom import InvitationClassroom
        invitation_classrooms = InvitationClassroom.query.filter_by(invitation_id=invitation.id).all()
        
        # Si pas de disciplines spécifiques, utiliser l'ancienne logique (rétrocompatibilité)
        if not invitation_classrooms:
            invitation_classrooms = [type('obj', (object,), {
                'target_classroom_id': invitation.target_classroom_id,
                'proposed_class_name': invitation.proposed_class_name,
                'proposed_subject': invitation.proposed_subject,
                'proposed_color': invitation.proposed_color
            })()]
        
        created_classes = []
        print(f"DEBUG: Traitement de {len(invitation_classrooms)} disciplines")
        
        for idx, inv_classroom in enumerate(invitation_classrooms):
            # Pour la première classe, utiliser la classe temporaire existante
            # Pour les autres, créer de nouvelles classes
            if idx == 0:
                # Utiliser la classe temporaire existante
                temp_classroom = Classroom.query.filter_by(
                    user_id=invitation.requesting_teacher_id,
                    name=invitation.proposed_class_name,
                    is_temporary=True
                ).first()
                
                if temp_classroom:
                    temp_classroom.is_temporary = False
                    temp_classroom.color = inv_classroom.proposed_color
                    # Mettre à jour le nom avec la matière spécifique
                    temp_classroom.name = inv_classroom.proposed_class_name
                    temp_classroom.subject = inv_classroom.proposed_subject
            else:
                # Créer une nouvelle classe pour les classes supplémentaires
                temp_classroom = Classroom(
                    user_id=invitation.requesting_teacher_id,
                    name=inv_classroom.proposed_class_name,
                    subject=inv_classroom.proposed_subject,
                    color=inv_classroom.proposed_color,
                    is_temporary=False
                )
                db.session.add(temp_classroom)
                db.session.flush()  # Pour obtenir l'ID
            
            if temp_classroom:
                # Créer la liaison entre la classe de l'enseignant et celle du maître
                from models.class_collaboration import SharedClassroom
                shared_classroom = SharedClassroom(
                    collaboration_id=collaboration.id,
                    original_classroom_id=inv_classroom.target_classroom_id,  # Classe du maître
                    derived_classroom_id=temp_classroom.id,  # Classe de l'enseignant
                    subject=inv_classroom.proposed_subject
                )
                db.session.add(shared_classroom)
                
                # Mettre à jour le class_group de la classe de l'enseignant pour correspondre au maître
                target_classroom = Classroom.query.get(inv_classroom.target_classroom_id)
                if target_classroom:
                    temp_classroom.class_group = target_classroom.class_group or target_classroom.name
                
                created_classes.append(temp_classroom)
        
        # CORRECTIF: Création automatique des préférences et détection du mode centralisé pour toutes les classes
        from models.user_preferences import UserSanctionPreferences
        from models.class_collaboration import ClassMaster
        
        # Traiter les préférences pour chaque classe créée
        for temp_classroom in created_classes:
            if not temp_classroom:
                continue
                
            # Trouver la classe maître correspondante via SharedClassroom
            shared_classroom = SharedClassroom.query.filter_by(
                collaboration_id=collaboration.id,
                derived_classroom_id=temp_classroom.id
            ).first()
            
            if shared_classroom:
                master_classroom_id = shared_classroom.original_classroom_id
                
                # S'assurer que les préférences du maître existent
                master_prefs = UserSanctionPreferences.query.filter_by(
                    user_id=current_user.id,
                    classroom_id=master_classroom_id
                ).first()
                
                if not master_prefs:
                    master_prefs = UserSanctionPreferences(
                        user_id=current_user.id,
                        classroom_id=master_classroom_id,
                        display_mode='unified'  # Mode par défaut
                    )
                    db.session.add(master_prefs)
                    db.session.flush()  # Pour obtenir l'ID
                
                # Créer ou mettre à jour les préférences de l'enseignant spécialisé
                specialized_prefs = UserSanctionPreferences.query.filter_by(
                    user_id=invitation.requesting_teacher_id,
                    classroom_id=temp_classroom.id
                ).first()
                
                if not specialized_prefs:
                    specialized_prefs = UserSanctionPreferences(
                        user_id=invitation.requesting_teacher_id,
                        classroom_id=temp_classroom.id,
                        display_mode='unified',  # Mode par défaut
                        is_locked=False,
                        locked_by_user_id=None
                    )
                    db.session.add(specialized_prefs)
                
                # Vérifier si le maître est en mode centralisé et appliquer le verrouillage
                if master_prefs.display_mode == 'centralized':
                    # Verrouiller automatiquement l'enseignant spécialisé
                    specialized_prefs.display_mode = 'centralized'
                    specialized_prefs.is_locked = True
                    specialized_prefs.locked_by_user_id = current_user.id
                    
                    # Appliquer le verrouillage à toutes les classes du groupe
                    UserSanctionPreferences.lock_classroom_for_centralized_mode(
                        master_classroom_id, 
                        current_user.id
                    )
        
        try:
            db.session.commit()
            class_count = len(created_classes)
            if class_count > 1:
                flash(f'Invitation acceptée ! {invitation.requesting_teacher.username} peut maintenant accéder à {class_count} de vos classes.', 'success')
            else:
                flash(f'Invitation acceptée ! {invitation.requesting_teacher.username} peut maintenant accéder à vos classes.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de l\'acceptation : {str(e)}', 'error')
            
    elif action == 'reject':
        # Rejeter l'invitation
        invitation.reject(response_message)
        
        # Supprimer la classe temporaire
        temp_classroom = Classroom.query.filter_by(
            user_id=invitation.requesting_teacher_id,
            name=invitation.proposed_class_name,
            is_temporary=True
        ).first()
        
        if temp_classroom:
            db.session.delete(temp_classroom)
        
        try:
            db.session.commit()
            flash(f'Invitation rejetée.', 'info')
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors du rejet : {str(e)}', 'error')
    
    return redirect(url_for('planning.dashboard'))

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
    
    from models.class_collaboration import ClassMaster, SharedClassroom
    from models.student import Student
    from models.parent import ClassCode
    from models.user_preferences import UserSanctionPreferences
    
    # Vérifier si l'utilisateur est le maître de cette classe
    is_class_master = ClassMaster.query.filter_by(
        classroom_id=classroom.id, 
        master_teacher_id=current_user.id
    ).first() is not None
    
    if is_class_master:
        # CAS 1: L'utilisateur est le maître de classe - SUPPRESSION COMPLÈTE
        print(f"DEBUG DELETE: User {current_user.id} is class master - performing complete deletion")
        
        # Vérifier s'il y a des classes dérivées (enseignants spécialisés qui utilisent cette classe)
        shared_as_original = SharedClassroom.query.filter_by(original_classroom_id=classroom.id).count()
        if shared_as_original > 0:
            flash(f'Impossible de supprimer la classe "{classroom.name}" car elle est partagée avec {shared_as_original} enseignant(s) spécialisé(s).', 'error')
            return redirect(url_for('setup.manage_classrooms'))
        
        # Supprimer tous les enregistrements liés à cette classe
        group_name = classroom.class_group or classroom.name
        
        # Trouver toutes les classes de tous les utilisateurs avec le même nom de groupe
        group_classrooms = Classroom.query.filter(
            (Classroom.class_group == group_name) if classroom.class_group 
            else (Classroom.name == group_name)
        ).all()
        
        # Vider la session pour éviter les conflits avec les objets en mémoire
        db.session.expunge_all()
        
        # Supprimer tous les enregistrements pour toutes les classes du groupe
        for group_classroom in group_classrooms:
            print(f"DEBUG DELETE: Processing group classroom {group_classroom.id}")
            
            # Supprimer les préférences de sanctions EN PREMIER (pour éviter les contraintes)
            # Utiliser du SQL brut pour éviter les problèmes de relations SQLAlchemy
            db.session.execute(
                db.text("DELETE FROM user_sanction_preferences WHERE classroom_id = :classroom_id"),
                {"classroom_id": group_classroom.id}
            )
            print(f"DEBUG DELETE: Removed all sanction preferences for classroom {group_classroom.id}")
            
            # Supprimer les ClassMaster
            db.session.execute(
                db.text("DELETE FROM class_masters WHERE classroom_id = :classroom_id"),
                {"classroom_id": group_classroom.id}
            )
            
            # Supprimer les étudiants
            db.session.execute(
                db.text("DELETE FROM students WHERE classroom_id = :classroom_id"),
                {"classroom_id": group_classroom.id}
            )
            print(f"DEBUG DELETE: Removed all students for classroom {group_classroom.id}")
            
            # Supprimer les codes de classe
            db.session.execute(
                db.text("DELETE FROM class_codes WHERE classroom_id = :classroom_id"),
                {"classroom_id": group_classroom.id}
            )
            print(f"DEBUG DELETE: Removed all class codes for classroom {group_classroom.id}")
            
            # Supprimer les plannings/horaires
            db.session.execute(
                db.text("DELETE FROM schedules WHERE classroom_id = :classroom_id"),
                {"classroom_id": group_classroom.id}
            )
            print(f"DEBUG DELETE: Removed all schedules for classroom {group_classroom.id}")
            
            # Supprimer les plannings de cours
            db.session.execute(
                db.text("DELETE FROM plannings WHERE classroom_id = :classroom_id"),
                {"classroom_id": group_classroom.id}
            )
            print(f"DEBUG DELETE: Removed all plannings for classroom {group_classroom.id}")
            
            # Supprimer la classe elle-même
            db.session.execute(
                db.text("DELETE FROM classrooms WHERE id = :classroom_id"),
                {"classroom_id": group_classroom.id}
            )
            print(f"DEBUG DELETE: Removed classroom {group_classroom.id}")
        
        flash(f'Classe "{classroom.name}" et toutes ses données supprimées avec succès.', 'info')
        
    else:
        # CAS 2: L'utilisateur n'est pas le maître - DÉLIAISON SIMPLE
        print(f"DEBUG DELETE: User {current_user.id} is not class master - performing simple unlinking")
        
        # Vider la session pour éviter les conflits avec les objets en mémoire
        db.session.expunge_all()
        
        # Supprimer seulement les enregistrements SharedClassroom où cette classe est utilisée comme derived_classroom_id
        db.session.execute(
            db.text("DELETE FROM shared_classrooms WHERE derived_classroom_id = :classroom_id"),
            {"classroom_id": classroom.id}
        )
        print(f"DEBUG DELETE: Removed SharedClassroom links for classroom {classroom.id}")
        
        # Supprimer les préférences de sanctions de l'utilisateur pour cette classe
        db.session.execute(
            db.text("DELETE FROM user_sanction_preferences WHERE user_id = :user_id AND classroom_id = :classroom_id"),
            {"user_id": current_user.id, "classroom_id": classroom.id}
        )
        print(f"DEBUG DELETE: Removed user sanction preferences for classroom {classroom.id}")
        
        # Supprimer les plannings/horaires de l'utilisateur pour cette classe
        db.session.execute(
            db.text("DELETE FROM schedules WHERE classroom_id = :classroom_id"),
            {"classroom_id": classroom.id}
        )
        print(f"DEBUG DELETE: Removed schedules for classroom {classroom.id}")
        
        # Supprimer les plannings de cours de l'utilisateur pour cette classe
        db.session.execute(
            db.text("DELETE FROM plannings WHERE classroom_id = :classroom_id"),
            {"classroom_id": classroom.id}
        )
        print(f"DEBUG DELETE: Removed plannings for classroom {classroom.id}")
        
        # Supprimer uniquement la classe de l'utilisateur (pas les étudiants, codes, etc.)
        db.session.execute(
            db.text("DELETE FROM classrooms WHERE id = :classroom_id"),
            {"classroom_id": classroom.id}
        )
        print(f"DEBUG DELETE: Removed classroom {classroom.id}")
        
        flash(f'Vous avez été délié de la classe "{classroom.name}" avec succès.', 'info')
    
    db.session.commit()
    return redirect(url_for('setup.manage_classrooms'))

@setup_bp.route('/sync-class-masters')
@login_required
def sync_class_masters():
    """Synchroniser les maîtres de classe pour tous les groupes de classes"""
    from models.class_collaboration import ClassMaster
    
    try:
        # Récupérer tous les ClassMaster existants
        existing_masters = ClassMaster.query.filter_by(school_year="2024-2025").all()
        
        synced_count = 0
        for master in existing_masters:
            classroom = master.classroom
            group_name = classroom.class_group or classroom.name
            
            # Trouver toutes les classes du même groupe pour ce maître
            group_classrooms = Classroom.query.filter_by(user_id=master.master_teacher_id).filter(
                (Classroom.class_group == group_name) if classroom.class_group 
                else (Classroom.name == group_name)
            ).all()
            
            # Créer les enregistrements manquants
            for group_classroom in group_classrooms:
                existing = ClassMaster.query.filter_by(
                    classroom_id=group_classroom.id,
                    master_teacher_id=master.master_teacher_id,
                    school_year="2024-2025"
                ).first()
                
                if not existing:
                    new_master = ClassMaster(
                        classroom_id=group_classroom.id,
                        master_teacher_id=master.master_teacher_id,
                        school_year="2024-2025"
                    )
                    db.session.add(new_master)
                    synced_count += 1
        
        db.session.commit()
        flash(f'Synchronisation terminée. {synced_count} enregistrements de maître de classe créés.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la synchronisation : {str(e)}', 'error')
    
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
