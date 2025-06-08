#!/usr/bin/env python3
"""
Script pour ajouter la table des annotations
"""

import sys
import os

# Ajouter le répertoire du projet au chemin Python
sys.path.insert(0, '/Users/loicstrauch/PycharmProjects/profcalendar')

from app import app
from extensions import db
from models.file_manager import FileAnnotation

def add_annotations_table():
    """Ajouter la table des annotations"""
    
    with app.app_context():
        print("🔧 Ajout de la table des annotations...")
        
        try:
            # Créer la table des annotations
            db.create_all()
            print("✅ Table file_annotations créée avec succès")
            
        except Exception as e:
            print(f"❌ Erreur lors de la création de la table: {e}")
            return False
        
        return True

if __name__ == "__main__":
    print("=" * 50)
    print("AJOUT DE LA TABLE DES ANNOTATIONS")
    print("=" * 50)
    
    if add_annotations_table():
        print("\n✅ Table des annotations prête!")
        print("\nMaintenant vous pouvez utiliser le système d'annotation.")
    else:
        print("\n❌ Échec de la création de la table")