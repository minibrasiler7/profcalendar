#!/usr/bin/env python3
"""
Script de migration pour passer de l'ancien système de fichiers de classe au nouveau
"""

from app import app
from extensions import db
from models.class_file import ClassFile, ClassFolder
from models.student import ClassFile as OldClassFile
from models.file_manager import UserFile
from models.classroom import Classroom
import os

def migrate_class_files():
    """Migrer les fichiers de classe vers le nouveau système"""
    
    with app.app_context():
        print("🔄 Migration des fichiers de classe...")
        
        # Créer les nouvelles tables
        try:
            db.create_all()
            print("✅ Nouvelles tables créées")
        except Exception as e:
            print(f"⚠️  Tables déjà existantes ou erreur: {e}")
        
        # Récupérer tous les anciens fichiers de classe
        old_files = OldClassFile.query.all()
        total_files = len(old_files)
        
        print(f"\n📋 {total_files} ancien(s) fichier(s) trouvé(s)")
        
        if total_files == 0:
            print("✅ Aucune migration nécessaire")
            return
        
        migrated_count = 0
        error_count = 0
        
        for old_file in old_files:
            try:
                # Trouver le fichier utilisateur correspondant par nom
                user_file = UserFile.query.filter_by(
                    original_filename=old_file.original_filename
                ).first()
                
                if not user_file:
                    print(f"⚠️  Fichier utilisateur introuvable pour: {old_file.original_filename}")
                    error_count += 1
                    continue
                
                # Extraire le chemin du dossier depuis la description
                folder_path = ''
                if old_file.description and "Copié dans le dossier:" in old_file.description:
                    folder_path = old_file.description.split("Copié dans le dossier:")[1].strip()
                
                # Vérifier si le fichier n'est pas déjà migré
                existing = ClassFile.query.filter_by(
                    classroom_id=old_file.classroom_id,
                    user_file_id=user_file.id,
                    folder_path=folder_path
                ).first()
                
                if existing:
                    print(f"⚠️  Fichier déjà migré: {old_file.original_filename}")
                    continue
                
                # Créer la nouvelle entrée
                new_file = ClassFile(
                    classroom_id=old_file.classroom_id,
                    user_file_id=user_file.id,
                    folder_path=folder_path,
                    copied_at=old_file.uploaded_at
                )
                
                db.session.add(new_file)
                migrated_count += 1
                
                print(f"✅ Migré: {old_file.original_filename} -> Classe {old_file.classroom_id}")
                
            except Exception as e:
                error_count += 1
                print(f"❌ Erreur pour {old_file.original_filename}: {e}")
        
        try:
            db.session.commit()
            print(f"\n📊 Résumé de la migration:")
            print(f"   - Fichiers migrés: {migrated_count}")
            print(f"   - Erreurs: {error_count}")
            print(f"   - Total traité: {migrated_count + error_count}/{total_files}")
            
            if migrated_count > 0:
                print(f"\n✅ Migration terminée avec succès!")
                
                # Demander si on veut supprimer les anciens fichiers
                response = input(f"\n🗑️  Voulez-vous supprimer les anciens fichiers physiques? (oui/non): ")
                if response.lower() == 'oui':
                    cleanup_old_files()
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erreur lors de la validation: {e}")

def cleanup_old_files():
    """Nettoyer les anciens fichiers physiques"""
    try:
        old_class_files_dir = os.path.join(app.root_path, 'uploads', 'class_files')
        
        if not os.path.exists(old_class_files_dir):
            print("✅ Aucun ancien dossier à nettoyer")
            return
        
        print("🧹 Nettoyage des anciens fichiers physiques...")
        
        # Compter les fichiers à supprimer
        file_count = 0
        for root, dirs, files in os.walk(old_class_files_dir):
            file_count += len(files)
        
        if file_count == 0:
            print("✅ Aucun fichier physique à supprimer")
            return
        
        print(f"⚠️  Cela supprimera {file_count} fichier(s) physique(s)")
        response = input("Êtes-vous sûr? (oui/non): ")
        
        if response.lower() == 'oui':
            import shutil
            shutil.rmtree(old_class_files_dir)
            print("✅ Anciens fichiers physiques supprimés")
        else:
            print("❌ Nettoyage annulé")
            
    except Exception as e:
        print(f"❌ Erreur lors du nettoyage: {e}")

def show_migration_status():
    """Afficher le statut de la migration"""
    with app.app_context():
        old_count = OldClassFile.query.count()
        new_count = ClassFile.query.count()
        
        print(f"📊 Statut de la migration:")
        print(f"   - Anciens fichiers: {old_count}")
        print(f"   - Nouveaux fichiers: {new_count}")
        
        if old_count == 0 and new_count > 0:
            print("✅ Migration complète")
        elif old_count > 0 and new_count == 0:
            print("⚠️  Migration non effectuée")
        elif old_count > 0 and new_count > 0:
            print("🔄 Migration partielle")
        else:
            print("❓ Aucun fichier détecté")

if __name__ == "__main__":
    print("=" * 60)
    print("MIGRATION DES FICHIERS DE CLASSE")
    print("=" * 60)
    
    print("\n1. Migrer les fichiers")
    print("2. Afficher le statut")
    print("3. Nettoyer les anciens fichiers")
    
    choice = input("\nChoisissez une option (1-3): ")
    
    if choice == "1":
        migrate_class_files()
    elif choice == "2":
        show_migration_status()
    elif choice == "3":
        cleanup_old_files()
    else:
        print("Option invalide")