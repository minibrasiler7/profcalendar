from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db
from models.parent import Parent, ParentChild, ClassCode
from models.user import User
from models.classroom import Classroom
from models.student import Student
from models.attendance import Attendance
from models.student_sanctions import StudentSanctionCount
from models.sanctions import StudentSanctionRecord, SanctionTemplate
from models.evaluation import Evaluation, EvaluationGrade
from datetime import datetime, date
import re
import os
import uuid
from functools import wraps
from werkzeug.utils import secure_filename

parent_auth_bp = Blueprint('parent_auth', __name__, url_prefix='/parent')

def get_all_linked_students(original_student_id):
    """Récupérer tous les élèves liés (original + copies dans les classes dérivées)"""
    from models.class_collaboration import SharedClassroom, StudentClassroomLink
    
    # Récupérer l'élève original
    original_student = Student.query.get(original_student_id)
    if not original_student:
        return []
    
    linked_students = [original_student]
    
    # Chercher les classes dérivées qui ont été créées à partir de la classe de cet élève
    shared_classrooms = SharedClassroom.query.filter_by(
        original_classroom_id=original_student.classroom_id
    ).all()
    
    for shared_classroom in shared_classrooms:
        # Chercher l'élève correspondant dans la classe dérivée
        derived_student = Student.query.filter_by(
            classroom_id=shared_classroom.derived_classroom_id,
            first_name=original_student.first_name,
            last_name=original_student.last_name
        ).first()
        
        if derived_student:
            linked_students.append(derived_student)
    
    return linked_students

# Décorateur pour vérifier que c'est bien un parent qui est connecté
def parent_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not isinstance(current_user, Parent):
            # Pour les requêtes AJAX, retourner une erreur JSON
            if request.is_json or request.headers.get('Accept') == 'application/json':
                return jsonify({'error': 'Accès réservé aux parents'}), 403
            
            flash('Accès réservé aux parents', 'error')
            return redirect(url_for('parent_auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@parent_auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Connexion des parents"""
    # Si un utilisateur est déjà connecté, le déconnecter d'abord
    if current_user.is_authenticated:
        logout_user()
        session.pop('user_type', None)
    
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        email = data.get('email', '').strip().lower()
        password = data.get('password', '').strip()
        
        if not email or not password:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Email et mot de passe requis'}), 400
            flash('Email et mot de passe requis', 'error')
            return render_template('parent/login.html')
        
        # Rechercher le parent d'abord
        parent = Parent.query.filter_by(email=email).first()
        
        if parent and parent.check_password(password):
            # C'est bien un parent avec le bon mot de passe
            # Connexion réussie
            session.clear()  # Nettoyer la session pour éviter les conflits
            session['user_type'] = 'parent'  # Marquer comme parent dans la session
            login_user(parent, remember=True)
            parent.last_login = datetime.utcnow()
            db.session.commit()
            
            if request.is_json:
                return jsonify({'success': True, 'redirect': url_for('parent_auth.dashboard')})
            
            # Rediriger selon l'état du parent
            if not parent.teacher_id:
                return redirect(url_for('parent_auth.link_teacher'))
            else:
                return redirect(url_for('parent_auth.dashboard'))
        else:
            # Vérifier si c'est peut-être un enseignant qui essaie de se connecter ici
            teacher_check = User.query.filter_by(email=email).first()
            if teacher_check:
                if request.is_json:
                    return jsonify({'success': False, 'message': 'Cet email appartient à un compte enseignant. Veuillez utiliser la connexion enseignant.'}), 400
                flash('Cet email appartient à un compte enseignant. Veuillez utiliser la connexion enseignant.', 'error')
            else:
                if request.is_json:
                    return jsonify({'success': False, 'message': 'Email ou mot de passe incorrect'}), 401
                flash('Email ou mot de passe incorrect', 'error')
    
    return render_template('parent/login.html')

@parent_auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Inscription des parents"""
    # Si un utilisateur est déjà connecté, le déconnecter d'abord
    if current_user.is_authenticated:
        logout_user()
        session.pop('user_type', None)
    
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        email = data.get('email', '').strip().lower()
        password = data.get('password', '').strip()
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        
        # Validation
        if not email or not password:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Email et mot de passe requis'}), 400
            flash('Email et mot de passe requis', 'error')
            return render_template('parent/register.html')
        
        # Validation email
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email):
            if request.is_json:
                return jsonify({'success': False, 'message': 'Format d\'email invalide'}), 400
            flash('Format d\'email invalide', 'error')
            return render_template('parent/register.html')
        
        # Validation mot de passe
        if len(password) < 6:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Le mot de passe doit contenir au moins 6 caractères'}), 400
            flash('Le mot de passe doit contenir au moins 6 caractères', 'error')
            return render_template('parent/register.html')
        
        # Vérifier si l'email existe déjà
        if Parent.query.filter_by(email=email).first():
            if request.is_json:
                return jsonify({'success': False, 'message': 'Un compte avec cet email existe déjà'}), 400
            flash('Un compte avec cet email existe déjà', 'error')
            return render_template('parent/register.html')
        
        try:
            # Créer le nouveau parent
            parent = Parent(
                email=email,
                first_name=first_name,
                last_name=last_name
            )
            parent.set_password(password)
            
            db.session.add(parent)
            db.session.commit()
            
            # Connexion automatique
            session['user_type'] = 'parent'  # Marquer comme parent dans la session
            login_user(parent, remember=True)
            parent.last_login = datetime.utcnow()
            db.session.commit()
            
            if request.is_json:
                return jsonify({'success': True, 'redirect': url_for('parent_auth.link_teacher')})
            
            flash('Compte créé avec succès !', 'success')
            return redirect(url_for('parent_auth.link_teacher'))
            
        except Exception as e:
            db.session.rollback()
            if request.is_json:
                return jsonify({'success': False, 'message': 'Erreur lors de la création du compte'}), 500
            flash('Erreur lors de la création du compte', 'error')
    
    return render_template('parent/register.html')

@parent_auth_bp.route('/link-teacher', methods=['GET', 'POST'])
@parent_required
def link_teacher():
    """Lier le parent à un enseignant et une classe"""
    if current_user.teacher_id:
        return redirect(url_for('parent_auth.dashboard'))
    
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        teacher_name = data.get('teacher_name', '').strip()
        class_code = data.get('class_code', '').strip().upper()
        
        if not teacher_name or not class_code:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Nom de l\'enseignant et code de classe requis'}), 400
            flash('Nom de l\'enseignant et code de classe requis', 'error')
            return render_template('parent/link_teacher.html')
        
        try:
            # Rechercher le code de classe
            class_code_obj = ClassCode.query.filter_by(code=class_code, is_active=True).first()
            
            if not class_code_obj:
                if request.is_json:
                    return jsonify({'success': False, 'message': 'Code de classe introuvable'}), 404
                flash('Code de classe introuvable', 'error')
                return render_template('parent/link_teacher.html')
            
            # Vérifier si le nom de l'enseignant correspond
            teacher = class_code_obj.user
            
            # Accepter soit le username, soit l'email de l'enseignant
            teacher_name_lower = teacher_name.lower()
            if (teacher_name_lower != teacher.username.lower() and 
                teacher_name_lower != teacher.email.lower()):
                if request.is_json:
                    return jsonify({'success': False, 'message': f'Le nom de l\'enseignant ne correspond pas. Enseignant de cette classe : {teacher.username}'}), 400
                flash(f'Le nom de l\'enseignant ne correspond pas. Enseignant de cette classe : {teacher.username}', 'error')
                return render_template('parent/link_teacher.html')
            
            # Lier le parent à l'enseignant
            current_user.teacher_name = teacher_name
            current_user.class_code = class_code
            current_user.teacher_id = teacher.id
            
            # Rechercher et lier automatiquement les enfants
            children_linked = link_children_automatically(current_user, class_code_obj.classroom_id)
            
            if children_linked > 0:
                current_user.is_verified = True
                message = f'Liaison réussie ! {children_linked} enfant(s) trouvé(s) et lié(s) automatiquement.'
            else:
                message = 'Liaison réussie ! Aucun enfant trouvé avec votre email. Veuillez contacter l\'enseignant.'
            
            db.session.commit()
            
            if request.is_json:
                return jsonify({'success': True, 'message': message, 'redirect': url_for('parent_auth.dashboard')})
            
            flash(message, 'success')
            return redirect(url_for('parent_auth.dashboard'))
            
        except Exception as e:
            db.session.rollback()
            if request.is_json:
                return jsonify({'success': False, 'message': 'Erreur lors de la liaison'}), 500
            flash('Erreur lors de la liaison', 'error')
    
    return render_template('parent/link_teacher.html')

def link_children_automatically(parent, classroom_id):
    """Lier automatiquement les enfants selon l'email du parent"""
    children_linked = 0
    
    # Rechercher les élèves avec l'email du parent (mère ou père)
    students = Student.query.filter(
        Student.classroom_id == classroom_id,
        db.or_(
            Student.parent_email_mother == parent.email,
            Student.parent_email_father == parent.email
        )
    ).all()
    
    for student in students:
        # Vérifier si la liaison n'existe pas déjà
        existing_link = ParentChild.query.filter_by(
            parent_id=parent.id,
            student_id=student.id
        ).first()
        
        if not existing_link:
            # Déterminer le type de relation
            relationship = 'parent'  # Par défaut
            if student.parent_email_mother == parent.email:
                relationship = 'mother'
            elif student.parent_email_father == parent.email:
                relationship = 'father'
            
            # Créer la liaison
            parent_child = ParentChild(
                parent_id=parent.id,
                student_id=student.id,
                relationship=relationship,
                is_primary=True
            )
            db.session.add(parent_child)
            children_linked += 1
    
    return children_linked

@parent_auth_bp.route('/dashboard')
@parent_required
def dashboard():
    """Tableau de bord des parents"""
    if not current_user.teacher_id:
        return redirect(url_for('parent_auth.link_teacher'))
    
    # Récupérer les enfants du parent
    children = db.session.query(Student, ParentChild).join(
        ParentChild, Student.id == ParentChild.student_id
    ).filter(
        ParentChild.parent_id == current_user.id
    ).all()
    
    # Récupérer les justifications d'absence soumises par ce parent
    from models.absence_justification import AbsenceJustification
    justifications = AbsenceJustification.query.filter_by(
        parent_id=current_user.id
    ).order_by(AbsenceJustification.created_at.desc()).limit(10).all()
    
    return render_template('parent/dashboard.html', children=children, justifications=justifications)

@parent_auth_bp.route('/logout')
@parent_required
def logout():
    """Déconnexion des parents"""
    session.pop('user_type', None)  # Retirer le type d'utilisateur de la session
    logout_user()
    flash('Vous avez été déconnecté', 'info')
    return redirect(url_for('parent_auth.login'))

@parent_auth_bp.route('/student/<int:student_id>/attendance')
@parent_required
def get_student_attendance(student_id):
    """Récupérer les données de présence d'un élève"""
    # Vérifier que l'élève appartient bien au parent
    parent_child = ParentChild.query.filter_by(
        parent_id=current_user.id,
        student_id=student_id
    ).first()
    
    if not parent_child:
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    student = Student.query.get_or_404(student_id)
    
    # Récupérer tous les élèves liés (original + copies dans les classes dérivées)
    linked_students = get_all_linked_students(student_id)
    linked_student_ids = [s.id for s in linked_students]
    
    # Récupérer uniquement les absences et retards de TOUS les élèves liés
    attendances = Attendance.query.filter(Attendance.student_id.in_(linked_student_ids))\
        .filter(Attendance.status.in_(['absent', 'late']))\
        .order_by(Attendance.date.desc(), Attendance.period_number)\
        .limit(100).all()  # Augmenter la limite car on a plus de données
    
    # Grouper par date
    attendance_by_date = {}
    for attendance in attendances:
        date_key = attendance.date.strftime('%d/%m/%Y')
        if date_key not in attendance_by_date:
            attendance_by_date[date_key] = {
                'date': date_key,
                'periods': [],
                'general_note': ''
            }
        
        # Récupérer le nom de la classe/matière
        classroom_name = attendance.classroom.name if attendance.classroom else 'Classe inconnue'
        subject = attendance.classroom.subject if attendance.classroom else ''
        
        # Ajouter la période avec info de la classe
        attendance_by_date[date_key]['periods'].append({
            'period': str(attendance.period_number),
            'status': attendance.status,
            'arrival_time': None,  # Le modèle n'a pas ce champ spécifique
            'note': attendance.comment or '',
            'late_minutes': attendance.late_minutes if attendance.status == 'late' else None,
            'classroom': classroom_name,
            'subject': subject
        })
        
        # Ajouter le commentaire général si il y en a un et qu'il n'est pas déjà ajouté
        if attendance.comment and not attendance_by_date[date_key]['general_note']:
            attendance_by_date[date_key]['general_note'] = attendance.comment
    
    # Convertir en liste et trier par date (plus récent en premier)
    from datetime import datetime as dt
    attendance_data = list(attendance_by_date.values())
    attendance_data.sort(key=lambda x: dt.strptime(x['date'], '%d/%m/%Y'), reverse=True)
    
    return jsonify({
        'student_name': f"{student.first_name} {student.last_name}",
        'attendance_data': attendance_data
    })

@parent_auth_bp.route('/student/<int:student_id>/grades')
@parent_required
def get_student_grades(student_id):
    """Récupérer les notes d'un élève"""
    # Vérifier que l'élève appartient bien au parent
    parent_child = ParentChild.query.filter_by(
        parent_id=current_user.id,
        student_id=student_id
    ).first()
    
    if not parent_child:
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    student = Student.query.get_or_404(student_id)
    
    # Récupérer tous les élèves liés (original + copies dans les classes dérivées)
    linked_students = get_all_linked_students(student_id)
    linked_student_ids = [s.id for s in linked_students]
    
    # Récupérer toutes les notes de TOUS les élèves liés avec les évaluations et classes
    grades_query = db.session.query(EvaluationGrade, Evaluation, Classroom).join(
        Evaluation, EvaluationGrade.evaluation_id == Evaluation.id
    ).join(
        Classroom, Evaluation.classroom_id == Classroom.id
    ).filter(
        EvaluationGrade.student_id.in_(linked_student_ids),
        EvaluationGrade.points.isnot(None)  # Seulement les notes attribuées
    ).order_by(Classroom.subject, Evaluation.date).all()
    
    # Organiser les données pour un tableau unique avec toutes les disciplines
    subjects_data = {}
    all_evaluations = []  # Pour tracker toutes les évaluations uniques
    
    for grade, evaluation, classroom in grades_query:
        subject = classroom.subject
        
        if subject not in subjects_data:
            subjects_data[subject] = {
                'subject_name': subject,
                'classroom_name': classroom.name,
                'grades': {},  # grades par evaluation_id
                'total_significatif': 0,
                'count_significatif': 0,
                'total_ta': 0,
                'count_ta': 0
            }
        
        # Ajouter l'évaluation à la liste globale si elle n'existe pas
        if not any(e['id'] == evaluation.id for e in all_evaluations):
            all_evaluations.append({
                'id': evaluation.id,
                'title': evaluation.title,
                'type': evaluation.type,
                'ta_group_name': evaluation.ta_group_name,
                'date': evaluation.date,
                'subject': subject,
                'classroom_name': classroom.name
            })
        
        # Ajouter la note de l'élève pour cette évaluation
        subjects_data[subject]['grades'][evaluation.id] = round(grade.get_note_swiss(), 2) if grade.get_note_swiss() else None
        
        # Calculer pour les moyennes
        if grade.get_note_swiss():
            if evaluation.type == 'significatif':
                subjects_data[subject]['total_significatif'] += grade.get_note_swiss()
                subjects_data[subject]['count_significatif'] += 1
            elif evaluation.type == 'ta':
                subjects_data[subject]['total_ta'] += grade.get_note_swiss()
                subjects_data[subject]['count_ta'] += 1
    
    # Trier les évaluations par date
    all_evaluations.sort(key=lambda x: x['date'])
    
    # Calculer les moyennes pour chaque discipline
    for subject, data in subjects_data.items():
        # Calculer les moyennes
        avg_significatif = data['total_significatif'] / data['count_significatif'] if data['count_significatif'] > 0 else None
        avg_ta = data['total_ta'] / data['count_ta'] if data['count_ta'] > 0 else None
        
        # Moyenne générale (60% significatif, 40% TA)
        if avg_significatif is not None and avg_ta is not None:
            avg_general = round(avg_significatif * 0.6 + avg_ta * 0.4, 2)
        elif avg_significatif is not None:
            avg_general = avg_significatif
        elif avg_ta is not None:
            avg_general = avg_ta
        else:
            avg_general = None
        
        # Ajouter les moyennes aux données de la matière
        data['averages'] = {
            'significatif': round(avg_significatif, 2) if avg_significatif else None,
            'ta': round(avg_ta, 2) if avg_ta else None,
            'general': avg_general
        }
    
    return jsonify({
        'student_name': f"{student.first_name} {student.last_name}",
        'subjects_data': subjects_data,
        'all_evaluations': all_evaluations,
        'has_grades': len(subjects_data) > 0
    })

@parent_auth_bp.route('/student/<int:student_id>/sanctions')
@parent_required
def get_student_sanctions(student_id):
    """Récupérer les sanctions d'un élève avec un rapport des coches par discipline"""
    try:
        # Vérifier que l'élève appartient bien au parent
        parent_child = ParentChild.query.filter_by(
            parent_id=current_user.id,
            student_id=student_id
        ).first()
        
        if not parent_child:
            return jsonify({'error': 'Accès non autorisé'}), 403
        
        student = Student.query.get_or_404(student_id)
        
        # Récupérer tous les élèves liés (original + copies dans les classes dérivées)
        linked_students = get_all_linked_students(student_id)
        linked_student_ids = [s.id for s in linked_students]
        
        # Récupérer les compteurs de coches pour TOUS les élèves liés
        sanction_counts = StudentSanctionCount.query.filter(
            StudentSanctionCount.student_id.in_(linked_student_ids)
        ).filter(
            StudentSanctionCount.check_count > 0
        ).all()
        
        # Organiser par discipline - Obtenir toutes les classes de TOUS les élèves liés
        student_classrooms = Classroom.query.join(Student).filter(Student.id.in_(linked_student_ids)).all()
        
        sanctions_by_subject = {}
        total_checks = 0
        
        for classroom in student_classrooms:
            subject = classroom.subject
            
            # Récupérer les templates de sanctions actifs pour cette classe
            from models.sanctions import ClassroomSanctionImport
            classroom_imports = ClassroomSanctionImport.query.filter_by(
                classroom_id=classroom.id,
                is_active=True
            ).all()
            
            if subject not in sanctions_by_subject:
                sanctions_by_subject[subject] = {
                    'subject_name': subject,
                    'classroom_name': classroom.name,
                    'total_checks': 0,
                    'templates': []
                }
            
            # Pour chaque template de cette classe, vérifier s'il y a des coches pour cet élève
            for import_link in classroom_imports:
                template = SanctionTemplate.query.get(import_link.template_id)
                if not template:
                    continue
                
                # Chercher le compteur de coches pour cet élève et ce template
                student_count = StudentSanctionCount.query.filter_by(
                    student_id=student_id,
                    template_id=template.id
                ).first()
                
                check_count = student_count.check_count if student_count else 0
                
                sanctions_by_subject[subject]['templates'].append({
                    'template_name': template.name,
                    'check_count': check_count,
                    'template_id': template.id
                })
                
                if check_count > 0:
                    sanctions_by_subject[subject]['total_checks'] += check_count
                    total_checks += check_count
        
        return jsonify({
            'student_name': f"{student.first_name} {student.last_name}",
            'sanctions_by_subject': sanctions_by_subject,
            'total_checks': total_checks,
            'has_sanctions': total_checks > 0
        })
        
    except Exception as e:
        print(f"Erreur dans get_student_sanctions: {e}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@parent_auth_bp.route('/teacher-periods/<int:student_id>')
@parent_required
def get_teacher_periods(student_id):
    """Récupérer les périodes de l'enseignant pour un élève"""
    print(f"get_teacher_periods appelé pour student_id: {student_id}")
    print(f"current_user: {current_user}")
    print(f"current_user.is_authenticated: {current_user.is_authenticated}")
    
    try:
        # Vérifier que l'élève appartient bien au parent
        parent_child = ParentChild.query.filter_by(
            parent_id=current_user.id,
            student_id=student_id
        ).first()
        
        if not parent_child:
            return jsonify({'error': 'Accès non autorisé'}), 403
        
        student = Student.query.get_or_404(student_id)
        
        # Récupérer l'enseignant via la classe de l'élève (plus précis que le parent)
        if not student.classroom or not student.classroom.teacher:
            return jsonify({'error': 'Classe ou enseignant non trouvé pour cet élève'}), 404
        
        teacher_id = student.classroom.teacher.id
        
        # Récupérer l'enseignant pour sa configuration
        from models.user import User
        teacher = User.query.get(teacher_id)
        
        if not teacher:
            return jsonify({'error': 'Enseignant non trouvé'}), 404
        
        # Utiliser la même logique que dans schedule.py pour calculer les périodes
        from datetime import timedelta
        
        def calculate_periods(user):
            """Calcule les périodes en fonction de la configuration de l'utilisateur"""
            periods = []
            start_time = datetime.combine(datetime.today(), user.day_start_time)
            end_time = datetime.combine(datetime.today(), user.day_end_time)

            # Récupérer les pauses majeures
            major_breaks = [(b.start_time, b.end_time) for b in user.breaks.filter_by(is_major_break=True).all()]

            current_time = start_time
            period_number = 1

            while current_time < end_time:
                period_end = current_time + timedelta(minutes=user.period_duration)

                # Vérifier si cette période chevauche avec une pause majeure
                period_start_time = current_time.time()
                period_end_time = period_end.time()

                is_before_major_break = False
                for break_start, break_end in major_breaks:
                    if period_end_time >= break_start and period_start_time < break_start:
                        # La période se termine au début de la pause majeure
                        period_end = datetime.combine(datetime.today(), break_start)
                        is_before_major_break = True
                        break

                periods.append({
                    'number': period_number,
                    'start': current_time.time(),
                    'end': period_end.time()
                })

                # Calculer le prochain début de période
                if is_before_major_break:
                    # Trouver la fin de la pause majeure
                    for break_start, break_end in major_breaks:
                        if period_end.time() == break_start:
                            current_time = datetime.combine(datetime.today(), break_end)
                            break
                else:
                    # Ajouter la pause intercours normale
                    current_time = period_end + timedelta(minutes=user.break_duration)

                period_number += 1

                # Vérifier si on dépasse la fin de journée
                if current_time >= end_time:
                    break

            return periods
        
        # Calculer toutes les périodes possibles
        calculated_periods = calculate_periods(teacher)
        
        periods = []
        for period in calculated_periods:
            periods.append({
                'period_number': period['number'],
                'start_time': period['start'].strftime('%H:%M'),
                'end_time': period['end'].strftime('%H:%M')
            })
        
        # Si aucune période calculée, utiliser les données de la table schedules
        if not periods:
            from models.schedule import Schedule
            schedules = Schedule.query.filter_by(user_id=teacher_id).order_by(Schedule.period_number).all()
            
            period_dict = {}
            for schedule in schedules:
                if schedule.period_number not in period_dict:
                    period_dict[schedule.period_number] = {
                        'period_number': schedule.period_number,
                        'start_time': schedule.start_time.strftime('%H:%M'),
                        'end_time': schedule.end_time.strftime('%H:%M')
                    }
            
            periods = list(period_dict.values())
        
        # Si toujours pas de périodes, utiliser des périodes par défaut
        if not periods:
            periods = [
                {'period_number': 1, 'start_time': '07:40', 'end_time': '08:25'},
                {'period_number': 2, 'start_time': '08:30', 'end_time': '09:15'},
                {'period_number': 3, 'start_time': '09:20', 'end_time': '10:05'},
                {'period_number': 4, 'start_time': '10:25', 'end_time': '11:10'},
                {'period_number': 5, 'start_time': '11:15', 'end_time': '12:00'},
                {'period_number': 6, 'start_time': '13:00', 'end_time': '13:45'},
                {'period_number': 7, 'start_time': '13:50', 'end_time': '14:35'},
                {'period_number': 8, 'start_time': '14:45', 'end_time': '15:30'}
            ]
        
        # Déterminer quelles périodes sont le matin vs l'après-midi (avant/après 12h)
        for period in periods:
            start_hour = int(period['start_time'].split(':')[0])
            period['is_morning'] = start_hour < 12
        
        return jsonify({
            'periods': periods,
            'student_name': f"{student.first_name} {student.last_name}"
        })
    
    except Exception as e:
        import traceback
        print(f"Erreur dans get_teacher_periods: {e}")
        print(f"Traceback complet:")
        traceback.print_exc()
        return jsonify({'error': f'Erreur lors de la récupération des périodes: {str(e)}'}), 500

@parent_auth_bp.route('/justify-absence', methods=['POST'])
@parent_required
def justify_absence():
    """Traiter une justification d'absence soumise par un parent"""
    try:
        student_id = request.form.get('student_id')
        
        # Vérifier que l'élève appartient bien au parent
        parent_child = ParentChild.query.filter_by(
            parent_id=current_user.id,
            student_id=student_id
        ).first()
        
        if not parent_child:
            return jsonify({'success': False, 'message': 'Accès non autorisé'}), 403
        
        # Récupérer les données du formulaire
        absence_date_str = request.form.get('absence_date')
        reason_type = request.form.get('reason')
        other_reason_text = request.form.get('other_reason_text', '')
        
        # Champs pour les dispenses
        dispense_subject = request.form.get('dispense_subject', '')
        dispense_start_str = request.form.get('dispense_start', '')
        dispense_end_str = request.form.get('dispense_end', '')
        
        # Périodes
        selected_periods = request.form.getlist('periods[]')
        
        # Validation des champs obligatoires
        if not absence_date_str or not reason_type:
            return jsonify({'success': False, 'message': 'Date et motif requis'}), 400
        
        if not selected_periods:
            return jsonify({'success': False, 'message': 'Au moins une période requise'}), 400
        
        # Conversion des dates
        try:
            absence_date = datetime.strptime(absence_date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'message': 'Format de date invalide'}), 400
        
        dispense_start_date = None
        dispense_end_date = None
        if dispense_start_str:
            try:
                dispense_start_date = datetime.strptime(dispense_start_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        if dispense_end_str:
            try:
                dispense_end_date = datetime.strptime(dispense_end_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        # Construire la liste des périodes
        periods = []
        for period_num in selected_periods:
            periods.append({
                'period': int(period_num)
            })
        
        # Gestion du fichier uploadé
        justification_file = None
        if 'justification_file' in request.files:
            file = request.files['justification_file']
            if file and file.filename:
                # Créer le dossier s'il n'existe pas
                upload_folder = os.path.join('uploads', 'justifications')
                os.makedirs(upload_folder, exist_ok=True)
                
                # Sécuriser le nom de fichier et ajouter un UUID
                filename = secure_filename(file.filename)
                file_extension = os.path.splitext(filename)[1]
                unique_filename = f"{uuid.uuid4()}{file_extension}"
                
                file_path = os.path.join(upload_folder, unique_filename)
                file.save(file_path)
                justification_file = unique_filename
        
        # Créer la justification
        from models.absence_justification import AbsenceJustification
        
        justification = AbsenceJustification(
            student_id=student_id,
            parent_id=current_user.id,
            absence_date=absence_date,
            reason_type=reason_type,
            other_reason_text=other_reason_text if reason_type == 'autre' else None,
            dispense_subject=dispense_subject if reason_type == 'dispense' else None,
            dispense_start_date=dispense_start_date,
            dispense_end_date=dispense_end_date,
            justification_file=justification_file
        )
        
        # Sauvegarder les périodes
        justification.set_periods_list(periods)
        
        db.session.add(justification)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Justification envoyée avec succès. L\'enseignant sera notifié.',
            'justification_id': justification.id
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Erreur lors de l'envoi de la justification: {e}")
        return jsonify({'success': False, 'message': 'Erreur lors de l\'envoi de la justification'}), 500

@parent_auth_bp.route('/add-child', methods=['GET', 'POST'])
@parent_required
def add_child():
    """Ajouter un enfant supplémentaire (possiblement dans une autre classe)"""
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        teacher_name = data.get('teacher_name', '').strip()
        class_code = data.get('class_code', '').strip().upper()
        
        if not teacher_name or not class_code:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Nom de l\'enseignant et code de classe requis'}), 400
            flash('Nom de l\'enseignant et code de classe requis', 'error')
            return render_template('parent/add_child.html')
        
        try:
            # Rechercher le code de classe
            class_code_obj = ClassCode.query.filter_by(code=class_code, is_active=True).first()
            
            if not class_code_obj:
                if request.is_json:
                    return jsonify({'success': False, 'message': 'Code de classe introuvable'}), 404
                flash('Code de classe introuvable', 'error')
                return render_template('parent/add_child.html')
            
            # Vérifier si le nom de l'enseignant correspond
            teacher = class_code_obj.user
            
            # Accepter soit le username, soit l'email de l'enseignant
            teacher_name_lower = teacher_name.lower()
            if (teacher_name_lower != teacher.username.lower() and 
                teacher_name_lower != teacher.email.lower()):
                if request.is_json:
                    return jsonify({'success': False, 'message': f'Le nom de l\'enseignant ne correspond pas. Enseignant de cette classe : {teacher.username}'}), 400
                flash(f'Le nom de l\'enseignant ne correspond pas. Enseignant de cette classe : {teacher.username}', 'error')
                return render_template('parent/add_child.html')
            
            # Rechercher et lier automatiquement les enfants dans cette nouvelle classe
            children_linked = link_children_automatically(current_user, class_code_obj.classroom_id)
            
            if children_linked > 0:
                message = f'Liaison réussie ! {children_linked} enfant(s) trouvé(s) et lié(s) automatiquement dans la classe de {teacher.username}.'
            else:
                message = f'Liaison réussie avec la classe de {teacher.username} ! Aucun enfant trouvé avec votre email dans cette classe. Veuillez contacter l\'enseignant.'
            
            db.session.commit()
            
            if request.is_json:
                return jsonify({'success': True, 'message': message, 'redirect': url_for('parent_auth.dashboard')})
            
            flash(message, 'success')
            return redirect(url_for('parent_auth.dashboard'))
            
        except Exception as e:
            db.session.rollback()
            print(f"Erreur lors de l'ajout d'enfant: {e}")
            if request.is_json:
                return jsonify({'success': False, 'message': 'Erreur lors de la liaison'}), 500
            flash('Erreur lors de la liaison', 'error')
    
    return render_template('parent/add_child.html')

@parent_auth_bp.route('/student/<int:student_id>/teachers')
@parent_required
def get_student_teachers(student_id):
    """Récupérer la liste des enseignants d'un élève"""
    try:
        # Vérifier que l'élève appartient bien au parent
        parent_child = ParentChild.query.filter_by(
            parent_id=current_user.id,
            student_id=student_id
        ).first()
        
        if not parent_child:
            return jsonify({'error': 'Accès non autorisé'}), 403
        
        student = Student.query.get_or_404(student_id)
        
        # Récupérer l'enseignant maître de classe
        main_teacher = student.classroom.teacher if student.classroom else None
        
        # Récupérer tous les enseignants spécialisés de cette classe
        from models.class_collaboration import SharedClassroom
        
        # Trouver les classes dérivées de la classe principale
        derived_classrooms = SharedClassroom.query.filter_by(
            original_classroom_id=student.classroom_id
        ).all()
        
        teachers_list = []
        
        # Ajouter le maître de classe
        if main_teacher:
            teachers_list.append({
                'name': main_teacher.username,
                'email': main_teacher.email,
                'subject': student.classroom.subject,
                'role': 'Maître de classe',
                'classroom_name': student.classroom.name
            })
        
        # Ajouter les enseignants spécialisés
        for derived_classroom in derived_classrooms:
            specialized_classroom = derived_classroom.derived_classroom
            if specialized_classroom and specialized_classroom.teacher:
                specialized_teacher = specialized_classroom.teacher
                teachers_list.append({
                    'name': specialized_teacher.username,
                    'email': specialized_teacher.email,
                    'subject': specialized_classroom.subject,
                    'role': 'Enseignant spécialisé',
                    'classroom_name': specialized_classroom.name
                })
        
        return jsonify({
            'teachers': teachers_list,
            'student_name': f"{student.first_name} {student.last_name}"
        })
        
    except Exception as e:
        print(f"Erreur dans get_student_teachers: {e}")
        return jsonify({'error': f'Erreur lors du chargement des enseignants: {str(e)}'}), 500