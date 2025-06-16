from extensions import db
from datetime import datetime

class AccommodationTemplate(db.Model):
    """Modèles d'aménagements prédéfinis"""
    __tablename__ = 'accommodation_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    emoji = db.Column(db.String(10), nullable=False)  # Emoji représentant l'aménagement
    category = db.Column(db.String(100))  # ex: "Temps", "Matériel", "Consignes"
    is_time_extension = db.Column(db.Boolean, default=False)  # Si c'est un aménagement de temps
    time_multiplier = db.Column(db.Float)  # ex: 1.5 pour +50%, 1.33 pour +1/3
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    user = db.relationship('User', backref=db.backref('accommodation_templates', lazy='dynamic'))

class StudentAccommodation(db.Model):
    """Aménagements assignés aux élèves"""
    __tablename__ = 'student_accommodations'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('accommodation_templates.id'), nullable=True)
    
    # Champs pour aménagements personnalisés (si template_id est null)
    custom_name = db.Column(db.String(200))
    custom_description = db.Column(db.Text)
    custom_emoji = db.Column(db.String(10))
    custom_is_time_extension = db.Column(db.Boolean, default=False)
    custom_time_multiplier = db.Column(db.Float)
    
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)  # Notes spécifiques pour cet élève
    
    # Relations
    student = db.relationship('Student', backref=db.backref('accommodations', lazy='dynamic'))
    template = db.relationship('AccommodationTemplate', backref=db.backref('student_accommodations', lazy='dynamic'))
    
    @property
    def name(self):
        """Retourne le nom de l'aménagement (template ou personnalisé)"""
        return self.template.name if self.template else self.custom_name
    
    @property
    def description(self):
        """Retourne la description de l'aménagement (template ou personnalisé)"""
        return self.template.description if self.template else self.custom_description
    
    @property
    def emoji(self):
        """Retourne l'emoji de l'aménagement (template ou personnalisé)"""
        return self.template.emoji if self.template else self.custom_emoji
    
    @property
    def is_time_extension(self):
        """Retourne si c'est un aménagement de temps"""
        return self.template.is_time_extension if self.template else self.custom_is_time_extension
    
    @property
    def time_multiplier(self):
        """Retourne le multiplicateur de temps"""
        return self.template.time_multiplier if self.template else self.custom_time_multiplier

    def __repr__(self):
        return f'<StudentAccommodation {self.student_id}: {self.name}>'