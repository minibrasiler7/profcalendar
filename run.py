from app import create_app, db
from models import *  # Importer tous les modèles

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        # Créer toutes les tables si elles n'existent pas
        db.create_all()
        print("Base de données initialisée avec succès !")

    # Lancer l'application en mode debug
    app.run(debug=True, host='0.0.0.0', port=5001)
