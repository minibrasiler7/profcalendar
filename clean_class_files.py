#!/usr/bin/env python3
"""
Script pour nettoyer tous les fichiers associés aux classes
"""

import os
import shutil
from app import app
from extensions import db
from models.student import ClassFile
from models.classroom import Classroom

def clean_class_files():
    """Supprimer tous les fichiers et dossiers associés aux classes"""
    
    with app.app_context():
        print("🧹 Début du nettoyage des fichiers de classe...")
        
        # 1. Récupérer tous les fichiers de classe
        class_files = ClassFile.query.all()
        total_files = len(class_files)
        print(f"\n📋 Nombre total de fichiers de classe trouvés: {total_files}")
        
        if total_files == 0:
            print("✅ Aucun fichier de classe à supprimer.")
            return
        
        # Demander confirmation
        response = input(f"\n⚠️  Êtes-vous sûr de vouloir supprimer {total_files} fichier(s) de classe? (oui/non): ")
        if response.lower() != 'oui':
            print("❌ Nettoyage annulé.")
            return
        
        # 2. Supprimer les fichiers physiques
        deleted_files = 0
        errors = 0
        
        # Chemin du dossier class_files
        class_files_dir = os.path.join(app.root_path, 'uploads', 'class_files')
        
        print(f"\n🗑️  Suppression des fichiers physiques...")
        
        for class_file in class_files:
            try:
                # Construire le chemin du fichier
                file_path = os.path.join(class_files_dir, str(class_file.classroom_id), class_file.filename)
                
                # Supprimer le fichier s'il existe
                if os.path.exists(file_path):
                    os.remove(file_path)
                    deleted_files += 1
                    print(f"   ✓ Supprimé: {class_file.original_filename} (classe {class_file.classroom_id})")
                else:
                    print(f"   ⚠️  Fichier non trouvé: {class_file.original_filename}")
                
            except Exception as e:
                errors += 1
                print(f"   ❌ Erreur lors de la suppression de {class_file.original_filename}: {e}")
        
        # 3. Supprimer les entrées de la base de données
        print(f"\n💾 Suppression des entrées de la base de données...")
        
        try:
            # Supprimer tous les ClassFile
            db.session.query(ClassFile).delete()
            db.session.commit()
            print(f"   ✓ {total_files} entrées supprimées de la base de données")
        except Exception as e:
            db.session.rollback()
            print(f"   ❌ Erreur lors de la suppression en base de données: {e}")
            return
        
        # 4. Nettoyer les dossiers vides
        print(f"\n📁 Nettoyage des dossiers vides...")
        
        if os.path.exists(class_files_dir):
            # Parcourir tous les sous-dossiers
            for classroom_id in os.listdir(class_files_dir):
                classroom_dir = os.path.join(class_files_dir, classroom_id)
                
                if os.path.isdir(classroom_dir):
                    # Vérifier si le dossier est vide
                    if not os.listdir(classroom_dir):
                        try:
                            os.rmdir(classroom_dir)
                            print(f"   ✓ Dossier vide supprimé: {classroom_dir}")
                        except Exception as e:
                            print(f"   ❌ Erreur lors de la suppression du dossier {classroom_dir}: {e}")
        
        # 5. Afficher le résumé
        print(f"\n📊 Résumé du nettoyage:")
        print(f"   - Fichiers physiques supprimés: {deleted_files}")
        print(f"   - Entrées de base de données supprimées: {total_files}")
        print(f"   - Erreurs rencontrées: {errors}")
        
        print(f"\n✅ Nettoyage terminé!")
        
        # Option pour supprimer complètement le dossier class_files
        response = input(f"\n🗑️  Voulez-vous supprimer complètement le dossier 'class_files'? (oui/non): ")
        if response.lower() == 'oui':
            try:
                if os.path.exists(class_files_dir):
                    shutil.rmtree(class_files_dir)
                    print(f"✅ Dossier 'class_files' supprimé complètement.")
            except Exception as e:
                print(f"❌ Erreur lors de la suppression du dossier: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("NETTOYAGE DES FICHIERS DE CLASSE")
    print("=" * 60)
    
    clean_class_files()