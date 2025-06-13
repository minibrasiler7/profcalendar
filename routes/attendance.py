from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_required, current_user
from extensions import db
from models.attendance import Attendance
from models.student import Student
from models.classroom import Classroom
from models.absence_justification import AbsenceJustification
from datetime import datetime, date, time, timedelta

attendance_bp = Blueprint('attendance', __name__, url_prefix='/attendance')

def get_user_periods_schedule(user):
    """Utilise la fonction existante du système pour calculer les périodes"""
    from routes.schedule import calculate_periods
    return calculate_periods(user)

def get_period_time_range(periods_numbers, user):
    """Récupère les horaires pour une liste de numéros de périodes"""
    periods_schedule = get_user_periods_schedule(user)
    period_schedule_map = {p['number']: p for p in periods_schedule}
    
    if not periods_numbers:
        return "", ""
    
    # Trier les numéros de périodes
    sorted_periods = sorted(periods_numbers)
    
    # Récupérer l'heure de début de la première période et l'heure de fin de la dernière
    start_period = period_schedule_map.get(sorted_periods[0])
    end_period = period_schedule_map.get(sorted_periods[-1])
    
    if start_period and end_period:
        start_time = start_period['start'].strftime('%H:%M')
        end_time = end_period['end'].strftime('%H:%M')
        periods_str = ', '.join(map(str, sorted_periods))
        return periods_str, f"{start_time} - {end_time}"
    
    return ', '.join(map(str, sorted_periods)), ""

@attendance_bp.route('/')
@login_required
def index():
    """Page principale de suivi des absences"""
    # Vérifier la configuration de base
    if not current_user.setup_completed:
        return redirect(url_for('setup.initial_setup'))
    
    # Récupérer toutes les classes de l'utilisateur
    classrooms = current_user.classrooms.all()
    
    return render_template('attendance/index.html', classrooms=classrooms)

@attendance_bp.route('/api/absences')
@login_required
def get_absences():
    """API pour récupérer les absences avec filtres"""
    try:
        # Paramètres de filtrage
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        classroom_id = request.args.get('classroom_id', type=int)
        student_name = request.args.get('student_name', '').strip()
        
        # Query de base pour les absences
        query = db.session.query(Attendance, Student, Classroom).join(
            Student, Attendance.student_id == Student.id
        ).join(
            Classroom, Attendance.classroom_id == Classroom.id
        ).filter(
            Classroom.user_id == current_user.id,
            Attendance.status == 'absent'
        )
        
        # Appliquer les filtres
        if start_date:
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                query = query.filter(Attendance.date >= start_date_obj)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                query = query.filter(Attendance.date <= end_date_obj)
            except ValueError:
                pass
        
        if classroom_id:
            query = query.filter(Attendance.classroom_id == classroom_id)
        
        if student_name:
            query = query.filter(
                db.or_(
                    Student.first_name.ilike(f'%{student_name}%'),
                    Student.last_name.ilike(f'%{student_name}%')
                )
            )
        
        # Trier par date décroissante puis par élève et période
        results = query.order_by(Attendance.date.desc(), Student.last_name, Student.first_name, Attendance.period_number).all()
        
        # Regrouper les absences par élève et date
        grouped_absences = {}
        for attendance, student, classroom in results:
            key = f"{attendance.date}_{student.id}_{classroom.id}"
            
            if key not in grouped_absences:
                grouped_absences[key] = {
                    'date': attendance.date,
                    'date_str': attendance.date.strftime('%d/%m/%Y'),
                    'date_iso': attendance.date.isoformat(),
                    'student_name': student.full_name,
                    'classroom_name': classroom.name,
                    'periods': [],
                    'comments': []
                }
            
            grouped_absences[key]['periods'].append(attendance.period_number)
            if attendance.comment:
                grouped_absences[key]['comments'].append(attendance.comment)
        
        # Formater les données avec horaires
        absences_data = []
        for key, group in grouped_absences.items():
            periods_str, time_range = get_period_time_range(group['periods'], current_user)
            
            absences_data.append({
                'date': group['date_str'],
                'date_iso': group['date_iso'],
                'student_name': group['student_name'],
                'classroom_name': group['classroom_name'],
                'periods': periods_str,
                'time_range': time_range,
                'comment': ' | '.join(group['comments']) if group['comments'] else ''
            })
        
        # Trier par date décroissante
        absences_data.sort(key=lambda x: x['date_iso'], reverse=True)
        
        return jsonify({
            'success': True,
            'absences': absences_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@attendance_bp.route('/api/late-arrivals')
@login_required
def get_late_arrivals():
    """API pour récupérer les retards avec filtres"""
    try:
        # Paramètres de filtrage
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        classroom_id = request.args.get('classroom_id', type=int)
        student_name = request.args.get('student_name', '').strip()
        
        # Query de base pour les retards
        query = db.session.query(Attendance, Student, Classroom).join(
            Student, Attendance.student_id == Student.id
        ).join(
            Classroom, Attendance.classroom_id == Classroom.id
        ).filter(
            Classroom.user_id == current_user.id,
            Attendance.status == 'late'
        )
        
        # Appliquer les filtres
        if start_date:
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                query = query.filter(Attendance.date >= start_date_obj)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                query = query.filter(Attendance.date <= end_date_obj)
            except ValueError:
                pass
        
        if classroom_id:
            query = query.filter(Attendance.classroom_id == classroom_id)
        
        if student_name:
            query = query.filter(
                db.or_(
                    Student.first_name.ilike(f'%{student_name}%'),
                    Student.last_name.ilike(f'%{student_name}%')
                )
            )
        
        # Trier par date décroissante puis par élève et période
        results = query.order_by(Attendance.date.desc(), Student.last_name, Student.first_name, Attendance.period_number).all()
        
        # Regrouper les retards par élève et date
        grouped_late = {}
        for attendance, student, classroom in results:
            key = f"{attendance.date}_{student.id}_{classroom.id}"
            
            if key not in grouped_late:
                grouped_late[key] = {
                    'date': attendance.date,
                    'date_str': attendance.date.strftime('%d/%m/%Y'),
                    'date_iso': attendance.date.isoformat(),
                    'student_name': student.full_name,
                    'classroom_name': classroom.name,
                    'periods': [],
                    'late_minutes': [],
                    'comments': []
                }
            
            grouped_late[key]['periods'].append(attendance.period_number)
            grouped_late[key]['late_minutes'].append(attendance.late_minutes or 0)
            if attendance.comment:
                grouped_late[key]['comments'].append(attendance.comment)
        
        # Formater les données avec horaires
        late_arrivals_data = []
        for key, group in grouped_late.items():
            periods_str, time_range = get_period_time_range(group['periods'], current_user)
            total_late_minutes = sum(group['late_minutes'])
            
            late_arrivals_data.append({
                'date': group['date_str'],
                'date_iso': group['date_iso'],
                'student_name': group['student_name'],
                'classroom_name': group['classroom_name'],
                'periods': periods_str,
                'time_range': time_range,
                'late_minutes': total_late_minutes,
                'comment': ' | '.join(group['comments']) if group['comments'] else ''
            })
        
        # Trier par date décroissante
        late_arrivals_data.sort(key=lambda x: x['date_iso'], reverse=True)
        
        return jsonify({
            'success': True,
            'late_arrivals': late_arrivals_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@attendance_bp.route('/api/stats')
@login_required
def get_attendance_stats():
    """API pour récupérer les statistiques d'absences"""
    try:
        # Paramètres de filtrage
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        classroom_id = request.args.get('classroom_id', type=int)
        
        # Query de base
        query = db.session.query(Attendance).join(
            Classroom, Attendance.classroom_id == Classroom.id
        ).filter(
            Classroom.user_id == current_user.id
        )
        
        # Appliquer les filtres de date
        if start_date:
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                query = query.filter(Attendance.date >= start_date_obj)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                query = query.filter(Attendance.date <= end_date_obj)
            except ValueError:
                pass
        
        if classroom_id:
            query = query.filter(Attendance.classroom_id == classroom_id)
        
        # Compter les différents statuts
        all_records = query.all()
        
        stats = {
            'total_records': len(all_records),
            'present': len([r for r in all_records if r.status == 'present']),
            'absent': len([r for r in all_records if r.status == 'absent']),
            'late': len([r for r in all_records if r.status == 'late'])
        }
        
        # Calculer les pourcentages
        if stats['total_records'] > 0:
            stats['present_percentage'] = round((stats['present'] / stats['total_records']) * 100, 1)
            stats['absent_percentage'] = round((stats['absent'] / stats['total_records']) * 100, 1)
            stats['late_percentage'] = round((stats['late'] / stats['total_records']) * 100, 1)
        else:
            stats['present_percentage'] = 0
            stats['absent_percentage'] = 0
            stats['late_percentage'] = 0
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@attendance_bp.route('/api/justifications')
@login_required
def get_justifications():
    """API pour récupérer les justifications d'absence avec filtres"""
    try:
        # Paramètres de filtrage
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        classroom_id = request.args.get('classroom_id', type=int)
        student_name = request.args.get('student_name', '').strip()
        status = request.args.get('status', '').strip()
        
        # Query de base pour les justifications
        query = db.session.query(AbsenceJustification, Student, Classroom).join(
            Student, AbsenceJustification.student_id == Student.id
        ).join(
            Classroom, Student.classroom_id == Classroom.id
        ).filter(
            Classroom.user_id == current_user.id
        )
        
        # Appliquer les filtres
        if start_date:
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                query = query.filter(AbsenceJustification.absence_date >= start_date_obj)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                query = query.filter(AbsenceJustification.absence_date <= end_date_obj)
            except ValueError:
                pass
        
        if classroom_id:
            query = query.filter(Student.classroom_id == classroom_id)
        
        if student_name:
            query = query.filter(
                db.or_(
                    Student.first_name.ilike(f'%{student_name}%'),
                    Student.last_name.ilike(f'%{student_name}%')
                )
            )
        
        if status:
            query = query.filter(AbsenceJustification.status == status)
        
        # Trier par date de création décroissante
        results = query.order_by(AbsenceJustification.created_at.desc()).all()
        
        # Formater les données
        justifications_data = []
        for justification, student, classroom in results:
            periods = justification.get_periods_list()
            periods_str = ', '.join([f"P{p.get('period', '')}" for p in periods]) if periods else ''
            
            # Calculer les horaires en utilisant la fonction existante
            period_numbers = [p.get('period') for p in periods if p.get('period')]
            _, time_range = get_period_time_range(period_numbers, current_user)
            
            justifications_data.append({
                'id': justification.id,
                'date': justification.absence_date.strftime('%d/%m/%Y'),
                'date_iso': justification.absence_date.isoformat(),
                'student_name': student.full_name,
                'classroom_name': classroom.name,
                'periods': periods_str,
                'time_range': time_range,
                'reason_type': justification.reason_type,
                'reason_display': justification.get_reason_display(),
                'other_reason_text': justification.other_reason_text,
                'dispense_subject': justification.dispense_subject,
                'status': justification.status,
                'status_display': justification.get_status_display(),
                'teacher_response': justification.teacher_response,
                'created_at': justification.created_at.strftime('%d/%m/%Y à %H:%M'),
                'processed_at': justification.processed_at.strftime('%d/%m/%Y à %H:%M') if justification.processed_at else None
            })
        
        return jsonify({
            'success': True,
            'justifications': justifications_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500