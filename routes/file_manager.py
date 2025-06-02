from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from extensions import db
import os
import uuid
from datetime import datetime
from PIL import Image
from models.file_manager import FileFolder, UserFile
import io

# Importer les modèles après leur création
# from models.file_manager import FileFolder, UserFile

file_manager_bp = Blueprint('file_manager', __name__, url_prefix='/files')

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
    from models.file_manager import FileFolder

    folder = FileFolder.query.filter_by(
        id=folder_id,
        user_id=current_user.id
    ).first_or_404()

    try:
        # Fonction récursive pour supprimer les fichiers
        def delete_folder_files(folder):
            # Supprimer les fichiers du dossier
            for file in folder.files:
                file_path = os.path.join(current_app.root_path, file.get_file_path())
                if os.path.exists(file_path):
                    os.remove(file_path)

                if file.thumbnail_path:
                    thumbnail_path = os.path.join(current_app.root_path, file.get_thumbnail_path())
                    if os.path.exists(thumbnail_path):
                        os.remove(thumbnail_path)

            # Supprimer les fichiers des sous-dossiers
            for subfolder in folder.subfolders:
                delete_folder_files(subfolder)

        # Supprimer tous les fichiers
        delete_folder_files(folder)

        # Supprimer le dossier de la base de données (cascade supprimera les sous-dossiers et fichiers)
        db.session.delete(folder)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Dossier supprimé avec succès'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

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
