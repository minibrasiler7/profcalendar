#!/usr/bin/env python3
"""
Debug des routes pour identifier les problèmes
"""

def check_routes():
    print("🔍 Vérification des routes...")
    
    # Lire le fichier app.py pour voir si les routes sont bien enregistrées
    try:
        with open('app.py', 'r') as f:
            content = f.read()
            if 'class_files_bp' in content:
                print("✅ Blueprint class_files_bp trouvé dans app.py")
            else:
                print("❌ Blueprint class_files_bp MANQUANT dans app.py")
                
        print("\n📋 Routes qui devraient être disponibles:")
        print("   POST /api/class-files/copy-file")
        print("   POST /api/class-files/copy-folder")
        print("   GET  /api/class-files/list/<class_id>")
        print("   DELETE /api/class-files/delete/<file_id>")
        
        # Vérifier si le fichier routes/class_files.py existe
        try:
            with open('routes/class_files.py', 'r') as f:
                print("✅ Fichier routes/class_files.py existe")
        except FileNotFoundError:
            print("❌ Fichier routes/class_files.py MANQUANT")
            
        # Vérifier si le modèle existe
        try:
            with open('models/class_file.py', 'r') as f:
                print("✅ Fichier models/class_file.py existe")
        except FileNotFoundError:
            print("❌ Fichier models/class_file.py MANQUANT")
            
    except Exception as e:
        print(f"❌ Erreur: {e}")

def check_javascript():
    print("\n🔍 Vérification du JavaScript...")
    
    try:
        # Vérifier que les nouvelles fonctions existent
        with open('static/js/file_manager.js', 'r') as f:
            content = f.read()
            if 'copyFileToClassNew' in content:
                print("✅ Fonction copyFileToClassNew trouvée")
            else:
                print("❌ Fonction copyFileToClassNew MANQUANTE")
                
            if '/api/class-files/copy-file' in content:
                print("✅ Appel API vers /api/class-files/copy-file trouvé")
            else:
                print("❌ Appel API vers /api/class-files/copy-file MANQUANT")
                
        with open('static/js/class_files.js', 'r') as f:
            content = f.read()
            if 'window.classFileManager' in content:
                print("✅ Exposition globale window.classFileManager trouvée")
            else:
                print("❌ Exposition globale window.classFileManager MANQUANTE")
                
    except Exception as e:
        print(f"❌ Erreur JavaScript: {e}")

def suggest_debugging():
    print("\n🔧 Pour déboguer:")
    print("1. Ouvrez les outils de développement (F12)")
    print("2. Allez dans l'onglet Network")
    print("3. Faites un drag & drop d'un fichier sur une classe")
    print("4. Vérifiez si vous voyez des requêtes vers /api/class-files/")
    print("5. Si oui, regardez la réponse (200 OK ou erreur)")
    print("6. Si non, c'est que le JavaScript ne s'exécute pas")
    
    print("\n🐛 Erreurs possibles:")
    print("- Routes non enregistrées dans app.py")
    print("- Tables pas créées dans la base de données")
    print("- Erreur JavaScript (vérifiez la console)")
    print("- Conflit entre ancien et nouveau système")

if __name__ == "__main__":
    print("=" * 60)
    print("DEBUG DU SYSTÈME DE COPIE DE FICHIERS")
    print("=" * 60)
    
    check_routes()
    check_javascript()
    suggest_debugging()