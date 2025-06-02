from extensions import db
from datetime import datetime
import os

class FileFolder(db.Model):
    """Modèle pour les dossiers"""
    __tablename__ = 'file_folders'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('file_folders.id'), nullable=True)
    name = db.Column(db.String(255), nullable=False)
    color = db.Column(db.String(7), default='#4F46E5')  # Couleur hexadécimale
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    user = db.relationship('User', backref=db.backref('folders', lazy='dynamic'))
    parent = db.relationship('FileFolder', remote_side=[id], backref='subfolders')
    files = db.relationship('UserFile', backref='folder', lazy='dynamic', cascade='all, delete-orphan')

    def get_path(self):
        """Retourne le chemin complet du dossier"""
        if self.parent:
            return f"{self.parent.get_path()}/{self.name}"
        return self.name

    def get_size(self):
        """Calcule la taille totale du dossier"""
        total_size = 0
        # Taille des fichiers directs
        for file in self.files:
            total_size += file.file_size or 0
        # Taille des sous-dossiers
        for subfolder in self.subfolders:
            total_size += subfolder.get_size()
        return total_size

    def get_file_count(self):
        """Compte le nombre total de fichiers dans le dossier et ses sous-dossiers"""
        count = self.files.count()
        for subfolder in self.subfolders:
            count += subfolder.get_file_count()
        return count

    def __repr__(self):
        return f'<FileFolder {self.name}>'


class UserFile(db.Model):
    """Modèle pour les fichiers utilisateur"""
    __tablename__ = 'user_files'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    folder_id = db.Column(db.Integer, db.ForeignKey('file_folders.id'), nullable=True)
    filename = db.Column(db.String(255), nullable=False)  # Nom du fichier stocké
    original_filename = db.Column(db.String(255), nullable=False)  # Nom original
    file_type = db.Column(db.String(10), nullable=False)  # pdf, png, jpg
    file_size = db.Column(db.Integer)  # Taille en octets
    mime_type = db.Column(db.String(100))
    description = db.Column(db.Text)
    thumbnail_path = db.Column(db.String(255))  # Chemin vers la miniature pour les images
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relations
    user = db.relationship('User', backref=db.backref('files', lazy='dynamic'))

    def get_file_path(self):
        """Retourne le chemin complet du fichier"""
        return os.path.join('uploads', 'files', str(self.user_id), self.filename)

    def get_thumbnail_path(self):
        """Retourne le chemin de la miniature"""
        if self.thumbnail_path:
            return os.path.join('uploads', 'thumbnails', str(self.user_id), self.thumbnail_path)
        return None

    def format_size(self):
        """Formate la taille du fichier de manière lisible"""
        if not self.file_size:
            return "0 B"

        units = ['B', 'KB', 'MB', 'GB']
        size = float(self.file_size)
        unit_index = 0

        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1

        return f"{size:.1f} {units[unit_index]}"

    def __repr__(self):
        return f'<UserFile {self.original_filename}>'


class FileShare(db.Model):
    """Modèle pour le partage de fichiers (future fonctionnalité)"""
    __tablename__ = 'file_shares'

    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey('user_files.id'), nullable=False)
    shared_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    shared_with_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=True)
    permission = db.Column(db.String(20), default='read')  # read, write
    expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relations
    file = db.relationship('UserFile', backref='shares')
    shared_by = db.relationship('User', foreign_keys=[shared_by_id])
    shared_with = db.relationship('User', foreign_keys=[shared_with_id])
    classroom = db.relationship('Classroom', backref='file_shares')

    def __repr__(self):
        return f'<FileShare {self.id}>'
