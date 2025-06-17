from extensions import db
from datetime import datetime

class Schedule(db.Model):
    """Horaire type hebdomadaire"""
    __tablename__ = 'schedules'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Classe traditionnelle OU groupe mixte (l'un des deux doit être défini)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=True)
    mixed_group_id = db.Column(db.Integer, db.ForeignKey('mixed_groups.id'), nullable=True)

    # Jour de la semaine (0=Lundi, 1=Mardi, ..., 4=Vendredi)
    weekday = db.Column(db.Integer, nullable=False)

    # Numéro de la période dans la journée
    period_number = db.Column(db.Integer, nullable=False)

    # Heures calculées automatiquement basées sur la configuration utilisateur
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    
    # Note spécifique pour ce créneau (optionnel)
    notes = db.Column(db.Text)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'weekday', 'period_number', name='_user_weekday_period_uc'),
        db.CheckConstraint('(classroom_id IS NOT NULL AND mixed_group_id IS NULL) OR (classroom_id IS NULL AND mixed_group_id IS NOT NULL)', 
                          name='_classroom_or_mixed_group'),
    )

    # Relations
    mixed_group = db.relationship('MixedGroup', backref=db.backref('schedules', lazy='dynamic'))

    def get_display_name(self):
        """Retourne le nom à afficher (classe ou groupe mixte)"""
        if self.classroom_id:
            return self.classroom.name
        elif self.mixed_group_id:
            return self.mixed_group.name
        return "Non défini"
    
    def get_subject(self):
        """Retourne la matière enseignée"""
        if self.classroom_id:
            return self.classroom.subject
        elif self.mixed_group_id:
            return self.mixed_group.subject
        return "Non défini"
    
    def get_students(self):
        """Retourne la liste des élèves concernés par ce créneau"""
        if self.classroom_id:
            return self.classroom.students.all()
        elif self.mixed_group_id:
            return self.mixed_group.get_students()
        return []
    
    def is_mixed_group(self):
        """Vérifie si ce créneau concerne un groupe mixte"""
        return self.mixed_group_id is not None
    
    def get_color(self):
        """Retourne la couleur pour l'affichage"""
        if self.mixed_group_id:
            return self.mixed_group.color
        return '#4a90e2'  # Couleur par défaut pour les classes

    def __repr__(self):
        days = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi']
        name = self.get_display_name()
        return f'<Schedule {days[self.weekday]} P{self.period_number} - {name}>'
