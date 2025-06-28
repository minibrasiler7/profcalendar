from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from extensions import db
import os
import uuid
import shutil
from datetime import datetime
from PIL import Image
from models.file_manager import FileFolder, UserFile
from models.student import ClassFile
import io

# Importer les modèles après leur création
# from models.file_manager import FileFolder, UserFile

file_manager_bp = Blueprint('file_manager', __name__, url_prefix='/file_manager')

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
MAX_FILE_SIZE = 80 * 1024 * 1024  # 80 MB
THUMBNAIL_SIZE = (200, 200)

def allowed_file(filename):
    """Vérifie si le fichier est autorisé"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_thumbnail(image_path, thumbnail_path):
    """Crée une miniature pour une image"""
    try:
        with Image.open(image_path) as img:
            # Convertir en RGB si nécessaire
            if img.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1])
                img = background

            # Créer la miniature
            img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)

            # Créer le dossier si nécessaire
            os.makedirs(os.path.dirname(thumbnail_path), exist_ok=True)

            # Sauvegarder
            img.save(thumbnail_path, 'JPEG', quality=85)
            return True
    except Exception as e:
        print(f"Erreur lors de la création de la miniature : {e}")
        return False

@file_manager_bp.route('/')
@login_required
def index():
    """Page principale de gestion des fichiers"""
    from models.file_manager import FileFolder, UserFile

    # Récupérer le dossier actuel
    folder_id = request.args.get('folder', type=int)
    current_folder = None

    if folder_id:
        current_folder = FileFolder.query.filter_by(
            id=folder_id,
            user_id=current_user.id
        ).first_or_404()

    # Récupérer les dossiers et fichiers
    folders = FileFolder.query.filter_by(
        user_id=current_user.id,
        parent_id=folder_id
    ).order_by(FileFolder.name).all()

    files = UserFile.query.filter_by(
        user_id=current_user.id,
        folder_id=folder_id
    ).order_by(UserFile.original_filename).all()

    # Construire le fil d'ariane
    breadcrumb = []
    if current_folder:
        folder = current_folder
        while folder:
            breadcrumb.insert(0, folder)
            folder = folder.parent

    # Calculer l'espace utilisé
    total_size = sum(f.file_size or 0 for f in current_user.files.all())

    return render_template('file_manager/index.html',
                         folders=folders,
                         files=files,
                         current_folder=current_folder,
                         breadcrumb=breadcrumb,
                         total_size=total_size)

@file_manager_bp.route('/test-classes')
def test_classes():
    """Page de test pour diagnostiquer le problème des classes"""
    return render_template('file_manager/test_classes.html')

@file_manager_bp.route('/get-classes')
@login_required
def get_classes():
    """Récupérer les classes de l'utilisateur"""
    try:
        # Importer ici pour éviter les imports circulaires
        from models.classroom import Classroom

        classrooms = Classroom.query.filter_by(user_id=current_user.id).all()

        classes_data = []
        for classroom in classrooms:
            classes_data.append({
                'id': classroom.id,
                'name': classroom.name,
                'student_count': classroom.students.count()
            })

        return jsonify({
            'success': True,
            'classes': classes_data
        })
    except Exception as e:
        print(f"Erreur lors de la récupération des classes: {e}")
        return jsonify({
            'success': False,
            'message': 'Erreur lors de la récupération des classes',
            'classes': []
        })

@file_manager_bp.route('/get-class-files/<int:class_id>')
@login_required
def get_class_files(class_id):
    """Récupérer les fichiers d'une classe"""
    try:
        # Importer ici pour éviter les imports circulaires
        from models.classroom import Classroom

        # Vérifier que la classe appartient à l'utilisateur
        classroom = Classroom.query.filter_by(
            id=class_id,
            user_id=current_user.id
        ).first()

        if not classroom:
            return jsonify({'success': False, 'message': 'Classe introuvable'}), 404

        # Récupérer les fichiers de la classe
        class_files = ClassFile.query.filter_by(classroom_id=class_id).all()

        files_data = []
        for file in class_files:
            # Extraire le nom du dossier depuis la description si c'est une copie
            folder_path = None
            if file.description and "Copié dans le dossier:" in file.description:
                folder_path = file.description.split("Copié dans le dossier:")[1].strip()

            files_data.append({
                'id': file.id,
                'original_filename': file.original_filename,
                'file_type': file.file_type,
                'file_size': file.file_size,
                'folder_name': folder_path,
                'uploaded_at': file.uploaded_at.isoformat() if file.uploaded_at else None
            })

        return jsonify({
            'success': True,
            'files': files_data
        })

    except Exception as e:
        print(f"Erreur lors de la récupération des fichiers: {e}")
        return jsonify({
            'success': False,
            'message': 'Erreur lors de la récupération des fichiers',
            'files': []
        })

@file_manager_bp.route('/copy-folder-to-class', methods=['POST'])
@login_required
def copy_folder_to_class():
    """Copier un dossier complet vers une classe"""
    try:
        from models.file_manager import FileFolder, UserFile
        from models.classroom import Classroom

        data = request.get_json()
        folder_id = data.get('folder_id')
        class_id = data.get('class_id')

        if not folder_id or not class_id:
            return jsonify({'success': False, 'message': 'Données manquantes'}), 400

        # Vérifier que le dossier appartient à l'utilisateur
        folder = FileFolder.query.filter_by(
            id=folder_id,
            user_id=current_user.id
        ).first()

        if not folder:
            return jsonify({'success': False, 'message': 'Dossier introuvable'}), 404

        # Vérifier que la classe appartient à l'utilisateur
        classroom = Classroom.query.filter_by(
            id=class_id,
            user_id=current_user.id
        ).first()

        if not classroom:
            return jsonify({'success': False, 'message': 'Classe introuvable'}), 404

        # Fonction récursive pour copier un dossier et son contenu
        def copy_folder_recursive(source_folder, class_id, parent_folder_path=None):
            copied_count = 0
            current_folder_path = parent_folder_path + "/" + source_folder.name if parent_folder_path else source_folder.name

            # Copier tous les fichiers du dossier
            files_in_folder = list(source_folder.files)
            for file in files_in_folder:
                if copy_single_file_to_class(file, class_id, current_folder_path):
                    copied_count += 1

            # Si le dossier est vide (pas de fichiers), créer un marqueur de dossier
            if len(files_in_folder) == 0 and len(list(source_folder.subfolders)) == 0:
                # Créer un fichier marqueur pour représenter le dossier vide
                marker_file = ClassFile(
                    classroom_id=class_id,
                    filename='.folder_marker',
                    original_filename=f'[Dossier vide: {source_folder.name}]',
                    file_type='folder',
                    file_size=0,
                    description=f"Copié dans le dossier: {current_folder_path}"
                )
                db.session.add(marker_file)
                copied_count += 1
                print(f"📁 Marqueur créé pour dossier vide: {current_folder_path}")

            # Copier récursivement les sous-dossiers
            for subfolder in source_folder.subfolders:
                copied_count += copy_folder_recursive(subfolder, class_id, current_folder_path)

            return copied_count

        # Copier le dossier
        copied_count = copy_folder_recursive(folder, class_id)

        return jsonify({
            'success': True,
            'message': f'Dossier "{folder.name}" copié avec {copied_count} fichier(s)'
        })

    except Exception as e:
        print(f"Erreur lors de la copie du dossier: {e}")
        return jsonify({'success': False, 'message': 'Erreur lors de la copie du dossier'}), 500

@file_manager_bp.route('/copy-to-class-folder', methods=['POST'])
@login_required
def copy_to_class_folder():
    """Copier un fichier vers un dossier spécifique d'une classe"""
    try:
        from models.file_manager import UserFile
        from models.classroom import Classroom

        data = request.get_json()
        file_id = data.get('file_id')
        class_id = data.get('class_id')
        folder_path = data.get('folder_name')  # Gardons 'folder_name' pour la compatibilité

        if not file_id or not class_id or not folder_path:
            return jsonify({'success': False, 'message': 'Données manquantes'}), 400

        # Vérifier que le fichier appartient à l'utilisateur
        user_file = UserFile.query.filter_by(
            id=file_id,
            user_id=current_user.id
        ).first()

        if not user_file:
            return jsonify({'success': False, 'message': 'Fichier introuvable'}), 404

        # Vérifier que la classe appartient à l'utilisateur
        classroom = Classroom.query.filter_by(
            id=class_id,
            user_id=current_user.id
        ).first()

        if not classroom:
            return jsonify({'success': False, 'message': 'Classe introuvable'}), 404

        # Copier le fichier
        if copy_single_file_to_class(user_file, class_id, folder_path):
            return jsonify({
                'success': True,
                'message': f'Fichier copié dans le dossier {folder_path}'
            })
        else:
            return jsonify({'success': False, 'message': 'Erreur lors de la copie'})

    except Exception as e:
        print(f"Erreur lors de la copie: {e}")
        return jsonify({'success': False, 'message': 'Erreur lors de la copie du fichier'}), 500

@file_manager_bp.route('/copy-folder-to-class-folder', methods=['POST'])
@login_required
def copy_folder_to_class_folder():
    """Copier un dossier vers un dossier spécifique d'une classe"""
    try:
        from models.file_manager import FileFolder
        from models.classroom import Classroom

        data = request.get_json()
        folder_id = data.get('folder_id')
        class_id = data.get('class_id')
        target_folder_path = data.get('folder_name')  # Gardons 'folder_name' pour la compatibilité

        if not folder_id or not class_id or not target_folder_path:
            return jsonify({'success': False, 'message': 'Données manquantes'}), 400

        # Vérifier que le dossier appartient à l'utilisateur
        folder = FileFolder.query.filter_by(
            id=folder_id,
            user_id=current_user.id
        ).first()

        if not folder:
            return jsonify({'success': False, 'message': 'Dossier introuvable'}), 404

        # Vérifier que la classe appartient à l'utilisateur
        classroom = Classroom.query.filter_by(
            id=class_id,
            user_id=current_user.id
        ).first()

        if not classroom:
            return jsonify({'success': False, 'message': 'Classe introuvable'}), 404

        # Fonction récursive pour copier dans un dossier spécifique
        def copy_folder_to_target(source_folder, class_id, target_folder_base):
            copied_count = 0
            current_target_path = target_folder_base + "/" + source_folder.name

            # Copier tous les fichiers du dossier
            for file in source_folder.files:
                if copy_single_file_to_class(file, class_id, current_target_path):
                    copied_count += 1

            # Copier récursivement les sous-dossiers
            for subfolder in source_folder.subfolders:
                copied_count += copy_folder_to_target(subfolder, class_id, current_target_path)

            return copied_count

        # Copier le dossier
        copied_count = copy_folder_to_target(folder, class_id, target_folder_path)

        return jsonify({
            'success': True,
            'message': f'Dossier "{folder.name}" copié dans {target_folder_path} avec {copied_count} fichier(s)'
        })

    except Exception as e:
        print(f"Erreur lors de la copie: {e}")
        return jsonify({'success': False, 'message': 'Erreur lors de la copie du dossier'}), 500

def copy_single_file_to_class(user_file, class_id, folder_path=None):
    """Fonction utilitaire pour copier un fichier vers une classe"""
    try:
        # Construire la description avec le chemin complet
        if folder_path:
            description = f"Copié dans le dossier: {folder_path}"
            # Construire un identifiant unique basé sur le fichier et le chemin
            unique_key = f"{user_file.original_filename}_{folder_path}"
        else:
            description = "Copié depuis le gestionnaire de fichiers"
            unique_key = user_file.original_filename

        # Vérifier si le fichier n'existe pas déjà dans ce chemin spécifique
        existing_file = ClassFile.query.filter_by(
            classroom_id=class_id,
            original_filename=user_file.original_filename,
            description=description
        ).first()

        if existing_file:
            print(f"Fichier déjà existant: {user_file.original_filename} dans {folder_path}")
            return False  # Fichier déjà existant

        # Copier le fichier physique
        source_path = os.path.join(current_app.root_path, user_file.get_file_path())

        if not os.path.exists(source_path):
            print(f"Fichier source introuvable: {source_path}")
            return False

        # Créer le dossier de destination pour la classe
        class_folder = os.path.join(current_app.root_path, UPLOAD_FOLDER, 'class_files', str(class_id))
        os.makedirs(class_folder, exist_ok=True)

        # Générer un nouveau nom de fichier unique
        file_ext = user_file.file_type
        unique_filename = f"{uuid.uuid4()}.{file_ext}"
        dest_path = os.path.join(class_folder, unique_filename)

        # Copier le fichier
        shutil.copy2(source_path, dest_path)

        # Créer l'entrée en base de données
        class_file = ClassFile(
            classroom_id=class_id,
            filename=unique_filename,
            original_filename=user_file.original_filename,
            file_type=user_file.file_type,
            file_size=user_file.file_size,
            description=description
        )

        db.session.add(class_file)
        db.session.commit()

        print(f"Fichier copié avec succès: {user_file.original_filename} vers {folder_path or 'racine'}")
        return True

    except Exception as e:
        db.session.rollback()
        print(f"Erreur lors de la copie du fichier: {e}")
        return False

@file_manager_bp.route('/copy-to-class', methods=['POST'])
@login_required
def copy_to_class():
    """Copier un fichier vers une classe"""
    try:
        from models.file_manager import UserFile
        from models.classroom import Classroom

        data = request.get_json()
        file_id = data.get('file_id')
        class_id = data.get('class_id')

        if not file_id or not class_id:
            return jsonify({'success': False, 'message': 'Données manquantes'}), 400

        # Vérifier que le fichier appartient à l'utilisateur
        user_file = UserFile.query.filter_by(
            id=file_id,
            user_id=current_user.id
        ).first()

        if not user_file:
            return jsonify({'success': False, 'message': 'Fichier introuvable'}), 404

        # Vérifier que la classe appartient à l'utilisateur
        classroom = Classroom.query.filter_by(
            id=class_id,
            user_id=current_user.id
        ).first()

        if not classroom:
            return jsonify({'success': False, 'message': 'Classe introuvable'}), 404

        # Utiliser la fonction helper pour copier le fichier
        if copy_single_file_to_class(user_file, class_id):
            return jsonify({
                'success': True,
                'message': f'Fichier copié dans {classroom.name}'
            })
        else:
            return jsonify({'success': False, 'message': 'Le fichier existe déjà dans cette classe'})

    except Exception as e:
        db.session.rollback()
        print(f"Erreur lors de la copie: {e}")
        return jsonify({'success': False, 'message': 'Erreur lors de la copie du fichier'}), 500

@file_manager_bp.route('/delete-multiple', methods=['DELETE'])
@login_required
def delete_multiple():
    """Supprimer plusieurs fichiers et dossiers"""
    try:
        from models.file_manager import FileFolder, UserFile

        data = request.get_json()
        items = data.get('items', [])

        if not items:
            return jsonify({'success': False, 'message': 'Aucun élément à supprimer'}), 400

        deleted_count = 0

        for item in items:
            item_id = item.get('id')
            item_type = item.get('type')

            if item_type == 'file':
                # Supprimer un fichier
                user_file = UserFile.query.filter_by(
                    id=item_id,
                    user_id=current_user.id
                ).first()

                if user_file:
                    # Supprimer le fichier physique
                    file_path = os.path.join(current_app.root_path, user_file.get_file_path())
                    if os.path.exists(file_path):
                        os.remove(file_path)

                    # Supprimer la miniature si elle existe
                    if user_file.thumbnail_path:
                        thumbnail_path = os.path.join(current_app.root_path, user_file.get_thumbnail_path())
                        if os.path.exists(thumbnail_path):
                            os.remove(thumbnail_path)

                    # Supprimer de la base de données
                    db.session.delete(user_file)
                    deleted_count += 1

            elif item_type == 'folder':
                # Supprimer un dossier
                folder = FileFolder.query.filter_by(
                    id=item_id,
                    user_id=current_user.id
                ).first()

                if folder:
                    # Fonction récursive pour supprimer les fichiers et dossiers
                    def delete_folder_recursive(folder):
                        # D'abord, supprimer récursivement tous les sous-dossiers
                        for subfolder in list(folder.subfolders):
                            delete_folder_recursive(subfolder)
                        
                        # Supprimer les fichiers physiques du dossier
                        for file in folder.files:
                            file_path = os.path.join(current_app.root_path, file.get_file_path())
                            if os.path.exists(file_path):
                                os.remove(file_path)

                            if file.thumbnail_path:
                                thumbnail_path = os.path.join(current_app.root_path, file.get_thumbnail_path())
                                if os.path.exists(thumbnail_path):
                                    os.remove(thumbnail_path)
                            
                            # Supprimer le fichier de la base de données
                            db.session.delete(file)
                        
                        # Supprimer le dossier de la base de données
                        db.session.delete(folder)

                    # Supprimer récursivement le dossier et tout son contenu
                    delete_folder_recursive(folder)
                    deleted_count += 1

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'{deleted_count} élément(s) supprimé(s) avec succès'
        })

    except Exception as e:
        db.session.rollback()
        print(f"Erreur lors de la suppression multiple: {e}")
        return jsonify({'success': False, 'message': 'Erreur lors de la suppression'}), 500

@file_manager_bp.route('/create-folder-structure', methods=['POST'])
@login_required
def create_folder_structure():
    """Créer une structure complète de dossiers"""
    from models.file_manager import FileFolder
    
    data = request.get_json()
    folder_paths = data.get('folders', [])
    parent_id = data.get('parent_id')
    
    if not folder_paths:
        return jsonify({'success': True, 'message': 'Aucun dossier à créer'})
    
    try:
        # Dictionnaire pour stocker les dossiers créés par chemin
        created_folders = {}
        
        # Si un parent_id est fourni, l'ajouter comme racine
        if parent_id:
            parent_folder = FileFolder.query.filter_by(
                id=parent_id,
                user_id=current_user.id
            ).first()
            if parent_folder:
                created_folders[''] = parent_folder
        
        # Créer les dossiers dans l'ordre (parents d'abord)
        for folder_path in sorted(folder_paths):
            # Retirer les slashes de début et fin
            folder_path = folder_path.strip('/')
            if not folder_path:
                continue
                
            # Séparer le chemin en parties
            path_parts = folder_path.split('/')
            
            # Construire le chemin parent
            parent_path = '/'.join(path_parts[:-1])
            folder_name = path_parts[-1]
            
            # Déterminer le parent_id
            if parent_path in created_folders:
                current_parent_id = created_folders[parent_path].id
            elif parent_path == '' and parent_id:
                current_parent_id = parent_id
            else:
                current_parent_id = None
            
            # Vérifier si le dossier existe déjà
            existing_folder = FileFolder.query.filter_by(
                user_id=current_user.id,
                parent_id=current_parent_id,
                name=folder_name
            ).first()
            
            if existing_folder:
                created_folders[folder_path] = existing_folder
            else:
                # Créer le nouveau dossier
                new_folder = FileFolder(
                    user_id=current_user.id,
                    parent_id=current_parent_id,
                    name=folder_name,
                    color='#4F46E5'
                )
                db.session.add(new_folder)
                db.session.flush()  # Pour obtenir l'ID
                created_folders[folder_path] = new_folder
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{len(created_folders)} dossier(s) créé(s)',
            'folders': {path: folder.id for path, folder in created_folders.items()}
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@file_manager_bp.route('/upload-with-structure', methods=['POST'])
@login_required
def upload_with_structure():
    """Upload d'un fichier avec conservation de la structure de dossiers"""
    from models.file_manager import UserFile, FileFolder
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'Aucun fichier fourni'}), 400
    
    file = request.files['file']
    folder_path = request.form.get('folder_path', '').strip('/')
    parent_folder_id = request.form.get('parent_folder_id', type=int)
    
    if file.filename == '':
        return jsonify({'success': False, 'message': 'Aucun fichier sélectionné'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'message': 'Type de fichier non autorisé'}), 400
    
    # Vérifier la taille
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    if file_size > MAX_FILE_SIZE:
        return jsonify({'success': False, 'message': f'Fichier trop volumineux. Maximum: {MAX_FILE_SIZE // (1024*1024)}MB'}), 400
    
    try:
        # Déterminer le dossier de destination
        target_folder_id = parent_folder_id
        
        if folder_path:
            # Parcourir le chemin pour trouver ou créer les dossiers
            path_parts = folder_path.split('/')
            current_parent_id = parent_folder_id
            
            for folder_name in path_parts:
                if not folder_name:
                    continue
                
                # Chercher le dossier
                folder = FileFolder.query.filter_by(
                    user_id=current_user.id,
                    parent_id=current_parent_id,
                    name=folder_name
                ).first()
                
                if not folder:
                    # Créer le dossier s'il n'existe pas
                    folder = FileFolder(
                        user_id=current_user.id,
                        parent_id=current_parent_id,
                        name=folder_name,
                        color='#4F46E5'
                    )
                    db.session.add(folder)
                    db.session.flush()
                
                current_parent_id = folder.id
            
            target_folder_id = current_parent_id
        
        # Générer un nom unique
        original_filename = secure_filename(file.filename)
        file_ext = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4()}.{file_ext}"
        
        # Créer les dossiers
        user_folder = os.path.join(current_app.root_path, UPLOAD_FOLDER, 'files', str(current_user.id))
        os.makedirs(user_folder, exist_ok=True)
        
        # Sauvegarder le fichier
        file_path = os.path.join(user_folder, unique_filename)
        file.save(file_path)
        
        # Créer l'entrée en base de données
        user_file = UserFile(
            user_id=current_user.id,
            folder_id=target_folder_id,
            filename=unique_filename,
            original_filename=original_filename,
            file_type=file_ext,
            file_size=file_size,
            mime_type=file.content_type
        )
        
        # Créer une miniature pour les images
        if file_ext in ['png', 'jpg', 'jpeg']:
            thumbnail_filename = f"thumb_{unique_filename}"
            thumbnail_folder = os.path.join(current_app.root_path, UPLOAD_FOLDER, 'thumbnails', str(current_user.id))
            thumbnail_path = os.path.join(thumbnail_folder, thumbnail_filename)
            
            if create_thumbnail(file_path, thumbnail_path):
                user_file.thumbnail_path = thumbnail_filename
        
        db.session.add(user_file)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Fichier uploadé avec succès',
            'file': {
                'id': user_file.id,
                'name': user_file.original_filename,
                'type': user_file.file_type,
                'size': user_file.format_size()
            }
        })
        
    except Exception as e:
        db.session.rollback()
        # Nettoyer le fichier en cas d'erreur
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        return jsonify({'success': False, 'message': str(e)}), 500

@file_manager_bp.route('/create-folder', methods=['POST'])
@login_required
def create_folder():
    """Créer un nouveau dossier"""
    from models.file_manager import FileFolder

    data = request.get_json()

    if not data or not data.get('name'):
        return jsonify({'success': False, 'message': 'Nom du dossier requis'}), 400

    try:
        folder = FileFolder(
            user_id=current_user.id,
            parent_id=data.get('parent_id'),
            name=data.get('name'),
            color=data.get('color', '#4F46E5')
        )

        db.session.add(folder)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Dossier créé avec succès',
            'folder': {
                'id': folder.id,
                'name': folder.name,
                'color': folder.color,
                'file_count': 0,
                'size': 0
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@file_manager_bp.route('/upload', methods=['POST'])
@login_required
def upload_file():
    """Upload d'un fichier"""
    from models.file_manager import UserFile

    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'Aucun fichier fourni'}), 400

    file = request.files['file']
    folder_id = request.form.get('folder_id', type=int)

    if file.filename == '':
        return jsonify({'success': False, 'message': 'Aucun fichier sélectionné'}), 400

    if not allowed_file(file.filename):
        return jsonify({'success': False, 'message': 'Type de fichier non autorisé'}), 400

    # Vérifier la taille
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)

    if file_size > MAX_FILE_SIZE:
        return jsonify({'success': False, 'message': f'Fichier trop volumineux. Maximum: {MAX_FILE_SIZE // (1024*1024)}MB'}), 400

    try:
        # Générer un nom unique
        original_filename = secure_filename(file.filename)
        file_ext = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4()}.{file_ext}"

        # Créer les dossiers
        user_folder = os.path.join(current_app.root_path, UPLOAD_FOLDER, 'files', str(current_user.id))
        os.makedirs(user_folder, exist_ok=True)

        # Sauvegarder le fichier
        file_path = os.path.join(user_folder, unique_filename)
        file.save(file_path)

        # Créer l'entrée en base de données
        user_file = UserFile(
            user_id=current_user.id,
            folder_id=folder_id,
            filename=unique_filename,
            original_filename=original_filename,
            file_type=file_ext,
            file_size=file_size,
            mime_type=file.content_type
        )

        # Créer une miniature pour les images
        if file_ext in ['png', 'jpg', 'jpeg']:
            thumbnail_filename = f"thumb_{unique_filename}"
            thumbnail_folder = os.path.join(current_app.root_path, UPLOAD_FOLDER, 'thumbnails', str(current_user.id))
            thumbnail_path = os.path.join(thumbnail_folder, thumbnail_filename)

            if create_thumbnail(file_path, thumbnail_path):
                user_file.thumbnail_path = thumbnail_filename

        db.session.add(user_file)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Fichier uploadé avec succès',
            'file': {
                'id': user_file.id,
                'name': user_file.original_filename,
                'type': user_file.file_type,
                'size': user_file.format_size(),
                'thumbnail': user_file.thumbnail_path is not None
            }
        })

    except Exception as e:
        db.session.rollback()
        # Nettoyer le fichier en cas d'erreur
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        return jsonify({'success': False, 'message': str(e)}), 500

@file_manager_bp.route('/test_serve/<int:file_id>')
def test_serve(file_id):
    """Route de test simple"""
    print(f"[TEST] Route de test appelée avec file_id={file_id}")
    return f"Test OK - file_id={file_id}"

@file_manager_bp.route('/serve_file/<int:file_id>')
@login_required
def serve_file(file_id):
    """Sert un fichier pour l'affichage inline (pour le viewer d'annotation)"""
    try:
        print(f"[DEBUG] === DEBUT serve_file file_id={file_id} ===")
        
        # Import simple pour tester
        from models.student import ClassFile
        
        print(f"[DEBUG] Import réussi, recherche du fichier...")
        
        # Recherche simple du fichier de classe
        class_file = ClassFile.query.filter_by(id=file_id).first()
        
        print(f"[DEBUG] ClassFile trouvé: {class_file}")
        
        if not class_file:
            print(f"[DEBUG] Aucun fichier trouvé avec id={file_id}")
            return "Fichier introuvable", 404
            
        print(f"[DEBUG] Fichier: {class_file.original_filename}")
        print(f"[DEBUG] Classroom ID: {class_file.classroom_id}")
        
        # Vérification simple des droits
        if hasattr(class_file, 'classroom') and hasattr(class_file.classroom, 'user_id'):
            if class_file.classroom.user_id != current_user.id:
                print(f"[DEBUG] Accès refusé - user_id:{current_user.id} vs {class_file.classroom.user_id}")
                return "Accès refusé", 403
        
        # Construction du chemin simplifié
        file_path = os.path.join(current_app.root_path, 'uploads', 'class_files', str(class_file.classroom_id), class_file.filename)
        print(f"[DEBUG] Chemin complet: {file_path}")
        print(f"[DEBUG] Fichier existe: {os.path.exists(file_path)}")
        
        if not os.path.exists(file_path):
            print(f"[DEBUG] Fichier physique introuvable")
            return "Fichier physique introuvable", 404
        
        # Mimetype simple
        mimetype = 'application/pdf' if class_file.file_type == 'pdf' else 'application/octet-stream'
        print(f"[DEBUG] Mimetype: {mimetype}")
        
        print(f"[DEBUG] === FIN serve_file - envoi du fichier ===")
        return send_file(file_path, mimetype=mimetype, as_attachment=False)
        
    except Exception as e:
        print(f"[ERROR] ERREUR dans serve_file: {e}")
        import traceback
        traceback.print_exc()
        return f"Erreur serveur: {str(e)}", 500

@file_manager_bp.route('/download/<int:file_id>')
@login_required
def download_file(file_id):
    """Télécharger un fichier"""
    from models.file_manager import UserFile

    file = UserFile.query.filter_by(
        id=file_id,
        user_id=current_user.id
    ).first_or_404()

    file_path = os.path.join(current_app.root_path, file.get_file_path())

    if not os.path.exists(file_path):
        flash('Fichier introuvable', 'error')
        return redirect(url_for('file_manager.index'))

    return send_file(file_path,
                     download_name=file.original_filename,
                     as_attachment=True)

@file_manager_bp.route('/preview/<int:file_id>')
@login_required
def preview_file(file_id):
    """Aperçu d'un fichier"""
    from models.file_manager import UserFile

    file = UserFile.query.filter_by(
        id=file_id,
        user_id=current_user.id
    ).first_or_404()

    file_path = os.path.join(current_app.root_path, file.get_file_path())

    if not os.path.exists(file_path):
        flash('Fichier introuvable', 'error')
        return redirect(url_for('file_manager.index'))

    # Pour les images, utiliser la miniature si disponible
    if file.thumbnail_path and request.args.get('thumbnail'):
        thumbnail_path = os.path.join(current_app.root_path, file.get_thumbnail_path())
        if os.path.exists(thumbnail_path):
            return send_file(thumbnail_path, mimetype='image/jpeg')

    return send_file(file_path, mimetype=file.mime_type)

@file_manager_bp.route('/delete-file/<int:file_id>', methods=['DELETE'])
@login_required
def delete_file(file_id):
    """Supprimer un fichier"""
    from models.file_manager import UserFile

    file = UserFile.query.filter_by(
        id=file_id,
        user_id=current_user.id
    ).first_or_404()

    try:
        # Supprimer le fichier physique
        file_path = os.path.join(current_app.root_path, file.get_file_path())
        if os.path.exists(file_path):
            os.remove(file_path)

        # Supprimer la miniature si elle existe
        if file.thumbnail_path:
            thumbnail_path = os.path.join(current_app.root_path, file.get_thumbnail_path())
            if os.path.exists(thumbnail_path):
                os.remove(thumbnail_path)

        # Supprimer de la base de données
        db.session.delete(file)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Fichier supprimé avec succès'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@file_manager_bp.route('/delete-folder/<int:folder_id>', methods=['DELETE'])
@login_required
def delete_folder(folder_id):
    """Supprimer un dossier et son contenu"""
    from models.file_manager import FileFolder, UserFile

    folder = FileFolder.query.filter_by(
        id=folder_id,
        user_id=current_user.id
    ).first_or_404()

    try:
        # Fonction récursive pour supprimer les fichiers et dossiers
        def delete_folder_recursive(folder):
            # D'abord, supprimer récursivement tous les sous-dossiers
            for subfolder in list(folder.subfolders):
                delete_folder_recursive(subfolder)
            
            # Supprimer les fichiers physiques du dossier
            for file in folder.files:
                file_path = os.path.join(current_app.root_path, file.get_file_path())
                if os.path.exists(file_path):
                    os.remove(file_path)

                if file.thumbnail_path:
                    thumbnail_path = os.path.join(current_app.root_path, file.get_thumbnail_path())
                    if os.path.exists(thumbnail_path):
                        os.remove(thumbnail_path)
                
                # Supprimer le fichier de la base de données
                db.session.delete(file)
            
            # Supprimer le dossier de la base de données
            db.session.delete(folder)

        # Supprimer récursivement le dossier et tout son contenu
        delete_folder_recursive(folder)
        
        # Commit final
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Dossier et son contenu supprimés avec succès'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@file_manager_bp.route('/delete-class-file/<int:file_id>', methods=['DELETE'])
@login_required
def delete_class_file(file_id):
    """Supprimer un fichier d'une classe"""
    print(f"🔍 Tentative de suppression du fichier de classe ID: {file_id}")
    print(f"🔍 Utilisateur: {current_user.id} ({current_user.username})")
    
    try:
        from models.classroom import Classroom
        
        # Vérifier que le fichier appartient à une classe de l'utilisateur
        class_file = ClassFile.query.join(
            Classroom, ClassFile.classroom_id == Classroom.id
        ).filter(
            ClassFile.id == file_id,
            Classroom.user_id == current_user.id
        ).first()

        print(f"🔍 Fichier trouvé: {class_file}")
        if class_file:
            print(f"🔍 Détails: {class_file.original_filename} dans classe {class_file.classroom_id}")

        if not class_file:
            print("❌ Fichier introuvable dans les classes de l'utilisateur")
            return jsonify({'success': False, 'message': 'Fichier introuvable'}), 404

        # Supprimer le fichier physique
        file_path = os.path.join(current_app.root_path, UPLOAD_FOLDER, 'class_files', 
                                str(class_file.classroom_id), class_file.filename)
        
        print(f"🔍 Chemin du fichier physique: {file_path}")
        if os.path.exists(file_path):
            os.remove(file_path)
            print("✅ Fichier physique supprimé")
        else:
            print("⚠️  Fichier physique déjà inexistant")

        # Supprimer de la base de données
        print("🔍 Suppression de la base de données...")
        db.session.delete(class_file)
        db.session.commit()
        print("✅ Suppression de la base de données réussie")

        return jsonify({
            'success': True,
            'message': 'Fichier supprimé avec succès'
        })

    except Exception as e:
        db.session.rollback()
        print(f"❌ Erreur lors de la suppression du fichier de classe: {e}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        return jsonify({'success': False, 'message': 'Erreur lors de la suppression'}), 500

@file_manager_bp.route('/delete-class-folder', methods=['DELETE'])
@login_required
def delete_class_folder():
    """Supprimer tous les fichiers d'un dossier dans une classe"""
    print(f"🔍 Tentative de suppression du dossier de classe")
    print(f"🔍 Utilisateur: {current_user.id} ({current_user.username})")
    
    try:
        from models.classroom import Classroom
        
        data = request.get_json()
        folder_path = data.get('folder_path')
        class_id = data.get('class_id')
        
        print(f"🔍 Données reçues: folder_path='{folder_path}', class_id={class_id}")
        
        if not folder_path or not class_id:
            return jsonify({'success': False, 'message': 'Données manquantes'}), 400
        
        # Vérifier que la classe appartient à l'utilisateur
        classroom = Classroom.query.filter_by(
            id=class_id,
            user_id=current_user.id
        ).first()
        
        if not classroom:
            return jsonify({'success': False, 'message': 'Classe introuvable'}), 404
        
        # Trouver tous les fichiers dans ce dossier ET ses sous-dossiers
        folder_description_exact = f"Copié dans le dossier: {folder_path}"
        folder_description_prefix = f"Copié dans le dossier: {folder_path}/"
        
        print(f"🔍 Recherche des fichiers avec description exacte: '{folder_description_exact}'")
        print(f"🔍 Recherche des fichiers avec préfixe: '{folder_description_prefix}'")
        
        # Chercher les fichiers dans le dossier exact ET dans tous ses sous-dossiers
        class_files = ClassFile.query.filter(
            ClassFile.classroom_id == class_id,
            db.or_(
                ClassFile.description == folder_description_exact,
                ClassFile.description.like(folder_description_prefix + '%')
            )
        ).all()
        
        print(f"🔍 Fichiers trouvés: {len(class_files)}")
        for cf in class_files:
            print(f"🔍   - {cf.original_filename} (ID: {cf.id})")
        
        # Supprimer tous les fichiers du dossier
        deleted_count = 0
        for class_file in class_files:
            # Supprimer le fichier physique
            file_path = os.path.join(current_app.root_path, UPLOAD_FOLDER, 'class_files', 
                                   str(class_file.classroom_id), class_file.filename)
            
            print(f"🔍 Suppression fichier physique: {file_path}")
            if os.path.exists(file_path):
                os.remove(file_path)
                print("✅ Fichier physique supprimé")
            else:
                print("⚠️  Fichier physique déjà inexistant")
            
            # Supprimer l'entrée de la base de données
            db.session.delete(class_file)
            deleted_count += 1
        
        print(f"🔍 Commit de la suppression de {deleted_count} fichier(s)")
        db.session.commit()
        print("✅ Suppression terminée")
        
        return jsonify({
            'success': True,
            'message': f'Dossier "{folder_path}" supprimé avec {deleted_count} fichier(s)'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Erreur lors de la suppression du dossier de classe: {e}")
        return jsonify({'success': False, 'message': 'Erreur lors de la suppression'}), 500

@file_manager_bp.route('/rename', methods=['PUT'])
@login_required
def rename_item():
    """Renommer un fichier ou dossier"""
    from models.file_manager import FileFolder, UserFile

    data = request.get_json()
    item_type = data.get('type')
    item_id = data.get('id')
    new_name = data.get('name')

    if not all([item_type, item_id, new_name]):
        return jsonify({'success': False, 'message': 'Données manquantes'}), 400

    try:
        if item_type == 'folder':
            item = FileFolder.query.filter_by(
                id=item_id,
                user_id=current_user.id
            ).first_or_404()
        else:
            item = UserFile.query.filter_by(
                id=item_id,
                user_id=current_user.id
            ).first_or_404()
            item.original_filename = new_name

        if item_type == 'folder':
            item.name = new_name

        item.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Élément renommé avec succès'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@file_manager_bp.route('/update-folder-color', methods=['PUT'])
@login_required
def update_folder_color():
    """Mettre à jour la couleur d'un dossier"""
    from models.file_manager import FileFolder

    data = request.get_json()
    folder_id = data.get('id')
    new_color = data.get('color')

    if not folder_id or not new_color:
        return jsonify({'success': False, 'message': 'Données manquantes'}), 400

    try:
        folder = FileFolder.query.filter_by(
            id=folder_id,
            user_id=current_user.id
        ).first_or_404()

        folder.color = new_color
        folder.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Couleur mise à jour'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@file_manager_bp.route('/api/save-annotations', methods=['POST'])
@login_required
def save_annotations():
    """Sauvegarder les annotations d'un fichier"""
    try:
        from models.file_manager import FileAnnotation
        
        data = request.get_json()
        annotations_data = data.get('annotations', {})
        file_id_raw = data.get('file_id')
        
        # Extraire l'ID du fichier depuis les données
        file_id = int(file_id_raw) if str(file_id_raw).isdigit() else None
        if not file_id:
            return jsonify({'success': False, 'message': 'ID de fichier invalide'}), 400
            
        # Vérifier que le fichier existe et appartient à l'utilisateur
        from models.student import ClassFile
        from models.classroom import Classroom
        
        class_file = ClassFile.query.join(
            Classroom, ClassFile.classroom_id == Classroom.id
        ).filter(
            ClassFile.id == file_id,
            Classroom.user_id == current_user.id
        ).first()
        
        if not class_file:
            return jsonify({'success': False, 'message': 'Fichier introuvable'}), 404
            
        # Chercher une annotation existante
        annotation = FileAnnotation.query.filter_by(
            file_id=file_id,
            file_type='class_file',
            user_id=current_user.id
        ).first()
        
        if annotation:
            # Mettre à jour l'annotation existante
            annotation.annotations_data = annotations_data
            annotation.updated_at = datetime.utcnow()
        else:
            # Créer une nouvelle annotation
            annotation = FileAnnotation(
                file_id=file_id,
                file_type='class_file',
                user_id=current_user.id,
                annotations_data=annotations_data
            )
            db.session.add(annotation)
            
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Annotations sauvegardées'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Erreur lors de la sauvegarde des annotations: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@file_manager_bp.route('/api/load-annotations/<int:file_id>', methods=['GET'])
@login_required
def load_annotations(file_id):
    """Charger les annotations d'un fichier"""
    try:
        from models.file_manager import FileAnnotation
            
        # Vérifier que le fichier existe et appartient à l'utilisateur
        from models.student import ClassFile
        from models.classroom import Classroom
        
        class_file = ClassFile.query.join(
            Classroom, ClassFile.classroom_id == Classroom.id
        ).filter(
            ClassFile.id == file_id,
            Classroom.user_id == current_user.id
        ).first()
        
        if not class_file:
            return jsonify({'success': False, 'message': 'Fichier introuvable'}), 404
            
        # Chercher l'annotation
        annotation = FileAnnotation.query.filter_by(
            file_id=file_id,
            file_type='class_file',
            user_id=current_user.id
        ).first()
        
        if annotation:
            return jsonify({
                'success': True,
                'annotations': annotation.annotations_data
            })
        else:
            # Pas d'annotations trouvées, retourner structure vide
            return jsonify({
                'success': True,
                'annotations': {}
            })
            
    except Exception as e:
        print(f"Erreur lors du chargement des annotations: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
