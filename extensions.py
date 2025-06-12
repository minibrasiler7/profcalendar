from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate

# Initialisation des extensions
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()

# Configuration du user_loader pour gérer les deux types d'utilisateurs
@login_manager.user_loader
def load_user(user_id):
    """Charger un utilisateur (enseignant ou parent) par son ID composite"""
    from flask import session
    
    # L'ID composite a le format "type:id" (ex: "parent:1" ou "teacher:2")
    if ':' in str(user_id):
        user_type, actual_id = user_id.split(':', 1)
        
        if user_type == 'parent':
            from models.parent import Parent
            return Parent.query.get(int(actual_id))
        elif user_type == 'teacher':
            from models.user import User
            return User.query.get(int(actual_id))
    else:
        # Fallback pour la compatibilité avec les sessions existantes
        user_type = session.get('user_type', 'teacher')
        
        if user_type == 'parent':
            from models.parent import Parent
            return Parent.query.get(int(user_id))
        else:
            from models.user import User
            return User.query.get(int(user_id))
    
    return None
