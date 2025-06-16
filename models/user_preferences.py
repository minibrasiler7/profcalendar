from extensions import db
from datetime import datetime

class UserPreferences(db.Model):
    """Préférences d'affichage et de fonctionnement pour l'utilisateur"""
    __tablename__ = 'user_preferences'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    
    # Préférences d'affichage des aménagements dans la vue lesson
    show_accommodations = db.Column(db.String(20), default='none')  # 'none', 'emoji', 'name'
    
    # Autres préférences futures peuvent être ajoutées ici
    # show_student_photos = db.Column(db.Boolean, default=False)
    # default_absence_view = db.Column(db.String(20), default='current')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    user = db.relationship('User', backref=db.backref('preferences', uselist=False))
    
    @staticmethod
    def get_or_create_for_user(user_id):
        """Récupère ou crée les préférences pour un utilisateur"""
        preferences = UserPreferences.query.filter_by(user_id=user_id).first()
        if not preferences:
            preferences = UserPreferences(user_id=user_id)
            db.session.add(preferences)
            db.session.commit()
        return preferences
    
    def __repr__(self):
        return f'<UserPreferences {self.user_id}>'