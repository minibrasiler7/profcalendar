#!/usr/bin/env python
"""
Script pour initialiser Flask-Migrate et ajouter la colonne checklist_states
"""

from app import create_app, db
from flask_migrate import init, migrate, upgrade
import os

# Créer l'application
app = create_app()

with app.app_context():
    # Option 1 : Initialiser Flask-Migrate si ce n'est pas déjà fait
    if not os.path.exists('migrations'):
        print("Initialisation de Flask-Migrate...")
        init()
        print("✓ Flask-Migrate initialisé")

    # Option 2 : Créer la migration
    print("\nCréation de la migration...")
    try:
        migrate(message='Add checklist_states to Planning model')
        print("✓ Migration créée")
    except Exception as e:
        print(f"Note: {e}")

    # Option 3 : Appliquer la migration
    print("\nApplication de la migration...")
    try:
        upgrade()
        print("✓ Migration appliquée")
    except Exception as e:
        print(f"Erreur lors de l'application: {e}")

print("\n✅ Processus terminé !")
