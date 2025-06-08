#!/usr/bin/env python3
"""
Script pour créer les nouvelles tables du système de fichiers de classe
"""

from app import app
from extensions import db
from models.class_file import ClassFile, ClassFolder
from models.file_manager import FileAnnotation

def create_new_tables():
    """Créer les nouvelles tables"""
    
    with app.app_context():
        print("🔧 Création des nouvelles tables...")
        
        try:
            # Créer toutes les tables
            db.create_all()
            print("✅ Tables créées avec succès:")
            print("   - class_files_v2")
            print("   - class_folders")
            print("   - file_annotations")
            
        except Exception as e:
            print(f"❌ Erreur lors de la création des tables: {e}")
            return False
        
        return True

if __name__ == "__main__":
    print("=" * 50)
    print("CRÉATION DES NOUVELLES TABLES")
    print("=" * 50)
    
    if create_new_tables():
        print("\n✅ Prêt à utiliser le nouveau système!")
        print("\nÉtapes suivantes:")
        print("1. Redémarrez votre serveur Flask")
        print("2. Testez la copie de fichiers vers les classes")
        print("3. Si tout fonctionne, vous pouvez nettoyer les anciennes données avec clean_class_files.py")
    else:
        print("\n❌ Échec de la création des tables")