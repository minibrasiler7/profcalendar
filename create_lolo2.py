#!/usr/bin/env python3
"""
Créer un nouvel utilisateur lolo2 identique à lolo strauch mais avec un profil vide
"""

from app import create_app
from extensions import db
from models.user import User, Holiday, Break
from models.classroom import Classroom
from models.schedule import Schedule
from datetime import datetime, date, time

def create_lolo2_user():
    app = create_app()
    
    with app.app_context():
        # Récupérer l'utilisateur lolo strauch
        lolo_strauch = User.query.filter_by(username='lolo strauch').first()
        
        if not lolo_strauch:
            print("❌ Utilisateur 'lolo strauch' introuvable")
            return
        
        # Vérifier si lolo2 existe déjà
        existing_lolo2 = User.query.filter_by(username='lolo2').first()
        if existing_lolo2:
            print("⚠️  L'utilisateur 'lolo2' existe déjà. Suppression...")
            db.session.delete(existing_lolo2)
            db.session.commit()
        
        print("📝 Création de l'utilisateur lolo2...")
        
        # Créer le nouvel utilisateur avec les mêmes paramètres de configuration
        lolo2 = User(
            username='lolo2',
            email='lolo2@example.com',
            setup_completed=lolo_strauch.setup_completed,
            schedule_completed=lolo_strauch.schedule_completed,
            school_year_start=lolo_strauch.school_year_start,
            school_year_end=lolo_strauch.school_year_end,
            day_start_time=lolo_strauch.day_start_time,
            day_end_time=lolo_strauch.day_end_time,
            period_duration=lolo_strauch.period_duration,
            break_duration=lolo_strauch.break_duration
        )
        lolo2.set_password('lolo2')  # Mot de passe simple pour les tests
        
        db.session.add(lolo2)
        db.session.flush()  # Pour obtenir l'ID
        
        print(f"✅ Utilisateur lolo2 créé avec l'ID {lolo2.id}")
        
        # Copier les vacances
        print("📅 Copie des vacances...")
        for holiday in lolo_strauch.holidays:
            new_holiday = Holiday(
                user_id=lolo2.id,
                name=holiday.name,
                start_date=holiday.start_date,
                end_date=holiday.end_date
            )
            db.session.add(new_holiday)
        
        # Copier les pauses
        print("⏰ Copie des pauses...")
        for break_item in lolo_strauch.breaks:
            new_break = Break(
                user_id=lolo2.id,
                name=break_item.name,
                start_time=break_item.start_time,
                end_time=break_item.end_time,
                is_major_break=break_item.is_major_break
            )
            db.session.add(new_break)
        
        # Copier les classes
        print("🏫 Copie des classes...")
        for classroom in lolo_strauch.classrooms:
            new_classroom = Classroom(
                user_id=lolo2.id,
                name=classroom.name,
                color=classroom.color
            )
            db.session.add(new_classroom)
            print(f"   - Classe copiée: {classroom.name}")
        
        # Copier les horaires
        print("📋 Copie des horaires...")
        for schedule in lolo_strauch.schedules:
            new_schedule = Schedule(
                user_id=lolo2.id,
                day_of_week=schedule.day_of_week,
                period_number=schedule.period_number,
                subject=schedule.subject,
                classroom_name=schedule.classroom_name
            )
            db.session.add(new_schedule)
        
        # Commit toutes les modifications
        db.session.commit()
        
        print("✅ Utilisateur lolo2 créé avec succès!")
        print(f"📧 Email: lolo2@example.com")
        print(f"🔑 Mot de passe: lolo2")
        print("")
        print("🗂️  IMPORTANT: Le gestionnaire de fichiers est vide")
        print("📂 IMPORTANT: Aucun fichier dans les classes")
        print("")
        print("🧪 Utilisez ce compte pour tester le système de copie de fichiers.")

if __name__ == '__main__':
    create_lolo2_user()