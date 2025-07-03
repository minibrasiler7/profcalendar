from extensions import db
from datetime import datetime

class UserPreferences(db.Model):
    """Préférences générales de l'utilisateur"""
    __tablename__ = 'user_preferences'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Affichage des aménagements
    # 'none' = pas d'affichage (défaut)
    # 'emoji' = affichage par emoji
    # 'name' = affichage par nom complet
    show_accommodations = db.Column(db.String(20), default='none', nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    user = db.relationship('User', backref='preferences')
    
    # Index unique pour un seul paramétrage par utilisateur
    __table_args__ = (db.UniqueConstraint('user_id', name='unique_user_prefs'),)
    
    @classmethod
    def get_or_create_for_user(cls, user_id):
        """Récupérer ou créer les préférences pour un utilisateur"""
        preferences = cls.query.filter_by(user_id=user_id).first()
        if not preferences:
            preferences = cls(user_id=user_id)
            db.session.add(preferences)
            db.session.commit()
        return preferences
    
    def __repr__(self):
        return f'<UserPreferences {self.user.username} - {self.show_accommodations}>'

class UserSanctionPreferences(db.Model):
    """Préférences d'affichage des sanctions/coches par classe"""
    __tablename__ = 'user_sanction_preferences'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.id'), nullable=False)
    
    # Mode d'affichage des coches
    # 'unified' = tableau unique pour toutes les disciplines (défaut)
    # 'separated' = tableau séparé pour chaque discipline  
    # 'centralized' = coches centralisées (seulement pour maîtres de classe)
    display_mode = db.Column(db.String(20), default='unified', nullable=False)
    
    # Indique si ce mode est verrouillé par le maître de classe
    is_locked = db.Column(db.Boolean, default=False, nullable=False)
    
    # ID du maître de classe qui a verrouillé le mode (si applicable)
    locked_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    user = db.relationship('User', foreign_keys=[user_id], backref='sanction_preferences')
    classroom = db.relationship('Classroom', backref='sanction_preferences')
    locked_by_user = db.relationship('User', foreign_keys=[locked_by_user_id])
    
    # Index unique pour un seul paramétrage par utilisateur par classe
    __table_args__ = (db.UniqueConstraint('user_id', 'classroom_id', name='unique_user_classroom_sanction_prefs'),)
    
    @classmethod
    def get_or_create_for_user_classroom(cls, user_id, classroom_id):
        """Récupérer ou créer les préférences de sanctions pour un utilisateur et une classe"""
        preferences = cls.query.filter_by(user_id=user_id, classroom_id=classroom_id).first()
        if not preferences:
            preferences = cls(user_id=user_id, classroom_id=classroom_id)
            db.session.add(preferences)
            db.session.commit()
        return preferences
    
    def is_class_master(self):
        """Vérifier si l'utilisateur est maître de cette classe ou du groupe de classes"""
        from models.class_collaboration import ClassMaster
        from models.classroom import Classroom
        
        # D'abord vérifier directement cette classe
        direct_master = ClassMaster.query.filter_by(
            classroom_id=self.classroom_id,
            master_teacher_id=self.user_id
        ).first()
        
        if direct_master:
            return True
        
        # Si pas maître direct, vérifier si maître d'une autre classe du même groupe
        target_classroom = Classroom.query.get(self.classroom_id)
        if not target_classroom:
            return False
            
        group_name = target_classroom.class_group or target_classroom.name
        
        # Chercher le maître de classe dans toutes les classes du même groupe
        group_classrooms = Classroom.query.filter(
            (Classroom.class_group == group_name) if target_classroom.class_group 
            else (Classroom.name == group_name)
        ).all()
        
        for classroom in group_classrooms:
            class_master = ClassMaster.query.filter_by(
                classroom_id=classroom.id,
                master_teacher_id=self.user_id
            ).first()
            if class_master:
                return True
        
        return False
    
    def can_change_mode(self):
        """Vérifier si l'utilisateur peut changer le mode pour cette classe"""
        if self.is_class_master():
            return True
        return not self.is_locked
    
    def __repr__(self):
        return f'<UserSanctionPreferences {self.user.username} - {self.display_mode}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'display_mode': self.display_mode,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def lock_classroom_for_centralized_mode(cls, classroom_id, master_user_id):
        """Verrouiller une classe en mode centralisé"""
        from models.classroom import Classroom
        
        # Récupérer la classe et déterminer le groupe
        classroom = Classroom.query.get(classroom_id)
        if not classroom:
            return
            
        group_name = classroom.class_group or classroom.name
        
        # Trouver toutes les classes de ce groupe (tous utilisateurs confondus)
        group_classrooms = Classroom.query.filter(
            (Classroom.class_group == group_name) if classroom.class_group 
            else (Classroom.name == group_name)
        ).all()
        
        # Collecter tous les utilisateurs ayant des classes dans ce groupe
        all_group_users = set()
        for group_classroom in group_classrooms:
            all_group_users.add(group_classroom.user_id)
        
        # Verrouiller tous les enseignants de toutes les classes du groupe
        for group_classroom in group_classrooms:
            # Pour chaque utilisateur du groupe, créer ou mettre à jour les préférences
            for user_id in all_group_users:
                pref = cls.query.filter_by(
                    user_id=user_id, 
                    classroom_id=group_classroom.id
                ).first()
                
                if not pref:
                    # Créer les préférences manquantes
                    pref = cls(
                        user_id=user_id,
                        classroom_id=group_classroom.id,
                        display_mode='centralized'
                    )
                    db.session.add(pref)
                else:
                    pref.display_mode = 'centralized'
                
                # Configurer le verrouillage
                if user_id != master_user_id:
                    pref.is_locked = True
                    pref.locked_by_user_id = master_user_id
                else:
                    # Le maître reste en mode centralisé sans verrouillage
                    pref.is_locked = False
                    pref.locked_by_user_id = None
        
        db.session.commit()
    
    @classmethod
    def unlock_classroom_from_centralized_mode(cls, classroom_id, master_user_id):
        """Déverrouiller une classe du mode centralisé"""
        from models.classroom import Classroom
        
        # Récupérer la classe et déterminer le groupe
        classroom = Classroom.query.get(classroom_id)
        if not classroom:
            return
            
        group_name = classroom.class_group or classroom.name
        
        # Trouver toutes les classes de ce groupe (tous utilisateurs confondus)
        group_classrooms = Classroom.query.filter(
            (Classroom.class_group == group_name) if classroom.class_group 
            else (Classroom.name == group_name)
        ).all()
        
        # Collecter tous les utilisateurs ayant des classes dans ce groupe
        all_group_users = set()
        for group_classroom in group_classrooms:
            all_group_users.add(group_classroom.user_id)
        
        # Déverrouiller tous les enseignants de toutes les classes du groupe
        for group_classroom in group_classrooms:
            # Pour chaque utilisateur du groupe, mettre à jour les préférences
            for user_id in all_group_users:
                pref = cls.query.filter_by(
                    user_id=user_id, 
                    classroom_id=group_classroom.id
                ).first()
                
                if pref and user_id != master_user_id:
                    pref.is_locked = False
                    pref.locked_by_user_id = None
                    pref.display_mode = 'unified'  # Retour au mode par défaut
        
        db.session.commit()
    
    @classmethod
    def copy_sanction_templates_to_all_teachers(cls, classroom_id, master_user_id):
        """Copier les modèles de sanctions du maître vers tous les enseignants de la classe"""
        # Cette méthode est simplifiée car les modèles de sanctions sont globaux par utilisateur
        # et importés via ClassroomSanctionImport
        from models.sanctions import SanctionTemplate, ClassroomSanctionImport
        from models.student_sanctions import StudentSanctionCount
        from models.student import Student
        from models.classroom import Classroom
        
        # Récupérer la classe et déterminer le groupe
        classroom = Classroom.query.get(classroom_id)
        if not classroom:
            return
            
        group_name = classroom.class_group or classroom.name
        
        # Trouver toutes les classes de ce groupe (tous utilisateurs confondus)
        group_classrooms = Classroom.query.filter(
            (Classroom.class_group == group_name) if classroom.class_group 
            else (Classroom.name == group_name)
        ).all()
        
        # Récupérer tous les modèles du maître
        master_templates = SanctionTemplate.query.filter_by(user_id=master_user_id).all()
        
        # Collecter tous les utilisateurs ayant des classes dans ce groupe
        all_group_users = set()
        for group_classroom in group_classrooms:
            all_group_users.add(group_classroom.user_id)
        
        # Pour chaque classe du groupe, importer les modèles du maître
        for group_classroom in group_classrooms:
            # Pour chaque utilisateur du groupe (pas seulement ceux qui ont des préférences)
            for user_id in all_group_users:
                if user_id != master_user_id:
                    # Importer les modèles du maître dans la classe de cet enseignant
                    for template in master_templates:
                        # Vérifier si déjà importé
                        existing_import = ClassroomSanctionImport.query.filter_by(
                            classroom_id=group_classroom.id,
                            template_id=template.id
                        ).first()
                        
                        if not existing_import:
                            import_record = ClassroomSanctionImport(
                                classroom_id=group_classroom.id,
                                template_id=template.id,
                                is_active=True
                            )
                            db.session.add(import_record)
            
            # Remettre les coches à zéro pour tous les élèves de cette classe du groupe
            students = Student.query.filter_by(classroom_id=group_classroom.id).all()
            student_ids = [s.id for s in students]
            
            if student_ids:
                template_ids = [t.id for t in master_templates]
                if template_ids:
                    StudentSanctionCount.query.filter(
                        StudentSanctionCount.student_id.in_(student_ids),
                        StudentSanctionCount.template_id.in_(template_ids)
                    ).update({'check_count': 0}, synchronize_session=False)
        
        db.session.commit()
    
    @classmethod
    def cleanup_after_centralized_mode(cls, classroom_id, master_user_id):
        """Nettoyer après sortie du mode centralisé"""
        from models.sanctions import SanctionTemplate, ClassroomSanctionImport
        from models.student_sanctions import StudentSanctionCount
        from models.student import Student
        from models.classroom import Classroom
        
        # Récupérer la classe et déterminer le groupe
        classroom = Classroom.query.get(classroom_id)
        if not classroom:
            return
            
        group_name = classroom.class_group or classroom.name
        
        # Trouver toutes les classes de ce groupe (tous utilisateurs confondus)
        group_classrooms = Classroom.query.filter(
            (Classroom.class_group == group_name) if classroom.class_group 
            else (Classroom.name == group_name)
        ).all()
        
        # Pour chaque classe du groupe, nettoyer les imports de sanctions
        for group_classroom in group_classrooms:
            # Désactiver les imports de sanctions dans cette classe pour tous les enseignants
            # (chaque enseignant peut maintenant gérer ses propres modèles)
            ClassroomSanctionImport.query.filter_by(
                classroom_id=group_classroom.id
            ).update({'is_active': False}, synchronize_session=False)
            
            # Remettre les coches à zéro pour tous les élèves de cette classe
            students = Student.query.filter_by(classroom_id=group_classroom.id).all()
            student_ids = [s.id for s in students]
            
            if student_ids:
                # Récupérer tous les templates qui étaient importés dans cette classe
                imported_templates = db.session.query(SanctionTemplate.id).join(ClassroomSanctionImport).filter(
                    ClassroomSanctionImport.classroom_id == group_classroom.id
                ).distinct().all()
                
                template_ids = [t[0] for t in imported_templates]
                
                if template_ids:
                    StudentSanctionCount.query.filter(
                        StudentSanctionCount.student_id.in_(student_ids),
                        StudentSanctionCount.template_id.in_(template_ids)
                    ).update({'check_count': 0}, synchronize_session=False)
        
        db.session.commit()