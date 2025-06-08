from extensions import db
from datetime import datetime
import json

class SanctionTemplate(db.Model):
    """Modèle de type de problème avec ses seuils et sanctions"""
    __tablename__ = 'sanction_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)  # "oubli", "comportement", etc.
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    user = db.relationship('User', backref='sanction_templates')
    thresholds = db.relationship('SanctionThreshold', backref='template', lazy='dynamic', cascade='all, delete-orphan')
    classroom_imports = db.relationship('ClassroomSanctionImport', backref='template', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<SanctionTemplate {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'is_active': self.is_active,
            'thresholds_count': self.thresholds.count(),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class SanctionThreshold(db.Model):
    """Seuil de sanctions (ex: 3 coches, 6 coches)"""
    __tablename__ = 'sanction_thresholds'
    
    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey('sanction_templates.id'), nullable=False)
    check_count = db.Column(db.Integer, nullable=False)  # Nombre de coches (3, 6, 9...)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    sanctions = db.relationship('SanctionOption', backref='threshold', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<SanctionThreshold {self.check_count} coches>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'check_count': self.check_count,
            'sanctions': [s.to_dict() for s in self.sanctions.all()]
        }

class SanctionOption(db.Model):
    """Option de sanction pour un seuil donné"""
    __tablename__ = 'sanction_options'
    
    id = db.Column(db.Integer, primary_key=True)
    threshold_id = db.Column(db.Integer, db.ForeignKey('sanction_thresholds.id'), nullable=False)
    description = db.Column(db.Text, nullable=False)  # "Copier pages 17-18 de l'aide-mémoire"
    min_days_deadline = db.Column(db.Integer, nullable=True)  # Nombre minimum de jours pour rendre (optionnel)
    order_index = db.Column(db.Integer, default=0)  # Pour l'ordre d'affichage
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<SanctionOption {self.description[:50]}...>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'description': self.description,
            'min_days_deadline': self.min_days_deadline,
            'order_index': self.order_index,
            'is_active': self.is_active
        }

class ClassroomSanctionImport(db.Model):
    """Liaison entre un modèle de sanction et une classe"""
    __tablename__ = 'classroom_sanction_imports'
    
    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('sanction_templates.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    imported_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    classroom = db.relationship('Classroom', backref='sanction_imports')
    
    # Index unique pour éviter les doublons
    __table_args__ = (db.UniqueConstraint('classroom_id', 'template_id', name='unique_classroom_template'),)
    
    def __repr__(self):
        return f'<ClassroomSanctionImport {self.classroom.name} - {self.template.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'classroom_id': self.classroom_id,
            'classroom_name': self.classroom.name,
            'template_id': self.template_id,
            'template_name': self.template.name,
            'is_active': self.is_active,
            'imported_at': self.imported_at.isoformat() if self.imported_at else None
        }

class StudentSanctionRecord(db.Model):
    """Historique des sanctions appliquées aux élèves"""
    __tablename__ = 'student_sanction_records'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('sanction_templates.id'), nullable=False)
    threshold_id = db.Column(db.Integer, db.ForeignKey('sanction_thresholds.id'), nullable=False)
    sanction_id = db.Column(db.Integer, db.ForeignKey('sanction_options.id'), nullable=False)
    
    # Détails de la sanction
    check_count_reached = db.Column(db.Integer, nullable=False)  # Nombre de coches atteint
    assigned_date = db.Column(db.Date, nullable=False)  # Date d'attribution
    deadline_date = db.Column(db.Date, nullable=False)  # Date limite de rendu
    completed_date = db.Column(db.Date)  # Date de completion (si complétée)
    
    # Statuts
    status = db.Column(db.String(20), default='assigned')  # assigned, completed, overdue
    notes = db.Column(db.Text)  # Notes additionnelles
    
    # Métadonnées
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    student = db.relationship('Student', backref='sanction_records')
    template = db.relationship('SanctionTemplate', backref='applied_records')
    threshold = db.relationship('SanctionThreshold', backref='applied_records')
    sanction = db.relationship('SanctionOption', backref='applied_records')
    
    def __repr__(self):
        return f'<StudentSanctionRecord {self.student.full_name} - {self.template.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'student_name': self.student.full_name,
            'template_name': self.template.name,
            'sanction_description': self.sanction.description,
            'check_count_reached': self.check_count_reached,
            'assigned_date': self.assigned_date.isoformat() if self.assigned_date else None,
            'deadline_date': self.deadline_date.isoformat() if self.deadline_date else None,
            'completed_date': self.completed_date.isoformat() if self.completed_date else None,
            'status': self.status,
            'notes': self.notes
        }