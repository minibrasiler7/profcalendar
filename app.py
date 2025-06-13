from flask import Flask
from extensions import db, login_manager, migrate
from config import Config
import os

# Importer tous les modèles pour la création des tables
import models

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialiser les extensions avec l'app
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    # Configuration du login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'
    
    # Gestionnaire personnalisé pour les requêtes non autorisées
    @login_manager.unauthorized_handler
    def unauthorized():
        from flask import request, jsonify
        # Pour les requêtes AJAX, retourner une erreur JSON
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return jsonify({'error': 'Non autorisé. Veuillez vous connecter.'}), 401
        # Pour les requêtes normales, rediriger vers la page de login
        from flask import redirect, url_for
        return redirect(url_for('auth.login', next=request.url))

    # Activer les logs SQLAlchemy en mode debug
    if app.debug:
        import logging
        logging.basicConfig()
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

    # Gestion des erreurs pour le débogage
    @app.errorhandler(Exception)
    def handle_exception(e):
        if app.debug:
            # En mode debug, afficher l'erreur complète
            import traceback
            return f"<pre>{traceback.format_exc()}</pre>", 500
        # En production, afficher une page d'erreur générique
        return "Une erreur est survenue", 500

    # Créer les dossiers nécessaires
    os.makedirs(os.path.join(app.root_path, 'database'), exist_ok=True)

    # Importer et enregistrer les blueprints
    from routes.auth import auth_bp
    from routes.setup import setup_bp
    from routes.schedule import schedule_bp
    from routes.planning import planning_bp
    from routes.file_manager import file_manager_bp
    from routes.class_files import class_files_bp
    from routes.sanctions import sanctions_bp
    from routes.evaluations import evaluations_bp
    from routes.attendance import attendance_bp
    from routes.settings import settings_bp
    from routes.parent_auth import parent_auth_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(setup_bp)
    app.register_blueprint(schedule_bp)
    app.register_blueprint(planning_bp)
    app.register_blueprint(file_manager_bp)
    app.register_blueprint(class_files_bp)
    app.register_blueprint(sanctions_bp)
    app.register_blueprint(evaluations_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(parent_auth_bp)

    # Route d'accueil
    @app.route('/')
    def index():
        from flask_login import current_user
        from flask import redirect, url_for, session
        from models.parent import Parent

        if current_user.is_authenticated:
            # Vérifier si c'est un parent
            if isinstance(current_user, Parent):
                return redirect(url_for('parent_auth.dashboard'))
            
            # Pour les enseignants, continuer avec la logique existante
            # Étape 1 : Vérifier la configuration de base
            if not current_user.school_year_start or not current_user.day_start_time:
                return redirect(url_for('setup.initial_setup'))

            # Étape 2 : Vérifier qu'il y a au moins une classe
            if current_user.classrooms.count() == 0:
                return redirect(url_for('setup.manage_classrooms'))

            # Étape 3 : Vérifier que la configuration de base est marquée comme complète
            if not current_user.setup_completed:
                # Si les vacances/pauses ne sont pas encore configurées, aller aux vacances
                if current_user.holidays.count() == 0:
                    return redirect(url_for('setup.manage_holidays'))
                elif current_user.breaks.count() == 0:
                    return redirect(url_for('setup.manage_breaks'))
                else:
                    # Si tout est configuré mais pas validé, forcer la validation
                    return redirect(url_for('setup.validate_setup'))

            # Étape 4 : Vérifier l'horaire type
            if not current_user.schedule_completed:
                return redirect(url_for('schedule.weekly_schedule'))

            # Si tout est complété, aller au tableau de bord
            return redirect(url_for('planning.dashboard'))

        # Si pas connecté, aller à la page de connexion
        return redirect(url_for('auth.login'))

    # Route pour le favicon (éviter l'erreur 404)
    @app.route('/favicon.ico')
    def favicon():
        from flask import send_from_directory
        import os
        # Retourner une réponse vide si pas de favicon
        return '', 204

    # Créer les tables si elles n'existent pas
    os.makedirs(os.path.join(app.root_path, 'uploads', 'files'), exist_ok=True)
    os.makedirs(os.path.join(app.root_path, 'uploads', 'thumbnails'), exist_ok=True)
    with app.app_context():
        db.create_all()

    # Context processor pour rendre les informations de cours disponibles globalement
    @app.context_processor
    def inject_lesson_info():
        from flask_login import current_user

        if current_user.is_authenticated and hasattr(current_user, 'setup_completed') and current_user.setup_completed:
            try:
                from routes.planning import get_current_or_next_lesson
                lesson, is_current, lesson_date = get_current_or_next_lesson(current_user)

                return {
                    'global_current_lesson': lesson if is_current else None,
                    'global_next_lesson': lesson if not is_current else None,
                    'global_has_current_lesson': is_current
                }
            except:
                # En cas d'erreur, retourner des valeurs par défaut
                return {
                    'global_current_lesson': None,
                    'global_next_lesson': None,
                    'global_has_current_lesson': False
                }

        return {
            'global_current_lesson': None,
            'global_next_lesson': None,
            'global_has_current_lesson': False
        }

    # Filtres Jinja2 personnalisés
    @app.template_filter('format_date')
    def format_date(date):
        if date:
            months = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin',
                     'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']
            return f"{date.day} {months[date.month-1]} {date.year}"
        return ''

    @app.template_filter('format_month_year')
    def format_month_year(date):
        if date:
            months = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin',
                     'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']
            return f"{months[date.month-1]} {date.year}"
        return ''

    # Ajoutez cette fonction dans la fonction create_app après les filtres Jinja2 existants (vers la ligne 140)

    # Fonction helper pour rendre les checkboxes dans les plannings
    # Remplacer la fonction render_planning_with_checkboxes dans app.py (vers la ligne 145)

    @app.template_global()
    def render_planning_with_checkboxes(planning):
        """Rendre la description d'une planification avec les checkboxes"""
        if not planning or not planning.description:
            return 'Aucune description'

        import re
        lines = planning.description.split('\n')
        html = []
        checkbox_index = 0
        states = planning.get_checklist_states()

        for line in lines:
            # Vérifier si la ligne contient une checkbox
            checkbox_match = re.match(r'^(\s*)\[([ x])\]\s*(.*)$', line, re.IGNORECASE)

            if checkbox_match:
                indent = checkbox_match.group(1)
                content = checkbox_match.group(3)

                # Récupérer l'état de la checkbox depuis les données sauvegardées
                is_checked = states.get(str(checkbox_index), False)

                html.append(f'''<div class="planning-checklist-item" style="margin-left: {len(indent) * 20}px;">
                    <input type="checkbox" 
                           class="planning-checkbox" 
                           id="checkbox-{checkbox_index}" 
                           data-index="{checkbox_index}"
                           {'checked' if is_checked else ''}
                           onchange="updateCheckboxState({checkbox_index}, this.checked)">
                    <label for="checkbox-{checkbox_index}" class="planning-checkbox-label">{content}</label>
                </div>''')

                checkbox_index += 1
            else:
                # Ligne normale - échapper le HTML
                escaped_line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#039;')
                html.append(f'<div>{escaped_line}</div>')

        return '\n'.join(html)

    @app.template_filter('format_date_full')
    def format_date_full(date):
        if date:
            months = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin',
                     'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']
            return f"{date.day} {months[date.month-1]}"
        return ''

    return app
