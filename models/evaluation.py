from datetime import datetime
from extensions import db


class Evaluation(db.Model):
    """Modèle pour les évaluations des classes"""
    __tablename__ = 'evaluations'
    
    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'significatif' ou 'ta'
    ta_group_name = db.Column(db.String(100))  # Nom du groupe pour les TA
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    max_points = db.Column(db.Float, nullable=False)
    min_points = db.Column(db.Float, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    classroom = db.relationship('Classroom', backref='evaluations')
    evaluation_grades = db.relationship('EvaluationGrade', backref='evaluation', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Evaluation {self.title} - {self.classroom.name}>'
    
    def get_average(self):
        """Calcule la moyenne des notes pour cette évaluation"""
        if not self.evaluation_grades:
            return None
        
        valid_grades = [g.points for g in self.evaluation_grades if g.points is not None]
        if not valid_grades:
            return None
            
        return sum(valid_grades) / len(valid_grades)
    
    def get_grade_distribution(self):
        """Retourne la distribution des notes pour l'histogramme"""
        distribution = {}
        for grade in self.evaluation_grades:
            if grade.points is not None:
                points = round(grade.points, 1)
                distribution[points] = distribution.get(points, 0) + 1
        return distribution


class EvaluationGrade(db.Model):
    """Modèle pour les notes des étudiants dans les évaluations"""
    __tablename__ = 'evaluation_grades'
    
    id = db.Column(db.Integer, primary_key=True)
    evaluation_id = db.Column(db.Integer, db.ForeignKey('evaluations.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    points = db.Column(db.Float)  # Peut être null si pas encore noté
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    student = db.relationship('Student', backref='evaluation_grades')
    
    # Contrainte unique pour éviter les doublons
    __table_args__ = (db.UniqueConstraint('evaluation_id', 'student_id', name='unique_evaluation_grade_per_student'),)
    
    def __repr__(self):
        return f'<EvaluationGrade {self.student.full_name} - {self.evaluation.title}: {self.points}>'
    
    def get_percentage(self):
        """Calcule le pourcentage par rapport au maximum de points"""
        if self.points is None or self.evaluation.max_points == 0:
            return None
        return (self.points / self.evaluation.max_points) * 100
    
    def get_note_swiss(self):
        """Convertit en note suisse (1-6)"""
        percentage = self.get_percentage()
        if percentage is None:
            return None
        
        # Conversion pourcentage vers note suisse
        # 100% = 6, 0% = 1
        return 1 + (percentage / 100) * 5