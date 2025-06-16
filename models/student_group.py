from extensions import db
from datetime import datetime

class StudentGroup(db.Model):
    """Modèle pour les groupes d'élèves"""
    __tablename__ = 'student_groups'

    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    color = db.Column(db.String(7), default='#4F46E5')  # Couleur hex pour identifier le groupe
    
    # Métadonnées
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    classroom = db.relationship('Classroom', backref=db.backref('student_groups', lazy='dynamic'))
    user = db.relationship('User', backref=db.backref('student_groups', lazy='dynamic'))
    
    def __repr__(self):
        return f'<StudentGroup {self.name}>'

class StudentGroupMembership(db.Model):
    """Table d'association pour les membres des groupes"""
    __tablename__ = 'student_group_memberships'

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('student_groups.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    
    # Métadonnées
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    group = db.relationship('StudentGroup', backref=db.backref('memberships', lazy='dynamic', cascade='all, delete-orphan'))
    student = db.relationship('Student', backref=db.backref('group_memberships', lazy='dynamic'))
    
    # Contrainte d'unicité
    __table_args__ = (
        db.UniqueConstraint('group_id', 'student_id', name='_group_student_uc'),
    )
    
    def __repr__(self):
        return f'<StudentGroupMembership group={self.group_id} student={self.student_id}>'