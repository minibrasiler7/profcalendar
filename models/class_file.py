from extensions import db
from datetime import datetime
import os

class ClassFile(db.Model):
    """Nouveau modèle simplifié pour les fichiers de classe"""
    __tablename__ = 'class_files_v2'

    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False)
    user_file_id = db.Column(db.Integer, db.ForeignKey('user_files.id'), nullable=False)
    folder_path = db.Column(db.String(500), default='')  # Chemin du dossier dans la classe (ex: "Chapitre 1/Exercices")
    copied_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    classroom = db.relationship('Classroom', backref='class_files_v2')
    user_file = db.relationship('UserFile', backref='class_copies')
    
    def get_full_path(self):
        """Retourne le chemin complet du fichier dans la classe"""
        if self.folder_path:
            return f"{self.folder_path}/{self.user_file.original_filename}"
        return self.user_file.original_filename
    
    def get_display_folder(self):
        """Retourne le dossier d'affichage (ou 'Racine' si vide)"""
        return self.folder_path if self.folder_path else "Racine"
    
    def __repr__(self):
        return f'<ClassFile {self.user_file.original_filename} in {self.classroom.name}>'


class ClassFolder(db.Model):
    """Modèle pour les dossiers virtuels dans les classes"""
    __tablename__ = 'class_folders'
    
    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    parent_path = db.Column(db.String(500), default='')  # Chemin du parent (ex: "Chapitre 1")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    classroom = db.relationship('Classroom', backref='class_folders')
    
    def get_full_path(self):
        """Retourne le chemin complet du dossier"""
        if self.parent_path:
            return f"{self.parent_path}/{self.name}"
        return self.name
    
    def __repr__(self):
        return f'<ClassFolder {self.get_full_path()} in {self.classroom.name}>'