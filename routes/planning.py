from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from extensions import db
from models.planning import Planning
from models.classroom import Classroom
from models.schedule import Schedule
from datetime import datetime, timedelta
from datetime import date as date_type
import calendar

planning_bp = Blueprint('planning', __name__, url_prefix='/planning')

def get_week_dates(week_date):
    """Retourne les dates du lundi au vendredi de la semaine contenant la date donnée"""
    # Trouver le lundi de la semaine
    days_since_monday = week_date.weekday()
    monday = week_date - timedelta(days=days_since_monday)

    # Générer les 5 jours de la semaine
    week_dates = []
    for i in range(5):  # Lundi à Vendredi
        week_dates.append(monday + timedelta(days=i))

    return week_dates

def is_holiday(date_to_check, user):
    """Vérifie si une date est pendant les vacances et retourne le nom si c'est le cas"""
    for holiday in user.holidays.all():
        if holiday.start_date <= date_to_check <= holiday.end_date:
            return holiday.name
    return None

def is_school_year(date, user):
    """Vérifie si une date est dans l'année scolaire"""
    return user.school_year_start <= date <= user.school_year_end

def get_current_or_next_lesson(user):
    """Trouve le cours actuel ou le prochain cours"""
    now = datetime.now()
    current_time = now.time()
    current_date = now.date()
    weekday = current_date.weekday()

    # Récupérer les périodes du jour
    periods = calculate_periods(user)

    # Vérifier si on est actuellement en cours
    for period in periods:
        if period['start'] <= current_time <= period['end']:
            schedule = Schedule.query.filter_by(
                user_id=user.id,
                weekday=weekday,
                period_number=period['number']
            ).first()

            if schedule:
                return schedule, True, current_date  # schedule, is_current, date

    # Si pas de cours actuel, chercher le prochain aujourd'hui
    for period in periods:
        if period['start'] > current_time:
            schedule = Schedule.query.filter_by(
                user_id=user.id,
                weekday=weekday,
                period_number=period['number']
            ).first()

            if schedule:
                schedule.start_time = period['start']
                return schedule, False, current_date  # schedule, is_current, date

    # Si pas de cours aujourd'hui, chercher les jours suivants
    for days_ahead in range(1, 8):  # Chercher sur une semaine
        future_date = current_date + timedelta(days=days_ahead)
        future_weekday = future_date.weekday()

        # Ignorer les weekends
        if future_weekday >= 5:
            continue

        # Vérifier si c'est un jour de vacances
        if is_holiday(future_date, user):
            continue

        # Chercher le premier cours de la journée
        first_schedule = Schedule.query.filter_by(
            user_id=user.id,
            weekday=future_weekday
        ).order_by(Schedule.period_number).first()

        if first_schedule:
            # Obtenir l'heure de début de la première période
            future_periods = calculate_periods(user)
            if future_periods:
                first_schedule.start_time = future_periods[0]['start']
            return first_schedule, False, future_date  # schedule, is_current, date

    return None, False, None

@planning_bp.route('/')
@login_required
def dashboard():
    # Vérifier que la configuration de base est complète
    if not current_user.setup_completed:
        if not current_user.school_year_start:
            flash('Veuillez d\'abord compléter la configuration initiale.', 'warning')
            return redirect(url_for('setup.initial_setup'))
        elif current_user.classrooms.count() == 0:
            flash('Veuillez d\'abord ajouter au moins une classe.', 'warning')
            return redirect(url_for('setup.manage_classrooms'))
        else:
            flash('Veuillez terminer la configuration de base.', 'warning')
            return redirect(url_for('setup.manage_holidays'))

    # Vérifier que l'horaire type est complété
    if not current_user.schedule_completed:
        flash('Veuillez d\'abord créer votre horaire type.', 'warning')
        return redirect(url_for('schedule.weekly_schedule'))

    # Statistiques pour le tableau de bord
    classrooms_count = current_user.classrooms.count()
    schedules_count = current_user.schedules.count()

    # Obtenir la semaine actuelle
    today = date_type.today()
    week_dates = get_week_dates(today)

    # Plannings de la semaine
    week_plannings = Planning.query.filter(
        Planning.user_id == current_user.id,
        Planning.date >= week_dates[0],
        Planning.date <= week_dates[4]
    ).all()

    # Chercher le cours actuel ou le prochain
    lesson, is_current_lesson, lesson_date = get_current_or_next_lesson(current_user)

    return render_template('planning/dashboard.html',
                         classrooms_count=classrooms_count,
                         schedules_count=schedules_count,
                         week_plannings_count=len(week_plannings),
                         today=today,
                         current_lesson=lesson if is_current_lesson else None,
                         next_lesson=lesson if not is_current_lesson else None,
                         lesson_date=lesson_date)

@planning_bp.route('/calendar')
@login_required
def calendar_view():
    # Vérifier la configuration
    if not current_user.setup_completed:
        flash('Veuillez d\'abord compléter la configuration initiale.', 'warning')
        return redirect(url_for('setup.initial_setup'))

    if not current_user.schedule_completed:
        flash('Veuillez d\'abord créer votre horaire type.', 'warning')
        return redirect(url_for('schedule.weekly_schedule'))

    # Obtenir la semaine à afficher
    week_str = request.args.get('week')
    if week_str:
        try:
            current_week = datetime.strptime(week_str, '%Y-%m-%d').date()
        except ValueError:
            current_week = date_type.today()
    else:
        current_week = date_type.today()

    # Obtenir les dates de la semaine
    week_dates = get_week_dates(current_week)

    # Récupérer toutes les données nécessaires
    classrooms = current_user.classrooms.all()

    # Convertir les classrooms en dictionnaires pour JSON
    classrooms_dict = [{
        'id': c.id,
        'name': c.name,
        'subject': c.subject,
        'color': c.color
    } for c in classrooms]

    periods = calculate_periods(current_user)
    schedules = current_user.schedules.all()

    # Convertir les périodes pour JSON (convertir les objets time en chaînes)
    periods_json = []
    for period in periods:
        periods_json.append({
            'number': period['number'],
            'start': period['start'].strftime('%H:%M'),
            'end': period['end'].strftime('%H:%M')
        })

    # Organiser les horaires par jour et période
    schedule_grid = {}
    for schedule in schedules:
        key = f"{schedule.weekday}_{schedule.period_number}"
        schedule_grid[key] = schedule

    # Récupérer les plannings de la semaine
    week_plannings = Planning.query.filter(
        Planning.user_id == current_user.id,
        Planning.date >= week_dates[0],
        Planning.date <= week_dates[4]
    ).all()

    # Organiser les plannings par date et période
    planning_grid = {}
    for planning in week_plannings:
        key = f"{planning.date}_{planning.period_number}"
        planning_grid[key] = planning

    # Vérifier si les dates sont en vacances et récupérer les noms
    holidays_info = {}
    for date in week_dates:
        date_str = date.strftime('%Y-%m-%d')
        holiday_name = is_holiday(date, current_user)
        holidays_info[date_str] = {
            'is_holiday': holiday_name is not None,
            'name': holiday_name
        }

    # Générer les données annuelles pour chaque classe
    annual_data = {}
    for classroom in classrooms:
        annual_data[classroom.id] = generate_annual_calendar(classroom)

    # Sélectionner la première classe par défaut
    selected_classroom_id = request.args.get('classroom', classrooms[0].id if classrooms else None)

    return render_template('planning/calendar_view.html',
                         week_dates=week_dates,
                         current_week=current_week,
                         classrooms=classrooms,
                         classrooms_json=classrooms_dict,
                         periods=periods,
                         periods_json=periods_json,
                         schedule_grid=schedule_grid,
                         planning_grid=planning_grid,
                         annual_data=annual_data,
                         holidays_info=holidays_info,
                         selected_classroom_id=int(selected_classroom_id) if selected_classroom_id else None,
                         days=['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi'],
                         today=date_type.today())

def calculate_periods(user):
    """Calcule les périodes en fonction de la configuration de l'utilisateur"""
    from routes.schedule import calculate_periods as calc_periods
    return calc_periods(user)

def generate_annual_calendar(classroom):
    """Génère les données du calendrier annuel pour une classe"""
    # Calculer toutes les semaines de l'année scolaire
    start_date = current_user.school_year_start
    end_date = current_user.school_year_end

    # Récupérer toutes les vacances
    holidays = current_user.holidays.all()

    # Récupérer tous les plannings pour cette classe
    all_plannings = Planning.query.filter_by(
        user_id=current_user.id,
        classroom_id=classroom.id
    ).all()

    # Organiser les plannings par date
    plannings_by_date = {}
    for planning in all_plannings:
        date_str = planning.date.strftime('%Y-%m-%d')
        if date_str not in plannings_by_date:
            plannings_by_date[date_str] = []
        plannings_by_date[date_str].append({
            'title': planning.title or f'P{planning.period_number}',
            'period': planning.period_number
        })

    weeks = []
    current_date = start_date
    # Aller au lundi de la première semaine
    current_date -= timedelta(days=current_date.weekday())

    week_number = 0  # Compteur de semaines scolaires (hors vacances)

    while current_date <= end_date:
        week_dates = get_week_dates(current_date)

        # Vérifier si cette semaine est pendant les vacances
        week_holiday = None

        # Pour chaque période de vacances
        for holiday in holidays:
            # Compter combien de jours ouvrables (lundi-vendredi) sont en vacances
            days_in_holiday = 0
            for i in range(5):  # Seulement lundi à vendredi
                date_to_check = week_dates[i]
                if holiday.start_date <= date_to_check <= holiday.end_date:
                    days_in_holiday += 1

            # Si au moins 3 jours ouvrables sont en vacances, c'est une semaine de vacances
            if days_in_holiday >= 3:
                week_holiday = holiday.name
                break

        # Incrémenter le compteur seulement si ce n'est pas une semaine de vacances
        if not week_holiday and current_date >= start_date:
            week_number += 1

        week_info = {
            'start_date': week_dates[0],
            'dates': week_dates,
            'has_class': [False] * 5,  # Par défaut, pas de cours
            'plannings': {},  # Plannings de la semaine
            'holidays_by_day': [None] * 5,  # Nom des vacances par jour
            'is_holiday': week_holiday is not None,
            'holiday_name': week_holiday,
            'holiday_name_short': week_holiday.replace("Vacances d'", "Vac.").replace("Vacances de ", "Vac. ").replace("Relâches de ", "Relâches ") if week_holiday else None,
            'week_number': week_number if not week_holiday else None,
            'formatted_date': week_dates[0].strftime('%d/%m')  # Date du lundi
        }

        # Vérifier pour chaque jour si la classe a cours et s'il y a des vacances
        for i in range(5):  # 0 à 4 pour lundi à vendredi
            date_to_check = week_dates[i]
            date_str = date_to_check.strftime('%Y-%m-%d')

            # Vérifier si c'est un jour de vacances
            holiday_name = is_holiday(date_to_check, current_user)
            if holiday_name:
                week_info['holidays_by_day'][i] = holiday_name

            if not is_school_year(date_to_check, current_user) or holiday_name:
                continue

            # Vérifier dans l'horaire type si cette classe a cours ce jour
            weekday = i
            has_schedule = Schedule.query.filter_by(
                user_id=current_user.id,
                classroom_id=classroom.id,
                weekday=weekday
            ).first() is not None

            week_info['has_class'][i] = has_schedule

            # Ajouter les plannings pour ce jour
            if date_str in plannings_by_date:
                week_info['plannings'][date_str] = plannings_by_date[date_str]

        weeks.append(week_info)
        current_date += timedelta(days=7)

    return weeks

@planning_bp.route('/save_planning', methods=['POST'])
@login_required
def save_planning():
    data = request.get_json()

    if not data:
        return jsonify({'success': False, 'message': 'Aucune donnée reçue'}), 400

    try:
        date_str = data.get('date')
        period_number = data.get('period_number')
        classroom_id = data.get('classroom_id')
        title = data.get('title', '')
        description = data.get('description', '')

        # Convertir la date
        planning_date = datetime.strptime(date_str, '%Y-%m-%d').date()

        # Vérifier la classe
        if classroom_id:
            classroom = Classroom.query.filter_by(id=classroom_id, user_id=current_user.id).first()
            if not classroom:
                return jsonify({'success': False, 'message': 'Classe non trouvée'}), 404

        # Chercher un planning existant
        existing = Planning.query.filter_by(
            user_id=current_user.id,
            date=planning_date,
            period_number=period_number
        ).first()

        if classroom_id and (title or description):
            if existing:
                # Mettre à jour
                existing.classroom_id = classroom_id
                existing.title = title
                existing.description = description
            else:
                # Créer nouveau
                planning = Planning(
                    user_id=current_user.id,
                    classroom_id=classroom_id,
                    date=planning_date,
                    period_number=period_number,
                    title=title,
                    description=description
                )
                db.session.add(planning)
        else:
            # Supprimer si vide
            if existing:
                db.session.delete(existing)

        db.session.commit()
        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@planning_bp.route('/get_available_periods/<date>')
@login_required
def get_available_periods(date):
    """Retourne les périodes disponibles pour une date avec leur état de planification"""
    try:
        planning_date = datetime.strptime(date, '%Y-%m-%d').date()
        weekday = planning_date.weekday()

        # Récupérer les périodes du jour
        periods = calculate_periods(current_user)

        # Récupérer les plannings existants pour cette date
        existing_plannings = Planning.query.filter_by(
            user_id=current_user.id,
            date=planning_date
        ).all()

        planning_by_period = {p.period_number: p for p in existing_plannings}

        # Récupérer l'horaire type pour ce jour
        schedules = Schedule.query.filter_by(
            user_id=current_user.id,
            weekday=weekday
        ).all()

        schedule_by_period = {s.period_number: s for s in schedules}

        # Construire la réponse
        result_periods = []
        for period in periods:
            period_info = {
                'number': period['number'],
                'start': period['start'].strftime('%H:%M'),
                'end': period['end'].strftime('%H:%M'),
                'hasPlanning': period['number'] in planning_by_period,
                'hasSchedule': period['number'] in schedule_by_period
            }

            if period['number'] in schedule_by_period:
                period_info['defaultClassroom'] = schedule_by_period[period['number']].classroom_id

            result_periods.append(period_info)

        return jsonify({
            'success': True,
            'periods': result_periods
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@planning_bp.route('/get_planning/<date>/<int:period>')
@login_required
def get_planning(date, period):
    try:
        planning_date = datetime.strptime(date, '%Y-%m-%d').date()
        planning = Planning.query.filter_by(
            user_id=current_user.id,
            date=planning_date,
            period_number=period
        ).first()

        if planning:
            return jsonify({
                'success': True,
                'planning': {
                    'classroom_id': planning.classroom_id,
                    'title': planning.title,
                    'description': planning.description
                }
            })
        else:
            # Retourner l'horaire type par défaut
            weekday = planning_date.weekday()
            schedule = Schedule.query.filter_by(
                user_id=current_user.id,
                weekday=weekday,
                period_number=period
            ).first()

            if schedule:
                return jsonify({
                    'success': True,
                    'planning': {
                        'classroom_id': schedule.classroom_id,
                        'title': '',
                        'description': ''
                    }
                })

        return jsonify({'success': True, 'planning': None})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@planning_bp.route('/lesson')
@login_required
def lesson_view():
    """Affiche la vue du cours actuel ou du prochain cours"""
    from datetime import time as time_type

    # Obtenir l'heure actuelle et le jour de la semaine
    now = datetime.now()
    current_time = now.time()
    current_date = now.date()
    weekday = current_date.weekday()

    # Récupérer les périodes du jour
    periods = calculate_periods(current_user)

    # Trouver le cours actuel ou le prochain
    current_lesson = None
    next_lesson = None
    is_current = False

    # Vérifier si on est actuellement en cours
    for period in periods:
        period_start = period['start']
        period_end = period['end']

        # Vérifier si on est dans cette période
        if period_start <= current_time <= period_end:
            # Chercher s'il y a un cours à cette période aujourd'hui
            schedule = Schedule.query.filter_by(
                user_id=current_user.id,
                weekday=weekday,
                period_number=period['number']
            ).first()

            if schedule:
                current_lesson = schedule
                is_current = True
                break

    # Si pas de cours actuel, chercher le prochain
    if not current_lesson:
        # D'abord chercher aujourd'hui
        for period in periods:
            if period['start'] > current_time:
                schedule = Schedule.query.filter_by(
                    user_id=current_user.id,
                    weekday=weekday,
                    period_number=period['number']
                ).first()

                if schedule:
                    next_lesson = schedule
                    break

        # Si pas de cours aujourd'hui, chercher les jours suivants
        if not next_lesson:
            for days_ahead in range(1, 8):  # Chercher sur une semaine
                future_date = current_date + timedelta(days=days_ahead)
                future_weekday = future_date.weekday()

                # Ignorer les weekends
                if future_weekday >= 5:
                    continue

                # Chercher le premier cours de la journée
                first_schedule = Schedule.query.filter_by(
                    user_id=current_user.id,
                    weekday=future_weekday
                ).order_by(Schedule.period_number).first()

                if first_schedule:
                    next_lesson = first_schedule
                    current_date = future_date  # Mettre à jour la date pour l'affichage
                    break

    # Préparer les données pour l'affichage
    lesson = current_lesson or next_lesson

    if not lesson:
        flash('Aucun cours programmé dans votre emploi du temps.', 'info')
        return redirect(url_for('planning.dashboard'))

    # Récupérer la planification si elle existe
    planning = None
    if lesson:
        planning = Planning.query.filter_by(
            user_id=current_user.id,
            date=current_date,
            period_number=lesson.period_number
        ).first()

    # Calculer le temps restant si cours en cours
    remaining_seconds = 0
    time_remaining = ""

    if is_current:
        # Trouver la période actuelle pour avoir l'heure de fin
        current_period = next((p for p in periods if p['number'] == lesson.period_number), None)
        if current_period:
            end_datetime = datetime.combine(current_date, current_period['end'])
            now_datetime = datetime.now()

            if end_datetime > now_datetime:
                remaining_seconds = int((end_datetime - now_datetime).total_seconds())
                hours = remaining_seconds // 3600
                minutes = (remaining_seconds % 3600) // 60

                if hours > 0:
                    time_remaining = f"{hours}:{minutes:02d}:00"
                else:
                    time_remaining = f"{minutes}:{remaining_seconds % 60:02d}"

    return render_template('planning/lesson_view.html',
                         lesson=lesson,
                         planning=planning,
                         is_current=is_current,
                         lesson_date=current_date,
                         time_remaining=time_remaining,
                         remaining_seconds=remaining_seconds)
