#!/usr/bin/env python3
"""
Script pour lister tous les fichiers associés aux classes
"""

import os
from app import app
from extensions import db
from models.student import ClassFile
from models.classroom import Classroom
from models.user import User

def list_class_files():
    """Lister tous les fichiers associés aux classes"""
    
    with app.app_context():
        print("📋 Liste des fichiers de classe...")
        
        # Récupérer tous les fichiers de classe avec les informations des classes
        class_files = db.session.query(
            ClassFile,
            Classroom.name.label('class_name'),
            User.username.label('teacher')
        ).join(
            Classroom, ClassFile.classroom_id == Classroom.id
        ).join(
            User, Classroom.user_id == User.id
        ).all()
        
        if not class_files:
            print("\n✅ Aucun fichier de classe trouvé.")
            return
        
        # Grouper par classe
        files_by_class = {}
        total_size = 0
        
        for file, class_name, teacher in class_files:
            key = (file.classroom_id, class_name, teacher)
            
            if key not in files_by_class:
                files_by_class[key] = []
            
            files_by_class[key].append(file)
            total_size += file.file_size or 0
        
        # Afficher les résultats
        print(f"\n📊 Résumé:")
        print(f"   - Nombre total de fichiers: {len(class_files)}")
        print(f"   - Nombre de classes avec fichiers: {len(files_by_class)}")
        print(f"   - Taille totale: {format_size(total_size)}")
        
        print("\n" + "=" * 80)
        
        # Afficher par classe
        for (class_id, class_name, teacher), files in sorted(files_by_class.items()):
            print(f"\n📚 Classe: {class_name} (ID: {class_id})")
            print(f"👤 Enseignant: {teacher}")
            print(f"📁 Nombre de fichiers: {len(files)}")
            
            class_size = sum(f.file_size or 0 for f in files)
            print(f"💾 Taille totale: {format_size(class_size)}")
            
            print("\n   Fichiers:")
            for file in sorted(files, key=lambda f: f.original_filename):
                # Vérifier si le fichier physique existe
                file_path = os.path.join(app.root_path, 'uploads', 'class_files', 
                                       str(file.classroom_id), file.filename)
                exists = "✓" if os.path.exists(file_path) else "✗"
                
                print(f"   {exists} {file.original_filename} ({file.file_type}) - {format_size(file.file_size or 0)}")
                
                # Afficher la description si elle contient un chemin de dossier
                if file.description and "Copié dans le dossier:" in file.description:
                    folder_path = file.description.split("Copié dans le dossier:")[1].strip()
                    print(f"      📂 Dossier: {folder_path}")
            
            print("-" * 80)
        
        # Vérifier les fichiers orphelins
        print("\n🔍 Vérification des fichiers orphelins...")
        
        class_files_dir = os.path.join(app.root_path, 'uploads', 'class_files')
        orphan_files = []
        
        if os.path.exists(class_files_dir):
            # Parcourir tous les fichiers physiques
            for classroom_id in os.listdir(class_files_dir):
                classroom_dir = os.path.join(class_files_dir, classroom_id)
                
                if os.path.isdir(classroom_dir):
                    for filename in os.listdir(classroom_dir):
                        # Vérifier si ce fichier existe dans la base de données
                        exists_in_db = ClassFile.query.filter_by(
                            classroom_id=int(classroom_id),
                            filename=filename
                        ).first() is not None
                        
                        if not exists_in_db:
                            orphan_files.append({
                                'path': os.path.join(classroom_dir, filename),
                                'classroom_id': classroom_id,
                                'filename': filename,
                                'size': os.path.getsize(os.path.join(classroom_dir, filename))
                            })
        
        if orphan_files:
            print(f"\n⚠️  {len(orphan_files)} fichier(s) orphelin(s) trouvé(s) (fichiers physiques sans entrée en base):")
            for orphan in orphan_files:
                print(f"   - Classe {orphan['classroom_id']}: {orphan['filename']} ({format_size(orphan['size'])})")
        else:
            print("✅ Aucun fichier orphelin trouvé.")

def format_size(size):
    """Formater la taille en unités lisibles"""
    units = ['B', 'KB', 'MB', 'GB']
    unit_index = 0
    size = float(size)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    return f"{size:.1f} {units[unit_index]}"

if __name__ == "__main__":
    print("=" * 80)
    print("LISTE DES FICHIERS DE CLASSE")
    print("=" * 80)
    
    list_class_files()