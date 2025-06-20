from extensions import db

class Classroom(db.Model):
    __tablename__ = 'classrooms'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    color = db.Column(db.String(7), nullable=False)  # Format hexadécimal #RRGGBB

    # Relations
    schedules = db.relationship('Schedule', backref='classroom', lazy='dynamic', cascade='all, delete-orphan')
    plannings = db.relationship('Planning', backref='classroom', lazy='dynamic', cascade='all, delete-orphan')

    def get_students(self):
        """Récupère les élèves de la classe (normale ou groupe mixte)"""
        if hasattr(self, 'mixed_group') and self.mixed_group:
            # C'est une classe auto-créée pour un groupe mixte
            return self.mixed_group.get_students()
        else:
            # C'est une classe normale
            from models.student import Student
            return Student.query.filter_by(classroom_id=self.id).all()
    
    def __repr__(self):
        return f'<Classroom {self.name} - {self.subject}>'
