"""
Script pour vérifier les vacances et le comptage des semaines
"""

from app import create_app, db
from models.user import User, Holiday
from datetime import datetime, timedelta

app = create_app()

def get_week_dates(week_date):
    """Retourne les dates du lundi au vendredi de la semaine"""
    days_since_monday = week_date.weekday()
    monday = week_date - timedelta(days=days_since_monday)

    week_dates = []
    for i in range(5):
        week_dates.append(monday + timedelta(days=i))

    return week_dates

with app.app_context():
    print("=== Vérification des vacances et du comptage des semaines ===\n")

    # Récupérer le premier utilisateur
    user = User.query.first()
    if not user:
        print("Aucun utilisateur trouvé")
        exit()

    print(f"Utilisateur: {user.username}")
    print(f"Année scolaire: {user.school_year_start} - {user.school_year_end}\n")

    # Afficher toutes les vacances
    print("Vacances enregistrées:")
    holidays = user.holidays.all()
    for holiday in holidays:
        print(f"  - {holiday.name}: {holiday.start_date} au {holiday.end_date}")

    print("\n=== Comptage des semaines ===\n")

    # Simuler le comptage
    current_date = user.school_year_start
    current_date -= timedelta(days=current_date.weekday())  # Aller au lundi

    week_number = 0
    week_count = 0

    while current_date <= user.school_year_end and week_count < 20:  # Limiter à 20 semaines pour le debug
        week_dates = get_week_dates(current_date)
        week_holiday = None

        # Vérifier les vacances
        for holiday in holidays:
            days_in_holiday = 0
            for i in range(5):  # Lundi à vendredi
                if holiday.start_date <= week_dates[i] <= holiday.end_date:
                    days_in_holiday += 1

            if days_in_holiday >= 3:
                week_holiday = holiday.name
                break

        # Incrémenter seulement si pas de vacances
        if not week_holiday and current_date >= user.school_year_start:
            week_number += 1

        # Afficher le résultat
        if week_holiday:
            print(f"Semaine du {week_dates[0].strftime('%d/%m/%Y')}: {week_holiday}")
        else:
            print(f"Semaine du {week_dates[0].strftime('%d/%m/%Y')}: S{week_number}")

        current_date += timedelta(days=7)
        week_count += 1
