#!/usr/bin/env python
"""
Script pour ajouter la colonne checklist_states directement dans SQLite
"""

from app import create_app, db
from sqlalchemy import text
import sys

app = create_app()

def check_column_exists():
    """Vérifie si la colonne existe déjà"""
    with app.app_context():
        result = db.session.execute(text(
            "SELECT COUNT(*) FROM pragma_table_info('plannings') WHERE name='checklist_states'"
        ))
        return result.scalar() > 0

def add_checklist_column():
    """Ajoute la colonne checklist_states à la table plannings"""
    with app.app_context():
        try:
            # Vérifier si la colonne existe déjà
            if check_column_exists():
                print("✓ La colonne 'checklist_states' existe déjà dans la table 'plannings'")
                return True

            # Ajouter la colonne
            print("Ajout de la colonne 'checklist_states'...")
            db.session.execute(text(
                "ALTER TABLE plannings ADD COLUMN checklist_states TEXT"
            ))
            db.session.commit()
            print("✓ Colonne 'checklist_states' ajoutée avec succès !")
            return True

        except Exception as e:
            print(f"✗ Erreur lors de l'ajout de la colonne : {e}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    print("=== Ajout de la colonne checklist_states ===\n")

    # Afficher le chemin de la base de données
    with app.app_context():
        db_path = app.config.get('SQLALCHEMY_DATABASE_URI', '').replace('sqlite:///', '')
        print(f"Base de données : {db_path}\n")

    # Ajouter la colonne
    if add_checklist_column():
        print("\n✅ Opération terminée avec succès !")
    else:
        print("\n❌ L'opération a échoué.")
        sys.exit(1)
