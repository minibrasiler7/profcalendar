#!/usr/bin/env python3
"""Script de débogage pour tester la collaboration"""

from app import create_app
from extensions import db
from models.user import User
from models.class_collaboration import TeacherAccessCode

app = create_app()

with app.app_context():
    # Afficher tous les enseignants
    print("\n=== ENSEIGNANTS ENREGISTRÉS ===")
    teachers = User.query.all()
    for teacher in teachers:
        print(f"ID: {teacher.id}, Username: {teacher.username}, Email: {teacher.email}")
        master_classes = teacher.get_master_classes()
        if master_classes:
            print(f"  - Maître de classe pour: {[mc.classroom.name for mc in master_classes]}")
    
    # Afficher tous les codes d'accès
    print("\n=== CODES D'ACCÈS ACTIFS ===")
    codes = TeacherAccessCode.query.filter_by(is_active=True).all()
    for code in codes:
        print(f"Code: {code.code}")
        print(f"  - Créé par: {code.master_teacher.username}")
        print(f"  - Utilisations: {code.current_uses}/{code.max_uses if code.max_uses else 'illimité'}")
        print(f"  - Expire: {code.expires_at if code.expires_at else 'jamais'}")
    
    if not codes:
        print("Aucun code d'accès actif trouvé.")