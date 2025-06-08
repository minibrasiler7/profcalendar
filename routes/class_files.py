from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from extensions import db
from models.student import ClassFile  # Utiliser le modèle existant
from models.file_manager import UserFile, FileFolder
from models.classroom import Classroom
import os
import uuid
import shutil

class_files_bp = Blueprint('class_files', __name__, url_prefix='/api/class-files')

def copy_file_physically(user_file, class_id):
    """Copier un fichier physiquement vers le dossier de la classe"""
    try:
        from flask import current_app
        
        # Chemin source
        source_path = os.path.join(current_app.root_path, user_file.get_file_path())
        
        if not os.path.exists(source_path):
            print(f"❌ Fichier source introuvable: {source_path}")
            return False, None
        
        # Créer le dossier de destination
        class_folder = os.path.join(current_app.root_path, 'uploads', 'class_files', str(class_id))
        os.makedirs(class_folder, exist_ok=True)
        
        # Générer un nom unique
        file_ext = user_file.file_type
        unique_filename = f"{uuid.uuid4()}.{file_ext}"
        dest_path = os.path.join(class_folder, unique_filename)
        
        # Copier le fichier
        shutil.copy2(source_path, dest_path)
        print(f"✅ Fichier copié: {source_path} -> {dest_path}")
        
        return True, unique_filename
        
    except Exception as e:
        print(f"❌ Erreur lors de la copie physique: {e}")
        return False, None

@class_files_bp.route('/copy-file', methods=['POST'])
@login_required
def copy_file_to_class():
    """Copier un fichier vers une classe"""
    print(f"🔍 copy_file_to_class appelée")
    try:
        data = request.get_json()
        print(f"🔍 Données reçues: {data}")
        file_id = data.get('file_id')
        class_id = data.get('class_id')
        folder_path = data.get('folder_path', '').strip()
        print(f"🔍 file_id={file_id}, class_id={class_id}, folder_path={folder_path}")
        
        if not file_id or not class_id:
            return jsonify({'success': False, 'message': 'Paramètres manquants'}), 400
        
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
        
        # Vérifier si le fichier n'est pas déjà dans cette classe
        existing = ClassFile.query.filter_by(
            classroom_id=class_id,
            original_filename=user_file.original_filename
        ).first()
        
        if existing:
            return jsonify({
                'success': False, 
                'message': f'Le fichier "{user_file.original_filename}" existe déjà dans cette classe'
            })
        
        # Copier le fichier physiquement vers le dossier de la classe
        success, new_filename = copy_file_physically(user_file, class_id)
        
        if not success:
            return jsonify({
                'success': False,
                'message': 'Erreur lors de la copie du fichier'
            })
        
        # Créer la description avec le chemin du dossier
        description = "Copié depuis le gestionnaire de fichiers"
        if folder_path:
            description = f"Copié dans le dossier: {folder_path}"
        
        # Créer l'entrée dans la base de données
        class_file = ClassFile(
            classroom_id=class_id,
            filename=new_filename,
            original_filename=user_file.original_filename,
            file_type=user_file.file_type,
            file_size=user_file.file_size,
            description=description
        )
        
        db.session.add(class_file)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Fichier "{user_file.original_filename}" copié dans {classroom.name}',
            'file': {
                'id': class_file.id,
                'name': user_file.original_filename,
                'folder_path': folder_path
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'}), 500

@class_files_bp.route('/copy-folder', methods=['POST'])
@login_required
def copy_folder_to_class():
    """Copier un dossier complet vers une classe"""
    try:
        data = request.get_json()
        folder_id = data.get('folder_id')
        class_id = data.get('class_id')
        target_path = data.get('folder_path', '').strip()
        
        if not folder_id or not class_id:
            return jsonify({'success': False, 'message': 'Paramètres manquants'}), 400
        
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
        
        # Copier récursivement
        copied_count = copy_folder_recursive(folder, class_id, target_path)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Dossier "{folder.name}" copié avec {copied_count} fichier(s)',
            'copied_count': copied_count
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'}), 500

def copy_folder_recursive(folder, class_id, base_path):
    """Fonction récursive pour copier un dossier et son contenu"""
    copied_count = 0
    
    # Construire le chemin de destination
    if base_path:
        current_path = f"{base_path}/{folder.name}"
    else:
        current_path = folder.name
    
    # Copier tous les fichiers du dossier
    for file in folder.files:
        # Vérifier si le fichier n'existe pas déjà
        existing = ClassFile.query.filter_by(
            classroom_id=class_id,
            original_filename=file.original_filename
        ).first()
        
        if not existing:
            # Copier le fichier physiquement
            success, new_filename = copy_file_physically(file, class_id)
            
            if success:
                # Créer l'entrée en base
                description = f"Copié dans le dossier: {current_path}"
                class_file = ClassFile(
                    classroom_id=class_id,
                    filename=new_filename,
                    original_filename=file.original_filename,
                    file_type=file.file_type,
                    file_size=file.file_size,
                    description=description
                )
                db.session.add(class_file)
                copied_count += 1
    
    # Copier récursivement les sous-dossiers
    for subfolder in folder.subfolders:
        copied_count += copy_folder_recursive(subfolder, class_id, current_path)
    
    return copied_count

@class_files_bp.route('/list/<int:class_id>')
@login_required
def list_class_files(class_id):
    """Lister tous les fichiers d'une classe avec leur structure"""
    try:
        # Vérifier que la classe appartient à l'utilisateur
        classroom = Classroom.query.filter_by(
            id=class_id,
            user_id=current_user.id
        ).first()
        
        if not classroom:
            return jsonify({'success': False, 'message': 'Classe introuvable'}), 404
        
        # Récupérer tous les fichiers de la classe
        class_files = ClassFile.query.filter_by(classroom_id=class_id).order_by(ClassFile.original_filename).all()
        
        # Organiser les fichiers par structure
        files_data = []
        for class_file in class_files:
            # Extraire le chemin du dossier depuis la description
            folder_path = ''
            if class_file.description and "Copié dans le dossier:" in class_file.description:
                folder_path = class_file.description.split("Copié dans le dossier:")[1].strip()
            
            files_data.append({
                'id': class_file.id,
                'original_filename': class_file.original_filename,
                'file_type': class_file.file_type,
                'file_size': class_file.file_size,
                'folder_path': folder_path,
                'copied_at': class_file.uploaded_at.isoformat() if class_file.uploaded_at else None,
                'thumbnail': False  # Pour l'instant pas de miniatures pour les fichiers de classe
            })
        
        return jsonify({
            'success': True,
            'files': files_data,
            'class_name': classroom.name
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'}), 500

@class_files_bp.route('/delete/<int:file_id>', methods=['DELETE'])
@login_required
def delete_class_file(file_id):
    """Supprimer un fichier d'une classe"""
    try:
        # Vérifier que le fichier appartient à une classe de l'utilisateur
        class_file = db.session.query(ClassFile).join(
            Classroom, ClassFile.classroom_id == Classroom.id
        ).filter(
            ClassFile.id == file_id,
            Classroom.user_id == current_user.id
        ).first()
        
        if not class_file:
            return jsonify({'success': False, 'message': 'Fichier introuvable'}), 404
        
        # Supprimer le fichier physique
        try:
            from flask import current_app
            file_path = os.path.join(current_app.root_path, 'uploads', 'class_files', 
                                   str(class_file.classroom_id), class_file.filename)
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"✅ Fichier physique supprimé: {file_path}")
        except Exception as e:
            print(f"⚠️  Erreur lors de la suppression du fichier physique: {e}")
        
        # Supprimer l'entrée de la base de données
        db.session.delete(class_file)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Fichier retiré de la classe'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'}), 500

# Route create-folder supprimée pour l'instant - fonctionnalité future

@class_files_bp.route('/<int:classroom_id>')
@login_required
def get_class_files(classroom_id):
    """Récupérer les fichiers d'une classe (racine)"""
    try:
        # Vérifier que la classe appartient à l'utilisateur
        classroom = Classroom.query.filter_by(
            id=classroom_id,
            user_id=current_user.id
        ).first()
        
        if not classroom:
            return jsonify({'success': False, 'message': 'Classe introuvable'}), 404
        
        # Récupérer les fichiers sans dossier parent
        files = ClassFile.query.filter_by(
            classroom_id=classroom_id
        ).filter(
            db.or_(
                ClassFile.description == None,
                ClassFile.description == '',
                ClassFile.description == 'Copié depuis le gestionnaire de fichiers'
            )
        ).all()
        
        files_data = []
        for file in files:
            files_data.append({
                'id': file.id,
                'original_filename': file.original_filename,
                'file_type': file.file_type,
                'file_size': file.file_size,
                'thumbnail_path': None  # TODO: implémenter les miniatures
            })
        
        return jsonify({
            'success': True,
            'files': files_data,
            'folders': [],  # TODO: implémenter les dossiers
            'breadcrumb': []
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'}), 500

@class_files_bp.route('/upload', methods=['POST'])
@login_required
def upload_class_file():
    """Uploader un fichier directement dans une classe"""
    try:
        from flask import current_app
        from werkzeug.utils import secure_filename
        
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'Aucun fichier fourni'}), 400
        
        file = request.files['file']
        classroom_id = request.form.get('classroom_id')
        folder_path = request.form.get('folder_path', '').strip()
        
        if not classroom_id:
            return jsonify({'success': False, 'message': 'ID de classe manquant'}), 400
        
        # Vérifier que la classe appartient à l'utilisateur
        classroom = Classroom.query.filter_by(
            id=classroom_id,
            user_id=current_user.id
        ).first()
        
        if not classroom:
            return jsonify({'success': False, 'message': 'Classe introuvable'}), 404
        
        if file.filename == '':
            return jsonify({'success': False, 'message': 'Nom de fichier vide'}), 400
        
        # Générer un nom unique
        file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        unique_filename = f"{uuid.uuid4()}.{file_ext}"
        
        # Créer le dossier de destination
        class_folder = os.path.join(current_app.root_path, 'uploads', 'class_files', str(classroom_id))
        os.makedirs(class_folder, exist_ok=True)
        
        # Sauvegarder le fichier
        file_path = os.path.join(class_folder, unique_filename)
        file.save(file_path)
        
        # Créer la description avec le chemin du dossier
        description = "Uploadé directement"
        if folder_path:
            description = f"Copié dans le dossier: {folder_path}"
        
        # Créer l'entrée dans la base de données
        class_file = ClassFile(
            classroom_id=classroom_id,
            filename=unique_filename,
            original_filename=secure_filename(file.filename),
            file_type=file_ext,
            file_size=os.path.getsize(file_path),
            description=description
        )
        
        db.session.add(class_file)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Fichier uploadé avec succès',
            'file': {
                'id': class_file.id,
                'name': class_file.original_filename
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'}), 500

@class_files_bp.route('/preview/<int:file_id>')
@login_required
def preview_class_file(file_id):
    """Aperçu d'un fichier de classe"""
    try:
        from flask import send_file, current_app
        
        # Vérifier que le fichier appartient à une classe de l'utilisateur
        class_file = db.session.query(ClassFile).join(
            Classroom, ClassFile.classroom_id == Classroom.id
        ).filter(
            ClassFile.id == file_id,
            Classroom.user_id == current_user.id
        ).first()
        
        if not class_file:
            return jsonify({'success': False, 'message': 'Fichier introuvable'}), 404
        
        file_path = os.path.join(current_app.root_path, 'uploads', 'class_files', 
                               str(class_file.classroom_id), class_file.filename)
        
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'message': 'Fichier physique introuvable'}), 404
        
        # Déterminer le type MIME
        mimetype = 'application/octet-stream'
        if class_file.file_type == 'pdf':
            mimetype = 'application/pdf'
        elif class_file.file_type in ['png', 'jpg', 'jpeg']:
            mimetype = f'image/{class_file.file_type}'
        
        return send_file(file_path, mimetype=mimetype)
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'}), 500

@class_files_bp.route('/download/<int:file_id>')
@login_required
def download_class_file(file_id):
    """Télécharger un fichier de classe"""
    try:
        from flask import send_file, current_app
        
        # Vérifier que le fichier appartient à une classe de l'utilisateur
        class_file = db.session.query(ClassFile).join(
            Classroom, ClassFile.classroom_id == Classroom.id
        ).filter(
            ClassFile.id == file_id,
            Classroom.user_id == current_user.id
        ).first()
        
        if not class_file:
            return jsonify({'success': False, 'message': 'Fichier introuvable'}), 404
        
        file_path = os.path.join(current_app.root_path, 'uploads', 'class_files', 
                               str(class_file.classroom_id), class_file.filename)
        
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'message': 'Fichier physique introuvable'}), 404
        
        return send_file(
            file_path, 
            as_attachment=True,
            download_name=class_file.original_filename
        )
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'}), 500

@class_files_bp.route('/rename', methods=['PUT'])
@login_required
def rename_class_item():
    """Renommer un fichier ou dossier de classe"""
    try:
        data = request.get_json()
        item_type = data.get('type')
        item_id = data.get('id')
        new_name = data.get('name', '').strip()
        
        if not item_type or not item_id or not new_name:
            return jsonify({'success': False, 'message': 'Paramètres manquants'}), 400
        
        if item_type == 'file':
            # Vérifier que le fichier appartient à une classe de l'utilisateur
            class_file = db.session.query(ClassFile).join(
                Classroom, ClassFile.classroom_id == Classroom.id
            ).filter(
                ClassFile.id == item_id,
                Classroom.user_id == current_user.id
            ).first()
            
            if not class_file:
                return jsonify({'success': False, 'message': 'Fichier introuvable'}), 404
            
            # Garder l'extension originale
            if '.' in class_file.original_filename:
                ext = class_file.original_filename.rsplit('.', 1)[1]
                if not new_name.endswith(f'.{ext}'):
                    new_name = f"{new_name}.{ext}"
            
            class_file.original_filename = new_name
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Fichier renommé avec succès'
            })
        
        # TODO: implémenter le renommage de dossiers
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'}), 500

# Pour le moment, les dossiers ne sont pas implémentés dans la base de données
# Les dossiers sont simulés via la description des fichiers
@class_files_bp.route('/create-folder', methods=['POST'])
@login_required
def create_class_folder():
    """Créer un dossier dans une classe (simulé)"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        classroom_id = data.get('classroom_id')
        parent_id = data.get('parent_id')  # Non utilisé pour le moment
        
        if not name or not classroom_id:
            return jsonify({'success': False, 'message': 'Paramètres manquants'}), 400
        
        # Vérifier que la classe appartient à l'utilisateur
        classroom = Classroom.query.filter_by(
            id=classroom_id,
            user_id=current_user.id
        ).first()
        
        if not classroom:
            return jsonify({'success': False, 'message': 'Classe introuvable'}), 404
        
        # Pour le moment, on retourne juste un succès
        # Les dossiers sont gérés via la description des fichiers
        return jsonify({
            'success': True,
            'message': 'Dossier créé avec succès',
            'folder': {
                'id': str(uuid.uuid4()),  # ID temporaire
                'name': name
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'}), 500

@class_files_bp.route('/delete-folder-by-path', methods=['DELETE'])
@login_required
def delete_class_folder_by_path():
    """Supprimer tous les fichiers d'un dossier par son chemin"""
    try:
        data = request.get_json()
        classroom_id = data.get('classroom_id')
        folder_path = data.get('folder_path', '').strip()
        
        if not classroom_id or not folder_path:
            return jsonify({'success': False, 'message': 'Paramètres manquants'}), 400
        
        # Vérifier que la classe appartient à l'utilisateur
        classroom = Classroom.query.filter_by(
            id=classroom_id,
            user_id=current_user.id
        ).first()
        
        if not classroom:
            return jsonify({'success': False, 'message': 'Classe introuvable'}), 404
        
        # Trouver tous les fichiers qui sont dans ce dossier ou ses sous-dossiers
        files_to_delete = ClassFile.query.filter(
            ClassFile.classroom_id == classroom_id,
            ClassFile.description.like(f'%{folder_path}%')
        ).all()
        
        deleted_count = 0
        
        for class_file in files_to_delete:
            # Vérifier que le fichier est vraiment dans ce dossier
            if class_file.description and folder_path in class_file.description:
                try:
                    # Supprimer le fichier physique
                    from flask import current_app
                    file_path = os.path.join(current_app.root_path, 'uploads', 'class_files', 
                                           str(classroom_id), class_file.filename)
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        print(f"✅ Fichier physique supprimé: {file_path}")
                except Exception as e:
                    print(f"⚠️  Erreur lors de la suppression du fichier physique: {e}")
                
                # Supprimer l'entrée de la base de données
                db.session.delete(class_file)
                deleted_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Dossier supprimé avec {deleted_count} fichier(s)',
            'deleted_count': deleted_count
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'}), 500