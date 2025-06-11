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

@planning_bp.route('/api/day/<date_str>')
@login_required
def get_day_plannings(date_str):
    """API endpoint pour récupérer les planifications d'une journée"""
    try:
        print(f"📅 Requête pour les planifications du {date_str}")
        
        # Parser la date
        planning_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Récupérer l'ID de la classe depuis les paramètres de requête
        classroom_id = request.args.get('classroom_id')
        print(f"🏫 Classe ID: {classroom_id}")
        
        # Construire la requête de base
        query = Planning.query.filter_by(
            user_id=current_user.id,
            date=planning_date
        )
        
        # Filtrer par classe si spécifié
        if classroom_id and classroom_id != '':
            query = query.filter_by(classroom_id=int(classroom_id))
        
        # Récupérer les planifications
        plannings = query.all()
        print(f"📊 Nombre de planifications trouvées: {len(plannings)}")
        
        # Récupérer les périodes de l'utilisateur
        periods = calculate_periods(current_user)
        periods_dict = {p['number']: p for p in periods}
        
        # Construire la réponse
        result = []
        for planning in plannings:
            period_info = periods_dict.get(planning.period_number)
            
            try:
                # Récupérer les informations de classe avec gestion d'erreur
                classroom_name = ''
                classroom_subject = ''
                classroom_color = '#4F46E5'
                
                if planning.classroom:
                    classroom_name = planning.classroom.name or ''
                    classroom_subject = planning.classroom.subject or ''
                    classroom_color = planning.classroom.color or '#4F46E5'
                
                result.append({
                    'id': planning.id,
                    'period': planning.period_number,
                    'period_start': period_info['start'].strftime('%H:%M') if period_info else '',
                    'period_end': period_info['end'].strftime('%H:%M') if period_info else '',
                    'classroom_id': planning.classroom_id,
                    'classroom_name': classroom_name,
                    'classroom_subject': classroom_subject,
                    'classroom_color': classroom_color,
                    'title': planning.title or '',
                    'description': planning.description or ''
                })
            except Exception as plan_error:
                print(f"Erreur lors du traitement de la planification {planning.id}: {plan_error}")
                # Continuer avec les autres planifications
        
        # Trier par période
        result.sort(key=lambda x: x['period'])
        
        print(f"✅ Réponse construite avec {len(result)} planifications")
        
        return jsonify({
            'success': True,
            'plannings': result
        })
        
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Format de date invalide'
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

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
    # Ajouter cette section dans la fonction calendar_view après la récupération des plannings
# (vers la ligne 160 du fichier routes/planning.py)

    # Récupérer les plannings de la semaine
    week_plannings = Planning.query.filter(
        Planning.user_id == current_user.id,
        Planning.date >= week_dates[0],
        Planning.date <= week_dates[4]
    ).all()

    # Organiser les plannings par date et période avec les infos de checklist
    planning_grid = {}
    for planning in week_plannings:
        key = f"{planning.date}_{planning.period_number}"
        planning_grid[key] = planning

        # Ajouter les informations de checklist pour chaque planning
        # Cette information sera accessible dans le template
        planning.checklist_summary = planning.get_checklist_summary()
        planning.checklist_items = planning.get_checklist_items_with_states()

# Dans la fonction generate_annual_calendar, modifier la partie qui organise les plannings
# (vers la ligne 245)

    # Organiser les plannings par date avec infos de checklist
    plannings_by_date = {}
    for planning in week_plannings:
        date_str = planning.date.strftime('%Y-%m-%d')
        if date_str not in plannings_by_date:
            plannings_by_date[date_str] = []

        # Obtenir le résumé des checkboxes
        checklist_summary = planning.get_checklist_summary()

        planning_data = {
            'title': planning.title or f'P{planning.period_number}',
            'period': planning.period_number,
            'checklist_summary': checklist_summary
        }

        plannings_by_date[date_str].append(planning_data)

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

    # Créer une version JSON-serializable de schedule_grid
    schedule_grid_json = {}
    for key, schedule in schedule_grid.items():
        schedule_grid_json[key] = {
            'classroom_id': schedule.classroom_id,
            'weekday': schedule.weekday,
            'period_number': schedule.period_number
        }

    return render_template('planning/calendar_view.html',
                         week_dates=week_dates,
                         current_week=current_week,
                         classrooms=classrooms,
                         classrooms_json=classrooms_dict,
                         periods=periods,
                         periods_json=periods_json,
                         schedule_grid=schedule_grid,
                         schedule_grid_json=schedule_grid_json,
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
        checklist_states = data.get('checklist_states', {})  # Récupérer les états des checkboxes

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
                existing.set_checklist_states(checklist_states)  # Sauvegarder les états des checkboxes
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
                planning.set_checklist_states(checklist_states)  # Sauvegarder les états des checkboxes
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


@planning_bp.route('/test-sanctions')
@login_required
def test_sanctions():
    """Page de test pour le système de sanctions"""
    # Obtenir la leçon actuelle pour les données de contexte
    lesson, is_current_lesson, lesson_date = get_current_or_next_lesson(current_user)
    
    return render_template('planning/test_sanctions.html',
                         lesson=lesson,
                         lesson_date=lesson_date,
                         is_current=is_current_lesson)

@planning_bp.route('/lesson')
@login_required
def lesson_view():
    """Affiche la vue du cours actuel ou du prochain cours"""
    from datetime import time as time_type
    from models.student import Student
    from models.attendance import Attendance

    # Obtenir l'heure actuelle et le jour de la semaine
    now = datetime.now()
    current_time = now.time()
    current_date = now.date()
    weekday = current_date.weekday()

    # Déterminer la date de recherche selon l'année scolaire
    search_start_date = current_date

    # Si on est avant le début de l'année scolaire, commencer la recherche au début
    if current_user.school_year_start and current_date < current_user.school_year_start:
        search_start_date = current_user.school_year_start
        # Ajuster weekday pour la date de début
        weekday = search_start_date.weekday()
        # Pour la recherche du premier cours, on ne vérifie pas l'heure actuelle
        current_time = time_type(0, 0)  # Minuit pour prendre tous les cours du jour

    # Récupérer les périodes du jour
    periods = calculate_periods(current_user)

    # Trouver le cours actuel ou le prochain
    current_lesson = None
    next_lesson = None
    is_current = False
    lesson_date = search_start_date

    # Vérifier si on est actuellement en cours (seulement si on est à la date du jour)
    if search_start_date == current_date:
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
        # D'abord chercher dans la journée de départ (aujourd'hui ou début d'année)
        for period in periods:
            # Si on est le jour actuel, ne prendre que les périodes futures
            if search_start_date == current_date and period['start'] <= now.time():
                continue

            schedule = Schedule.query.filter_by(
                user_id=current_user.id,
                weekday=weekday,
                period_number=period['number']
            ).first()

            if schedule:
                next_lesson = schedule
                lesson_date = search_start_date
                break

        # Si pas de cours ce jour-là, chercher les jours suivants
        if not next_lesson:
            # Calculer le nombre de jours maximum à chercher
            if current_user.school_year_end:
                max_days = (current_user.school_year_end - search_start_date).days
                # Limiter à 365 jours pour éviter les boucles infinies
                max_days = min(max_days, 365)
            else:
                max_days = 365

            for days_ahead in range(1, max_days + 1):
                future_date = search_start_date + timedelta(days=days_ahead)

                # Vérifier qu'on ne dépasse pas la fin de l'année scolaire
                if current_user.school_year_end and future_date > current_user.school_year_end:
                    break

                future_weekday = future_date.weekday()

                # Ignorer les weekends
                if future_weekday >= 5:
                    continue

                # Vérifier si c'est un jour de vacances
                if is_holiday(future_date, current_user):
                    continue

                # Chercher le premier cours de la journée
                first_schedule = Schedule.query.filter_by(
                    user_id=current_user.id,
                    weekday=future_weekday
                ).order_by(Schedule.period_number).first()

                if first_schedule:
                    next_lesson = first_schedule
                    lesson_date = future_date
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
            date=lesson_date,
            period_number=lesson.period_number
        ).first()

    # Vérifier que la classe appartient bien à l'utilisateur
    lesson_classroom = Classroom.query.filter_by(
        id=lesson.classroom_id,
        user_id=current_user.id
    ).first()
    
    if not lesson_classroom:
        flash('Classe non trouvée ou non autorisée.', 'error')
        return redirect(url_for('planning.dashboard'))

    # Récupérer les élèves de la classe
    students = Student.query.filter_by(
        classroom_id=lesson.classroom_id
    ).order_by(Student.last_name, Student.first_name).all()

    # Récupérer les présences existantes pour ce cours
    attendance_records = {}
    if lesson:
        attendances = Attendance.query.filter_by(
            classroom_id=lesson.classroom_id,
            date=lesson_date,
            period_number=lesson.period_number
        ).all()

        for attendance in attendances:
            attendance_records[attendance.student_id] = {
                'status': attendance.status,
                'late_minutes': attendance.late_minutes,
                'comment': attendance.comment
            }

    # Récupérer les modèles de sanctions importés dans cette classe
    from models.sanctions import SanctionTemplate, ClassroomSanctionImport
    from models.student_sanctions import StudentSanctionCount
    
    imported_sanctions = db.session.query(SanctionTemplate).join(ClassroomSanctionImport).filter(
        ClassroomSanctionImport.classroom_id == lesson.classroom_id,
        ClassroomSanctionImport.is_active == True,
        SanctionTemplate.user_id == current_user.id,
        SanctionTemplate.is_active == True
    ).order_by(SanctionTemplate.name).all()

    # Créer le tableau des coches pour chaque élève/sanction
    sanctions_data = {}
    for student in students:
        sanctions_data[student.id] = {}
        for sanction in imported_sanctions:
            # Récupérer ou créer le compteur de coches
            count = StudentSanctionCount.query.filter_by(
                student_id=student.id,
                template_id=sanction.id
            ).first()
            
            if not count:
                # Créer un nouveau compteur à 0
                count = StudentSanctionCount(
                    student_id=student.id,
                    template_id=sanction.id,
                    check_count=0
                )
                db.session.add(count)
            
            sanctions_data[student.id][sanction.id] = count.check_count
    
    # Sauvegarder les nouveaux compteurs créés
    db.session.commit()

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

    # Récupérer le plan de classe actif pour cette classe
    seating_plan = None
    try:
        if lesson and lesson_classroom:
            from models.seating_plan import SeatingPlan
            import json
            
            seating_plan_record = SeatingPlan.query.filter_by(
                classroom_id=lesson.classroom_id,
                user_id=current_user.id,
                is_active=True
            ).first()
            
            if seating_plan_record:
                seating_plan = {
                    'id': seating_plan_record.id,
                    'name': seating_plan_record.name,
                    'plan_data': json.loads(seating_plan_record.plan_data)
                }
    except Exception as e:
        print(f"Erreur plan de classe: {e}")
        seating_plan = None

    return render_template('planning/lesson_view.html',
                         lesson=lesson,
                         planning=planning,
                         is_current=is_current,
                         lesson_date=lesson_date,
                         time_remaining=time_remaining,
                         remaining_seconds=remaining_seconds,
                         students=students,
                         attendance_records=attendance_records,
                         imported_sanctions=imported_sanctions,
                         sanctions_data=sanctions_data,
                         seating_plan=seating_plan)

@planning_bp.route('/get-class-resources/<int:classroom_id>')
@login_required
def get_class_resources(classroom_id):
    """Récupérer les ressources d'une classe avec structure hiérarchique et épinglage"""
    try:
        from models.student import ClassFile
        from models.classroom import Classroom
        
        # Vérifier que la classe appartient à l'utilisateur
        classroom = Classroom.query.filter_by(
            id=classroom_id,
            user_id=current_user.id
        ).first()
        
        if not classroom:
            return jsonify({'success': False, 'message': 'Classe introuvable'}), 404
        
        # Récupérer tous les fichiers de la classe, triés par épinglage puis par nom
        class_files = ClassFile.query.filter_by(
            classroom_id=classroom_id
        ).order_by(
            ClassFile.is_pinned.desc(),
            ClassFile.pin_order.asc(),
            ClassFile.original_filename.asc()
        ).all()
        
        # Organiser les fichiers par structure hiérarchique
        files_data = []
        pinned_files = []
        
        for file in class_files:
            # Extraire le chemin du dossier depuis la description
            folder_path = ''
            if file.description and "Copié dans le dossier:" in file.description:
                folder_path = file.description.split("Copié dans le dossier:")[1].strip()
            
            file_data = {
                'id': file.id,
                'original_filename': file.original_filename,
                'file_type': file.file_type,
                'file_size': file.file_size,
                'folder_path': folder_path,
                'is_pinned': file.is_pinned,
                'pin_order': file.pin_order,
                'uploaded_at': file.uploaded_at.isoformat() if file.uploaded_at else None
            }
            
            if file.is_pinned:
                pinned_files.append(file_data)
            else:
                files_data.append(file_data)
        
        return jsonify({
            'success': True,
            'pinned_files': pinned_files,
            'files': files_data,
            'class_name': classroom.name
        })
        
    except Exception as e:
        print(f"Erreur lors de la récupération des ressources: {e}")
        return jsonify({
            'success': False,
            'message': 'Erreur lors de la récupération des ressources'
        }), 500

@planning_bp.route('/toggle-pin-resource', methods=['POST'])
@login_required
def toggle_pin_resource():
    """Épingler ou désépingler une ressource"""
    try:
        from models.student import ClassFile
        from models.classroom import Classroom
        
        data = request.get_json()
        file_id = data.get('file_id')
        
        if not file_id:
            return jsonify({'success': False, 'message': 'ID de fichier manquant'}), 400
        
        # Vérifier que le fichier appartient à une classe de l'utilisateur
        class_file = db.session.query(ClassFile).join(
            Classroom, ClassFile.classroom_id == Classroom.id
        ).filter(
            ClassFile.id == file_id,
            Classroom.user_id == current_user.id
        ).first()
        
        if not class_file:
            return jsonify({'success': False, 'message': 'Fichier introuvable'}), 404
        
        # Basculer l'état d'épinglage
        class_file.is_pinned = not class_file.is_pinned
        
        if class_file.is_pinned:
            # Si on épingle, donner le prochain ordre d'épinglage
            max_pin_order = db.session.query(db.func.max(ClassFile.pin_order)).filter_by(
                classroom_id=class_file.classroom_id,
                is_pinned=True
            ).scalar() or 0
            class_file.pin_order = max_pin_order + 1
        else:
            # Si on désépingle, remettre l'ordre à 0
            class_file.pin_order = 0
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'is_pinned': class_file.is_pinned,
            'message': f'Fichier {"épinglé" if class_file.is_pinned else "désépinglé"}'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Erreur lors de l'épinglage: {e}")
        return jsonify({'success': False, 'message': 'Erreur lors de l\'épinglage'}), 500

# Ajoutez cette route après la route lesson_view dans votre fichier planning.py

@planning_bp.route('/manage-classes')
@login_required
def manage_classes():
    """Gestion des classes - élèves, notes, fichiers et sanctions"""
    from models.student import Student, Grade
    from models.sanctions import SanctionTemplate, ClassroomSanctionImport
    from models.student_sanctions import StudentSanctionCount

    # Récupérer la classe sélectionnée (par défaut la première)
    selected_classroom_id = request.args.get('classroom', type=int)
    classrooms = current_user.classrooms.all()

    if not classrooms:
        flash('Veuillez d\'abord créer au moins une classe.', 'warning')
        return redirect(url_for('setup.manage_classrooms'))

    # Si aucune classe sélectionnée, prendre la première
    if not selected_classroom_id or not any(c.id == selected_classroom_id for c in classrooms):
        selected_classroom_id = classrooms[0].id

    selected_classroom = Classroom.query.get(selected_classroom_id)

    # Récupérer les données de la classe sélectionnée
    students = Student.query.filter_by(classroom_id=selected_classroom_id).order_by(Student.last_name, Student.first_name).all()
    
    # Convertir les étudiants en dictionnaires pour le JSON (utilisé en JavaScript)
    students_json = []
    for student in students:
        students_json.append({
            'id': student.id,
            'first_name': student.first_name,
            'last_name': student.last_name,
            'full_name': student.full_name,
            'email': student.email
        })

    # Récupérer les notes récentes
    recent_grades = Grade.query.filter_by(classroom_id=selected_classroom_id).order_by(Grade.date.desc()).limit(10).all()

    # Récupérer les modèles de sanctions importés dans cette classe
    imported_sanctions = db.session.query(SanctionTemplate).join(ClassroomSanctionImport).filter(
        ClassroomSanctionImport.classroom_id == selected_classroom_id,
        ClassroomSanctionImport.is_active == True,
        SanctionTemplate.user_id == current_user.id,
        SanctionTemplate.is_active == True
    ).order_by(SanctionTemplate.name).all()

    # Créer le tableau des coches pour chaque élève/sanction
    sanctions_data = {}
    for student in students:
        sanctions_data[student.id] = {}
        for sanction in imported_sanctions:
            # Récupérer ou créer le compteur de coches
            count = StudentSanctionCount.query.filter_by(
                student_id=student.id,
                template_id=sanction.id
            ).first()
            
            if not count:
                # Créer un nouveau compteur à 0
                count = StudentSanctionCount(
                    student_id=student.id,
                    template_id=sanction.id,
                    check_count=0
                )
                db.session.add(count)
            
            sanctions_data[student.id][sanction.id] = count.check_count
    
    # Sauvegarder les nouveaux compteurs créés
    db.session.commit()

    return render_template('planning/manage_classes.html',
                         classrooms=classrooms,
                         selected_classroom=selected_classroom,
                         selected_classroom_id=selected_classroom_id,
                         students=students,
                         students_json=students_json,
                         recent_grades=recent_grades,
                         imported_sanctions=imported_sanctions,
                         sanctions_data=sanctions_data)


@planning_bp.route('/update-sanction-count', methods=['POST'])
@login_required
def update_sanction_count():
    """Mettre à jour le nombre de coches pour une sanction d'un élève"""
    from models.student_sanctions import StudentSanctionCount
    
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Aucune donnée reçue'}), 400
    
    try:
        student_id = data.get('student_id')
        template_id = data.get('template_id')
        new_count = data.get('count')
        
        if student_id is None or template_id is None or new_count is None:
            return jsonify({'success': False, 'message': 'Données manquantes'}), 400
        
        # Vérifier que l'élève appartient à une classe de l'utilisateur
        from models.student import Student
        student = Student.query.join(Classroom).filter(
            Student.id == student_id,
            Classroom.user_id == current_user.id
        ).first()
        
        if not student:
            return jsonify({'success': False, 'message': 'Élève non trouvé'}), 404
        
        # Récupérer ou créer le compteur
        count_record = StudentSanctionCount.query.filter_by(
            student_id=student_id,
            template_id=template_id
        ).first()
        
        if not count_record:
            count_record = StudentSanctionCount(
                student_id=student_id,
                template_id=template_id,
                check_count=0
            )
            db.session.add(count_record)
        
        # Mettre à jour le compteur
        count_record.check_count = max(0, int(new_count))  # Ne pas aller en dessous de 0
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Compteur mis à jour',
            'new_count': count_record.check_count
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@planning_bp.route('/reset-all-sanctions', methods=['POST'])
@login_required
def reset_all_sanctions():
    """Réinitialiser toutes les coches d'une classe à zéro"""
    from models.student_sanctions import StudentSanctionCount
    from models.student import Student
    
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Aucune donnée reçue'}), 400
    
    try:
        classroom_id = data.get('classroom_id')
        
        if not classroom_id:
            return jsonify({'success': False, 'message': 'ID de classe manquant'}), 400
        
        # Vérifier que la classe appartient à l'utilisateur
        classroom = Classroom.query.filter_by(
            id=classroom_id,
            user_id=current_user.id
        ).first()
        
        if not classroom:
            return jsonify({'success': False, 'message': 'Classe non trouvée'}), 404
        
        # Récupérer tous les élèves de la classe
        student_ids = [s.id for s in Student.query.filter_by(classroom_id=classroom_id).all()]
        
        if student_ids:
            # Réinitialiser tous les compteurs à 0 pour cette classe
            StudentSanctionCount.query.filter(
                StudentSanctionCount.student_id.in_(student_ids)
            ).update({'check_count': 0}, synchronize_session=False)
            
            db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Toutes les coches ont été réinitialisées à zéro'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@planning_bp.route('/add-student', methods=['POST'])
@login_required
def add_student():
    """Ajouter un nouvel élève à une classe"""
    from models.student import Student

    data = request.get_json()

    if not data:
        return jsonify({'success': False, 'message': 'Aucune donnée reçue'}), 400

    try:
        # Vérifier que la classe appartient à l'utilisateur
        classroom_id = data.get('classroom_id')
        classroom = Classroom.query.filter_by(id=classroom_id, user_id=current_user.id).first()

        if not classroom:
            return jsonify({'success': False, 'message': 'Classe non trouvée'}), 404

        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        email = data.get('email', '').strip() if data.get('email') else None

        # Validation du prénom obligatoire
        if not first_name:
            return jsonify({'success': False, 'message': 'Le prénom est obligatoire'}), 400

        # Vérifier si un élève avec ce prénom existe déjà dans la classe
        existing_student = Student.query.filter_by(
            classroom_id=classroom_id,
            first_name=first_name
        ).first()

        # Si un élève avec ce prénom existe et qu'aucun nom n'est fourni
        if existing_student and not last_name:
            return jsonify({
                'success': False,
                'message': f'Un élève nommé {first_name} existe déjà dans cette classe. Veuillez ajouter un nom de famille pour les différencier.'
            }), 400

        # Créer le nouvel élève
        student = Student(
            classroom_id=classroom_id,
            first_name=first_name,
            last_name=last_name,
            email=email
        )

        db.session.add(student)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'{student.full_name} a été ajouté avec succès',
            'student': {
                'id': student.id,
                'first_name': student.first_name,
                'last_name': student.last_name,
                'full_name': student.full_name,
                'email': student.email,
                'initials': student.first_name[0] + (student.last_name[0] if student.last_name else '')
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@planning_bp.route('/delete-student/<int:student_id>', methods=['DELETE'])
@login_required
def delete_student(student_id):
    """Supprimer un élève"""
    from models.student import Student

    try:
        # Vérifier que l'élève existe et appartient à une classe de l'utilisateur
        student = Student.query.join(Classroom).filter(
            Student.id == student_id,
            Classroom.user_id == current_user.id
        ).first()

        if not student:
            return jsonify({'success': False, 'message': 'Élève non trouvé'}), 404

        student_name = student.full_name

        # Supprimer l'élève (les notes seront supprimées automatiquement grâce à cascade)
        db.session.delete(student)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'{student_name} a été supprimé avec succès'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@planning_bp.route('/update-student', methods=['PUT'])
@login_required
def update_student():
    """Modifier un élève"""
    from models.student import Student

    data = request.get_json()
    student_id = data.get('student_id')

    if not data or not student_id:
        return jsonify({'success': False, 'message': 'Données invalides'}), 400

    try:
        # Vérifier que l'élève existe et appartient à une classe de l'utilisateur
        student = Student.query.join(Classroom).filter(
            Student.id == student_id,
            Classroom.user_id == current_user.id
        ).first()

        if not student:
            return jsonify({'success': False, 'message': 'Élève non trouvé'}), 404

        # Récupérer les nouvelles valeurs
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        email = data.get('email', '').strip() if data.get('email') else None

        # Validation du prénom obligatoire
        if not first_name:
            return jsonify({'success': False, 'message': 'Le prénom est obligatoire'}), 400

        # Si le prénom change, vérifier les doublons
        if first_name != student.first_name:
            existing_student = Student.query.filter(
                Student.classroom_id == student.classroom_id,
                Student.first_name == first_name,
                Student.id != student_id
            ).first()

            if existing_student and not last_name:
                return jsonify({
                    'success': False,
                    'message': f'Un autre élève nommé {first_name} existe déjà dans cette classe. Veuillez ajouter un nom de famille pour les différencier.'
                }), 400

        # Mettre à jour l'élève
        student.first_name = first_name
        student.last_name = last_name
        student.email = email

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'{student.full_name} a été modifié avec succès',
            'student': {
                'id': student.id,
                'first_name': student.first_name,
                'last_name': student.last_name,
                'full_name': student.full_name,
                'email': student.email,
                'initials': student.first_name[0] + (student.last_name[0] if student.last_name else '')
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@planning_bp.route('/get-student/<int:student_id>')
@login_required
def get_student(student_id):
    """Récupérer les informations d'un élève"""
    from models.student import Student

    try:
        # Vérifier que l'élève existe et appartient à une classe de l'utilisateur
        student = Student.query.join(Classroom).filter(
            Student.id == student_id,
            Classroom.user_id == current_user.id
        ).first()

        if not student:
            return jsonify({'success': False, 'message': 'Élève non trouvé'}), 404

        return jsonify({
            'success': True,
            'student': {
                'id': student.id,
                'first_name': student.first_name,
                'last_name': student.last_name or '',
                'email': student.email or ''
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@planning_bp.route('/update-attendance', methods=['POST'])
@login_required
def update_attendance():
    """Mettre à jour la présence d'un élève"""
    from models.attendance import Attendance
    from models.student import Student

    data = request.get_json()

    if not data:
        return jsonify({'success': False, 'message': 'Aucune donnée reçue'}), 400

    try:
        student_id = data.get('student_id')
        classroom_id = data.get('classroom_id')
        date_str = data.get('date')
        period_number = data.get('period_number')
        status = data.get('status', 'present')
        late_minutes = data.get('late_minutes')

        # Convertir la date
        date = datetime.strptime(date_str, '%Y-%m-%d').date()

        # Vérifier que l'élève appartient à une classe de l'utilisateur
        student = Student.query.join(Classroom).filter(
            Student.id == student_id,
            Classroom.user_id == current_user.id
        ).first()

        if not student:
            return jsonify({'success': False, 'message': 'Élève non trouvé'}), 404

        # Chercher un enregistrement existant
        attendance = Attendance.query.filter_by(
            student_id=student_id,
            date=date,
            period_number=period_number
        ).first()

        if attendance:
            # Mettre à jour l'existant
            attendance.status = status
            attendance.late_minutes = late_minutes if status == 'late' and late_minutes else None
            attendance.updated_at = datetime.utcnow()
        else:
            # Créer un nouveau
            attendance = Attendance(
                student_id=student_id,
                classroom_id=classroom_id,
                user_id=current_user.id,
                date=date,
                period_number=period_number,
                status=status,
                late_minutes=late_minutes if status == 'late' and late_minutes else None
            )
            db.session.add(attendance)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Présence mise à jour',
            'attendance': {
                'student_id': student_id,
                'status': status,
                'late_minutes': attendance.late_minutes
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@planning_bp.route('/get-attendance-stats/<date>/<int:period>')
@login_required
def get_attendance_stats(date, period):
    """Obtenir les statistiques de présence pour un cours"""
    from models.attendance import Attendance

    try:
        # Convertir la date
        course_date = datetime.strptime(date, '%Y-%m-%d').date()

        # Récupérer toutes les présences pour ce cours
        attendances = Attendance.query.filter_by(
            user_id=current_user.id,
            date=course_date,
            period_number=period
        ).all()

        stats = {
            'present': 0,
            'absent': 0,
            'late': 0,
            'total': 0
        }

        for attendance in attendances:
            stats['total'] += 1
            stats[attendance.status] += 1

        return jsonify({
            'success': True,
            'stats': stats
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@planning_bp.route('/save-lesson-planning', methods=['POST'])
@login_required
def save_lesson_planning():
    """Sauvegarder la planification depuis la vue leçon"""
    data = request.get_json()

    if not data:
        return jsonify({'success': False, 'message': 'Aucune donnée reçue'}), 400

    try:
        date_str = data.get('date')
        period_number = data.get('period_number')
        classroom_id = data.get('classroom_id')
        title = data.get('title', '').strip()
        description = data.get('description', '').strip()
        checklist_states = data.get('checklist_states', {})

        # Convertir la date
        planning_date = datetime.strptime(date_str, '%Y-%m-%d').date()

        # Vérifier la classe
        classroom = Classroom.query.filter_by(id=classroom_id, user_id=current_user.id).first()
        if not classroom:
            return jsonify({'success': False, 'message': 'Classe non trouvée'}), 404

        # Chercher un planning existant
        existing = Planning.query.filter_by(
            user_id=current_user.id,
            date=planning_date,
            period_number=period_number
        ).first()

        if existing:
            # Mettre à jour
            existing.classroom_id = classroom_id
            existing.title = title
            existing.description = description
            existing.set_checklist_states(checklist_states)
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
            planning.set_checklist_states(checklist_states)
            db.session.add(planning)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Planification enregistrée avec succès',
            'planning': {
                'title': title,
                'description': description
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
# Vérifier que cette route existe à la fin du fichier routes/planning.py
# Si elle n'existe pas, l'ajouter après la route save_lesson_planning

@planning_bp.route('/update-checklist-states', methods=['POST'])
@login_required
def update_checklist_states():
    """Mettre à jour uniquement les états des checkboxes"""
    data = request.get_json()

    if not data:
        return jsonify({'success': False, 'message': 'Aucune donnée reçue'}), 400

    try:
        date_str = data.get('date')
        period_number = data.get('period_number')
        checklist_states = data.get('checklist_states', {})

        # Convertir la date
        planning_date = datetime.strptime(date_str, '%Y-%m-%d').date()

        # Chercher le planning existant
        planning = Planning.query.filter_by(
            user_id=current_user.id,
            date=planning_date,
            period_number=period_number
        ).first()

        if planning:
            # Mettre à jour les états des checkboxes
            planning.set_checklist_states(checklist_states)
            db.session.commit()

            return jsonify({
                'success': True,
                'message': 'États des checkboxes mis à jour'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Planification non trouvée'
            }), 404

    except Exception as e:
        db.session.rollback()
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
                    'description': planning.description,
                    'checklist_states': planning.get_checklist_states()  # Ajouter les états des checkboxes
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
                        'description': '',
                        'checklist_states': {}
                    }
                })

        return jsonify({'success': True, 'planning': None})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@planning_bp.route('/save_file_annotations', methods=['POST'])
@login_required
def save_file_annotations():
    """Sauvegarde les annotations d'un fichier"""
    try:
        print(f"[DEBUG] === DEBUT save_file_annotations ===")
        
        data = request.get_json()
        file_id = data.get('file_id')
        annotations = data.get('annotations', [])
        
        print(f"[DEBUG] file_id={file_id}, nb_annotations={len(annotations)}")
        
        if not file_id:
            return jsonify({'success': False, 'message': 'ID de fichier manquant'}), 400
        
        # Vérifier que le fichier appartient à l'utilisateur (fichier de classe)
        from models.file_manager import UserFile, FileAnnotation
        from models.student import ClassFile
        
        # D'abord chercher dans user_files
        user_file = UserFile.query.filter_by(id=file_id, user_id=current_user.id).first()
        file_found = bool(user_file)
        
        if not user_file:
            # Vérifier si c'est un fichier de classe
            class_file = ClassFile.query.filter_by(id=file_id).first()
            if class_file and class_file.classroom.user_id == current_user.id:
                file_found = True
                print(f"[DEBUG] Fichier de classe trouvé: {class_file.original_filename}")
            else:
                print(f"[DEBUG] Fichier non trouvé ou accès refusé")
                return jsonify({'success': False, 'message': 'Fichier non trouvé'}), 404
        
        if not file_found:
            return jsonify({'success': False, 'message': 'Fichier non trouvé'}), 404
        
        print(f"[DEBUG] Fichier validé, suppression des anciennes annotations...")
        
        # Supprimer les anciennes annotations
        deleted_count = FileAnnotation.query.filter_by(
            file_id=file_id,
            user_id=current_user.id
        ).delete()
        
        print(f"[DEBUG] {deleted_count} anciennes annotations supprimées")
        
        # Sauvegarder les nouvelles annotations
        if annotations:
            print(f"[DEBUG] Création de nouvelles annotations...")
            new_annotation = FileAnnotation(
                file_id=file_id,
                user_id=current_user.id,
                annotations_data=annotations
            )
            db.session.add(new_annotation)
            print(f"[DEBUG] Nouvelles annotations ajoutées à la session")
        
        db.session.commit()
        print(f"[DEBUG] === FIN save_file_annotations - SUCCESS ===")
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"[ERROR] Erreur dans save_file_annotations: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@planning_bp.route('/check-sanction-thresholds', methods=['POST'])
@login_required
def check_sanction_thresholds():
    """Vérifier les seuils de sanctions franchis pendant la période"""
    from models.sanctions import SanctionTemplate, SanctionThreshold, SanctionOption, ClassroomSanctionImport
    from models.student_sanctions import StudentSanctionCount
    from models.student import Student
    import random
    
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Aucune donnée reçue'}), 400
    
    try:
        classroom_id = data.get('classroom_id')
        initial_counts = data.get('initial_counts', {})  # Compteurs au début de la période
        
        # Vérifier que la classe appartient à l'utilisateur
        classroom = Classroom.query.filter_by(id=classroom_id, user_id=current_user.id).first()
        if not classroom:
            return jsonify({'success': False, 'message': 'Classe non trouvée'}), 404
        
        # Récupérer les sanctions importées dans cette classe
        imported_sanctions = db.session.query(SanctionTemplate).join(ClassroomSanctionImport).filter(
            ClassroomSanctionImport.classroom_id == classroom_id,
            ClassroomSanctionImport.is_active == True,
            SanctionTemplate.user_id == current_user.id,
            SanctionTemplate.is_active == True
        ).all()
        
        # Récupérer les élèves de la classe
        students = Student.query.filter_by(classroom_id=classroom_id).all()
        
        threshold_breaches = []
        
        for student in students:
            for sanction_template in imported_sanctions:
                # Récupérer le compteur actuel
                current_count = StudentSanctionCount.query.filter_by(
                    student_id=student.id,
                    template_id=sanction_template.id
                ).first()
                
                current_value = current_count.check_count if current_count else 0
                initial_value = int(initial_counts.get(f"{student.id}_{sanction_template.id}", 0))
                
                # Vérifier quels seuils ont été franchis pendant cette période
                thresholds = sanction_template.thresholds.order_by(SanctionThreshold.check_count).all()
                
                for threshold in thresholds:
                    # Seuil franchi si: initial < seuil <= current
                    if initial_value < threshold.check_count <= current_value:
                        # Tirer au sort une sanction pour ce seuil
                        available_options = threshold.sanctions.filter_by(is_active=True).all()
                        if available_options:
                            selected_option = random.choice(available_options)
                            
                            threshold_breaches.append({
                                'student_id': student.id,
                                'student_name': student.full_name,
                                'sanction_template': sanction_template.name,
                                'threshold': threshold.check_count,
                                'sanction_text': selected_option.description,
                                'min_days_deadline': selected_option.min_days_deadline,
                                'option_id': selected_option.id
                            })
        
        return jsonify({
            'success': True,
            'threshold_breaches': threshold_breaches
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@planning_bp.route('/calculate-next-lesson-date', methods=['POST'])
@login_required
def calculate_next_lesson_date():
    """Calculer la prochaine date de cours pour une classe après un délai minimum"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Aucune donnée reçue'}), 400
    
    try:
        classroom_id = data.get('classroom_id')
        min_days = data.get('min_days', 0)
        current_date = datetime.strptime(data.get('current_date'), '%Y-%m-%d').date()
        
        # Date minimale = date actuelle + nombre de jours minimum
        min_date = current_date + timedelta(days=min_days)
        
        # Récupérer l'horaire type pour cette classe
        schedules = Schedule.query.filter_by(
            user_id=current_user.id,
            classroom_id=classroom_id
        ).order_by(Schedule.weekday, Schedule.period_number).all()
        
        if not schedules:
            return jsonify({
                'success': True,
                'next_date': None,
                'message': 'Aucun cours programmé pour cette classe'
            })
        
        # Chercher la prochaine date de cours
        search_date = min_date
        max_search_days = 365  # Limiter la recherche à un an
        
        for days_ahead in range(max_search_days):
            check_date = search_date + timedelta(days=days_ahead)
            weekday = check_date.weekday()
            
            # Vérifier si c'est un jour de vacances
            if is_holiday(check_date, current_user):
                continue
            
            # Vérifier si cette classe a cours ce jour
            day_schedule = [s for s in schedules if s.weekday == weekday]
            if day_schedule:
                # Prendre la première période du jour
                first_period = min(day_schedule, key=lambda x: x.period_number)
                return jsonify({
                    'success': True,
                    'next_date': check_date.strftime('%Y-%m-%d'),
                    'weekday': weekday,
                    'period_number': first_period.period_number,
                    'formatted_date': check_date.strftime('%d/%m/%Y')
                })
        
        return jsonify({
            'success': True,
            'next_date': None,
            'message': 'Aucune date trouvée dans les 365 prochains jours'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@planning_bp.route('/add-sanction-to-planning', methods=['POST'])
@login_required
def add_sanction_to_planning():
    """Ajouter une sanction à récupérer dans la planification d'un cours"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Aucune donnée reçue'}), 400
    
    try:
        date_str = data.get('date')
        period_number = data.get('period_number')
        classroom_id = data.get('classroom_id')
        student_name = data.get('student_name')
        sanction_text = data.get('sanction_text')
        
        planning_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Chercher une planification existante
        existing = Planning.query.filter_by(
            user_id=current_user.id,
            date=planning_date,
            period_number=period_number
        ).first()
        
        # Texte de la sanction à ajouter
        sanction_reminder = f"☐ {student_name} : {sanction_text}"
        
        if existing:
            # Ajouter à la description existante
            if existing.description:
                existing.description += f"\n\n{sanction_reminder}"
            else:
                existing.description = sanction_reminder
        else:
            # Créer une nouvelle planification
            planning = Planning(
                user_id=current_user.id,
                classroom_id=classroom_id,
                date=planning_date,
                period_number=period_number,
                title="",
                description=sanction_reminder
            )
            db.session.add(planning)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Sanction ajoutée à la planification'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@planning_bp.route('/get_file_annotations/<int:file_id>')
@login_required 
def get_file_annotations(file_id):
    """Récupère les annotations d'un fichier"""
    try:
        print(f"[DEBUG] === DEBUT get_file_annotations file_id={file_id} ===")
        
        # Vérifier que le fichier appartient à l'utilisateur
        from models.file_manager import UserFile, FileAnnotation
        from models.student import ClassFile
        
        # D'abord chercher dans user_files
        user_file = UserFile.query.filter_by(id=file_id, user_id=current_user.id).first()
        file_found = bool(user_file)
        
        if not user_file:
            # Vérifier si c'est un fichier de classe
            class_file = ClassFile.query.filter_by(id=file_id).first()
            if class_file and class_file.classroom.user_id == current_user.id:
                file_found = True
                print(f"[DEBUG] Fichier de classe trouvé: {class_file.original_filename}")
            else:
                print(f"[DEBUG] Fichier non trouvé ou accès refusé")
                return jsonify({'success': False, 'message': 'Fichier non trouvé'}), 404
        
        if not file_found:
            return jsonify({'success': False, 'message': 'Fichier non trouvé'}), 404
        
        print(f"[DEBUG] Recherche des annotations...")
        
        # Récupérer les annotations
        annotation = FileAnnotation.query.filter_by(
            file_id=file_id,
            user_id=current_user.id
        ).first()
        
        annotations = annotation.annotations_data if annotation else []
        
        print(f"[DEBUG] {len(annotations)} annotations trouvées")
        print(f"[DEBUG] === FIN get_file_annotations - SUCCESS ===")
        
        return jsonify({
            'success': True,
            'annotations': annotations
        })
        
    except Exception as e:
        print(f"[ERROR] Erreur dans get_file_annotations: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@planning_bp.route('/save-seating-plan', methods=['POST'])
@login_required
def save_seating_plan():
    """Sauvegarder un plan de classe"""
    from models.seating_plan import SeatingPlan
    import json
    
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Aucune donnée reçue'}), 400
    
    try:
        classroom_id = data.get('classroom_id')
        plan_data = data.get('plan_data')
        name = data.get('name', 'Plan par défaut')
        
        if not classroom_id or not plan_data:
            return jsonify({'success': False, 'message': 'Données manquantes'}), 400
        
        # Vérifier que la classe appartient à l'utilisateur
        classroom = Classroom.query.filter_by(id=classroom_id, user_id=current_user.id).first()
        if not classroom:
            return jsonify({'success': False, 'message': 'Classe non trouvée'}), 404
        
        # Désactiver les anciens plans pour cette classe
        SeatingPlan.query.filter_by(
            classroom_id=classroom_id,
            user_id=current_user.id,
            is_active=True
        ).update({'is_active': False})
        
        # Créer le nouveau plan
        seating_plan = SeatingPlan(
            classroom_id=classroom_id,
            user_id=current_user.id,
            name=name,
            plan_data=json.dumps(plan_data),
            is_active=True
        )
        
        db.session.add(seating_plan)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Plan de classe sauvegardé avec succès',
            'plan_id': seating_plan.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@planning_bp.route('/load-seating-plan/<int:classroom_id>')
@login_required
def load_seating_plan(classroom_id):
    """Charger le plan de classe actif"""
    from models.seating_plan import SeatingPlan
    import json
    
    try:
        # Vérifier que la classe appartient à l'utilisateur
        classroom = Classroom.query.filter_by(id=classroom_id, user_id=current_user.id).first()
        if not classroom:
            return jsonify({'success': False, 'message': 'Classe non trouvée'}), 404
        
        # Récupérer le plan actif
        seating_plan = SeatingPlan.query.filter_by(
            classroom_id=classroom_id,
            user_id=current_user.id,
            is_active=True
        ).first()
        
        if seating_plan:
            return jsonify({
                'success': True,
                'plan_data': json.loads(seating_plan.plan_data),
                'name': seating_plan.name,
                'plan_id': seating_plan.id
            })
        else:
            return jsonify({
                'success': True,
                'plan_data': None,
                'message': 'Aucun plan sauvegardé pour cette classe'
            })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ===== ROUTES POUR LA GESTION DES GROUPES =====

@planning_bp.route('/get-groups/<int:classroom_id>')
@login_required
def get_groups(classroom_id):
    """Récupérer tous les groupes d'une classe"""
    try:
        from models.student_group import StudentGroup, StudentGroupMembership
        from models.student import Student
        
        # Vérifier que la classe appartient à l'utilisateur
        classroom = Classroom.query.filter_by(id=classroom_id, user_id=current_user.id).first()
        if not classroom:
            return jsonify({'success': False, 'message': 'Classe non trouvée'}), 404
        
        # Récupérer les groupes de cette classe
        groups = StudentGroup.query.filter_by(
            classroom_id=classroom_id,
            user_id=current_user.id
        ).all()
        
        groups_data = []
        for group in groups:
            # Récupérer les élèves de ce groupe
            students = db.session.query(Student).join(
                StudentGroupMembership,
                Student.id == StudentGroupMembership.student_id
            ).filter(
                StudentGroupMembership.group_id == group.id
            ).all()
            
            groups_data.append({
                'id': group.id,
                'name': group.name,
                'description': group.description,
                'color': group.color,
                'students': [{
                    'id': student.id,
                    'first_name': student.first_name,
                    'last_name': student.last_name
                } for student in students],
                'student_count': len(students)
            })
        
        return jsonify({
            'success': True,
            'groups': groups_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@planning_bp.route('/get-group/<int:group_id>')
@login_required
def get_group(group_id):
    """Récupérer un groupe spécifique"""
    try:
        from models.student_group import StudentGroup, StudentGroupMembership
        
        # Vérifier que le groupe appartient à l'utilisateur
        group = StudentGroup.query.filter_by(id=group_id, user_id=current_user.id).first()
        if not group:
            return jsonify({'success': False, 'message': 'Groupe non trouvé'}), 404
        
        # Récupérer les IDs des élèves de ce groupe
        student_ids = [membership.student_id for membership in group.memberships]
        
        return jsonify({
            'success': True,
            'group': {
                'id': group.id,
                'name': group.name,
                'description': group.description,
                'color': group.color,
                'student_ids': student_ids
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@planning_bp.route('/create-group', methods=['POST'])
@login_required
def create_group():
    """Créer un nouveau groupe"""
    try:
        from models.student_group import StudentGroup, StudentGroupMembership
        from models.student import Student
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Aucune donnée reçue'}), 400
        
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        color = data.get('color', '#4F46E5')
        classroom_id = data.get('classroom_id')
        student_ids = data.get('student_ids', [])
        
        if not name:
            return jsonify({'success': False, 'message': 'Le nom du groupe est obligatoire'}), 400
        
        # Vérifier que la classe appartient à l'utilisateur
        classroom = Classroom.query.filter_by(id=classroom_id, user_id=current_user.id).first()
        if not classroom:
            return jsonify({'success': False, 'message': 'Classe non trouvée'}), 404
        
        # Vérifier que tous les élèves appartiennent à cette classe
        if student_ids:
            valid_students = Student.query.filter(
                Student.id.in_(student_ids),
                Student.classroom_id == classroom_id
            ).count()
            if valid_students != len(student_ids):
                return jsonify({'success': False, 'message': 'Certains élèves ne sont pas valides'}), 400
        
        # Créer le groupe
        group = StudentGroup(
            classroom_id=classroom_id,
            user_id=current_user.id,
            name=name,
            description=description or None,
            color=color
        )
        db.session.add(group)
        db.session.flush()  # Pour obtenir l'ID du groupe
        
        # Ajouter les élèves au groupe
        for student_id in student_ids:
            membership = StudentGroupMembership(
                group_id=group.id,
                student_id=student_id
            )
            db.session.add(membership)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Groupe "{name}" créé avec succès',
            'group_id': group.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@planning_bp.route('/update-group/<int:group_id>', methods=['POST'])
@login_required
def update_group(group_id):
    """Mettre à jour un groupe existant"""
    try:
        from models.student_group import StudentGroup, StudentGroupMembership
        from models.student import Student
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Aucune donnée reçue'}), 400
        
        # Vérifier que le groupe appartient à l'utilisateur
        group = StudentGroup.query.filter_by(id=group_id, user_id=current_user.id).first()
        if not group:
            return jsonify({'success': False, 'message': 'Groupe non trouvé'}), 404
        
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        color = data.get('color', '#4F46E5')
        student_ids = data.get('student_ids', [])
        
        if not name:
            return jsonify({'success': False, 'message': 'Le nom du groupe est obligatoire'}), 400
        
        # Vérifier que tous les élèves appartiennent à cette classe
        if student_ids:
            valid_students = Student.query.filter(
                Student.id.in_(student_ids),
                Student.classroom_id == group.classroom_id
            ).count()
            if valid_students != len(student_ids):
                return jsonify({'success': False, 'message': 'Certains élèves ne sont pas valides'}), 400
        
        # Mettre à jour le groupe
        group.name = name
        group.description = description or None
        group.color = color
        
        # Supprimer les anciennes associations
        StudentGroupMembership.query.filter_by(group_id=group_id).delete()
        
        # Ajouter les nouvelles associations
        for student_id in student_ids:
            membership = StudentGroupMembership(
                group_id=group_id,
                student_id=student_id
            )
            db.session.add(membership)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Groupe "{name}" mis à jour avec succès'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@planning_bp.route('/delete-group/<int:group_id>', methods=['DELETE'])
@login_required
def delete_group(group_id):
    """Supprimer un groupe"""
    try:
        from models.student_group import StudentGroup
        
        # Vérifier que le groupe appartient à l'utilisateur
        group = StudentGroup.query.filter_by(id=group_id, user_id=current_user.id).first()
        if not group:
            return jsonify({'success': False, 'message': 'Groupe non trouvé'}), 404
        
        group_name = group.name
        db.session.delete(group)  # Les memberships seront supprimés automatiquement (cascade)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Groupe "{group_name}" supprimé avec succès'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@planning_bp.route('/api/slot/<date_str>/<int:period>')
@login_required
def get_slot_data(date_str, period):
    """API endpoint pour récupérer les données d'un slot de planning"""
    try:
        planning_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        weekday = planning_date.weekday()
        
        # Récupérer la période pour les horaires
        periods = calculate_periods(current_user)
        period_info = next((p for p in periods if p['number'] == period), None)
        
        if not period_info:
            return jsonify({'success': False, 'message': 'Période invalide'}), 400
        
        # Chercher un planning existant
        planning = Planning.query.filter_by(
            user_id=current_user.id,
            date=planning_date,
            period_number=period
        ).first()
        
        # Récupérer l'horaire type par défaut
        schedule = Schedule.query.filter_by(
            user_id=current_user.id,
            weekday=weekday,
            period_number=period
        ).first()
        
        result = {
            'period': period,
            'period_start': period_info['start'].strftime('%H:%M'),
            'period_end': period_info['end'].strftime('%H:%M'),
            'has_schedule': schedule is not None,
            'default_classroom_id': schedule.classroom_id if schedule else None,
            'has_planning': planning is not None
        }
        
        if planning:
            result.update({
                'classroom_id': planning.classroom_id,
                'title': planning.title or '',
                'description': planning.description or '',
                'checklist_states': planning.get_checklist_states()
            })
        elif schedule:
            result.update({
                'classroom_id': schedule.classroom_id,
                'title': '',
                'description': '',
                'checklist_states': {}
            })
        else:
            result.update({
                'classroom_id': None,
                'title': '',
                'description': '',
                'checklist_states': {}
            })
        
        return jsonify({
            'success': True,
            'slot': result
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

