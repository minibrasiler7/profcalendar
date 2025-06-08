#!/usr/bin/env python3
"""
Test rapide du nouveau système de fichiers de classe
"""

from app import app
from extensions import db
from models.class_file import ClassFile, ClassFolder
from models.file_manager import UserFile
from models.classroom import Classroom
from models.user import User

def test_new_system():
    """Tester le nouveau système"""
    
    with app.app_context():
        print("🧪 Test du nouveau système...")
        
        # Vérifier les tables
        try:
            tables_exist = db.inspect(db.engine).has_table('class_files_v2')
            if not tables_exist:
                print("❌ Tables non créées. Lancez d'abord create_new_tables.py")
                return
            
            print("✅ Tables trouvées")
        except Exception as e:
            print(f"❌ Erreur de vérification des tables: {e}")
            return
        
        # Compter les données existantes
        try:
            users_count = User.query.count()
            classes_count = Classroom.query.count()
            files_count = UserFile.query.count()
            new_class_files_count = ClassFile.query.count()
            
            print(f"\n📊 État actuel:")
            print(f"   - Utilisateurs: {users_count}")
            print(f"   - Classes: {classes_count}")
            print(f"   - Fichiers utilisateur: {files_count}")
            print(f"   - Fichiers de classe (nouveau): {new_class_files_count}")
            
            if classes_count == 0:
                print("\n⚠️  Aucune classe trouvée. Créez d'abord des classes dans l'interface.")
                return
            
            if files_count == 0:
                print("\n⚠️  Aucun fichier trouvé. Uploadez d'abord des fichiers dans le gestionnaire.")
                return
            
            print(f"\n✅ Système prêt pour les tests!")
            print("\nPour tester:")
            print("1. Ouvrez le gestionnaire de fichiers")
            print("2. Glissez un fichier sur une classe")
            print("3. L'arborescence devrait se mettre à jour automatiquement")
            
        except Exception as e:
            print(f"❌ Erreur lors du test: {e}")

def show_routes():
    """Afficher les nouvelles routes disponibles"""
    print("\n🛣️  Nouvelles routes API:")
    print("   POST /api/class-files/copy-file")
    print("   POST /api/class-files/copy-folder") 
    print("   GET  /api/class-files/list/<class_id>")
    print("   DELETE /api/class-files/delete/<file_id>")
    print("   POST /api/class-files/create-folder")

if __name__ == "__main__":
    print("=" * 50)
    print("TEST DU NOUVEAU SYSTÈME")
    print("=" * 50)
    
    test_new_system()
    show_routes()