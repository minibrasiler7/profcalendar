from flask import Flask
from extensions import db, login_manager, migrate
from config import Config
import os

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

    app.register_blueprint(auth_bp)
    app.register_blueprint(setup_bp)
    app.register_blueprint(schedule_bp)
    app.register_blueprint(planning_bp)

    # Route d'accueil
    @app.route('/')
    def index():
        from flask_login import current_user
        from flask import redirect, url_for

        if current_user.is_authenticated:
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
    with app.app_context():
        db.create_all()

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

    @app.template_filter('format_date_full')
    def format_date_full(date):
        if date:
            months = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin',
                     'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']
            return f"{date.day} {months[date.month-1]}"
        return ''

    return app
