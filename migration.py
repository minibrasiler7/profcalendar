from app import create_app, db
from models.file_manager import FileFolder, UserFile

app = create_app()

with app.app_context():
    db.create_all()
    print("Tables du gestionnaires de fichiers créés")
