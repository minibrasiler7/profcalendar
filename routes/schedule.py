from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from extensions import db
from models.classroom import Classroom
from models.schedule import Schedule
from datetime import datetime, time, timedelta

schedule_bp = Blueprint('schedule', __name__, url_prefix='/schedule')

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

@schedule_bp.route('/weekly')
@login_required
def weekly_schedule():
    # Vérifier d'abord que la configuration de base est complète
    if not current_user.school_year_start or not current_user.day_start_time:
        flash('Veuillez d\'abord compléter la configuration initiale.', 'warning')
        return redirect(url_for('setup.initial_setup'))

    if current_user.classrooms.count() == 0:
        flash('Veuillez d\'abord ajouter au moins une classe.', 'warning')
        return redirect(url_for('setup.manage_classrooms'))

    # Si déjà complété, proposer d'aller au tableau de bord
    if current_user.schedule_completed:
        flash('Votre horaire type est déjà configuré. Vous pouvez le modifier ici.', 'info')

    classrooms = current_user.classrooms.all()

    # Convertir les classrooms en dictionnaires pour JSON
    classrooms_dict = [{
        'id': c.id,
        'name': c.name,
        'subject': c.subject,
        'color': c.color
    } for c in classrooms]

    periods = calculate_periods(current_user)

    # Convertir les périodes pour JSON
    periods_json = []
    for period in periods:
        periods_json.append({
            'number': period['number'],
            'start': period['start'].strftime('%H:%M'),
            'end': period['end'].strftime('%H:%M')
        })

    schedules = current_user.schedules.all()

    # Organiser les horaires par jour et période
    schedule_grid = {}
    for schedule in schedules:
        key = f"{schedule.weekday}_{schedule.period_number}"
        schedule_grid[key] = schedule

    days = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi']

    return render_template('setup/weekly_schedule.html',
                         classrooms=classrooms,
                         classrooms_json=classrooms_dict,
                         periods=periods,
                         periods_json=periods_json,
                         schedule_grid=schedule_grid,
                         days=days)

@schedule_bp.route('/save', methods=['POST'])
@login_required
def save_schedule():
    data = request.get_json()

    if not data:
        return jsonify({'success': False, 'message': 'Aucune donnée reçue'}), 400

    try:
        weekday = data.get('weekday')
        period_number = data.get('period_number')
        classroom_id = data.get('classroom_id')

        # Vérifier si un horaire existe déjà pour ce créneau
        existing = Schedule.query.filter_by(
            user_id=current_user.id,
            weekday=weekday,
            period_number=period_number
        ).first()

        if classroom_id:
            # Vérifier que la classe appartient à l'utilisateur
            classroom = Classroom.query.filter_by(id=classroom_id, user_id=current_user.id).first()
            if not classroom:
                return jsonify({'success': False, 'message': 'Classe non trouvée'}), 404

            # Calculer les heures de début et fin
            periods = calculate_periods(current_user)
            period = next((p for p in periods if p['number'] == period_number), None)
            if not period:
                return jsonify({'success': False, 'message': 'Période non valide'}), 400

            if existing:
                # Mettre à jour
                existing.classroom_id = classroom_id
                existing.start_time = period['start']
                existing.end_time = period['end']
            else:
                # Créer nouveau
                schedule = Schedule(
                    user_id=current_user.id,
                    classroom_id=classroom_id,
                    weekday=weekday,
                    period_number=period_number,
                    start_time=period['start'],
                    end_time=period['end']
                )
                db.session.add(schedule)
        else:
            # Supprimer l'horaire si pas de classe sélectionnée
            if existing:
                db.session.delete(existing)

        db.session.commit()
        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@schedule_bp.route('/validate', methods=['POST'])
@login_required
def validate_schedule():
    # Vérifier qu'il y a au moins un cours dans l'horaire
    schedules_count = current_user.schedules.count()
    if schedules_count == 0:
        flash('Veuillez ajouter au moins un cours dans votre horaire type.', 'warning')
        return redirect(url_for('schedule.weekly_schedule'))

    # Marquer l'horaire comme complété
    current_user.schedule_completed = True
    db.session.commit()

    flash('Horaire type validé avec succès ! Vous pouvez maintenant accéder à votre calendrier.', 'success')
    return redirect(url_for('planning.dashboard'))
