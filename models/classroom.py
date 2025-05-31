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

    def __repr__(self):
        return f'<Classroom {self.name} - {self.subject}>'
