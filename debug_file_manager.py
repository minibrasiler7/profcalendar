#!/usr/bin/env python3
"""
Script de diagnostic pour le problème d'affichage des classes dans le gestionnaire de fichiers
"""

import sys
import os

# Ajouter le répertoire du projet au path Python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_database_classes():
    """Test 1: Vérifier les classes dans la base de données"""
    print("=" * 60)
    print("TEST 1: Vérification des classes dans la base de données")
    print("=" * 60)
    
    with app.app_context():
        # Compter le nombre total de classes
        total_classes = Classroom.query.count()
        print(f"Nombre total de classes dans la DB: {total_classes}")
        
        # Lister les utilisateurs et leurs classes
        users = User.query.all()
        for user in users:
            user_classes = Classroom.query.filter_by(user_id=user.id).all()
            print(f"\nUtilisateur {user.id} ({user.email}):")
            print(f"  - Nombre de classes: {len(user_classes)}")
            for cls in user_classes:
                student_count = cls.students.count() if hasattr(cls, 'students') else 0
                print(f"  - Classe {cls.id}: {cls.name} ({cls.subject}) - {student_count} élèves")

def test_route_access():
    """Test 2: Vérifier l'accès à la route get-user-classes"""
    print("\n" + "=" * 60)
    print("TEST 2: Test de la route /file_manager/get-user-classes")
    print("=" * 60)
    
    # Démarrer le serveur de test
    with app.test_client() as client:
        # Simuler une connexion
        with client.session_transaction() as sess:
            # Vous devrez ajuster ceci selon votre système d'authentification
            # Pour le moment, on teste juste si la route existe
            pass
        
        # Tester la route sans authentification
        response = client.get('/file_manager/get-user-classes')
        print(f"Code de réponse sans auth: {response.status_code}")
        
        if response.status_code == 302:  # Redirection (pas connecté)
            print("→ La route redirige (probablement vers login)")
        elif response.status_code == 200:
            print("→ La route répond avec succès")
            print(f"Contenu: {response.get_json()}")
        else:
            print(f"→ Erreur: {response.status_code}")

def test_javascript_errors():
    """Test 3: Générer du code pour tester les erreurs JavaScript"""
    print("\n" + "=" * 60)
    print("TEST 3: Code JavaScript de diagnostic")
    print("=" * 60)
    
    js_test_code = """
// Copiez ce code dans la console du navigateur sur la page /file_manager/

console.log('=== DIAGNOSTIC FILE MANAGER ===');

// 1. Vérifier si l'élément classesList existe
const classesList = document.getElementById('classesList');
console.log('Element classesList trouvé:', classesList ? 'OUI' : 'NON');
if (classesList) {
    console.log('Contenu HTML:', classesList.innerHTML.substring(0, 200) + '...');
}

// 2. Vérifier si le JS est chargé
console.log('Fonction loadClasses existe:', typeof loadClasses !== 'undefined' ? 'OUI' : 'NON');
console.log('Variable classes:', typeof classes !== 'undefined' ? classes : 'NON DÉFINIE');

// 3. Tester manuellement le chargement des classes
if (typeof loadClasses !== 'undefined') {
    console.log('Tentative de chargement des classes...');
    fetch('/file_manager/get-user-classes')
        .then(response => {
            console.log('Statut de la réponse:', response.status);
            return response.json();
        })
        .then(data => {
            console.log('Données reçues:', data);
            if (data.success && data.classes) {
                console.log('Nombre de classes:', data.classes.length);
                data.classes.forEach(cls => {
                    console.log(`- Classe: ${cls.name} (ID: ${cls.id}, ${cls.student_count} élèves)`);
                });
            }
        })
        .catch(error => {
            console.error('Erreur lors du chargement:', error);
        });
} else {
    console.error('La fonction loadClasses n\'est pas définie!');
}

// 4. Vérifier les erreurs dans la console
console.log('=== FIN DIAGNOSTIC ===');
"""
    
    print("Copiez et exécutez ce code JavaScript dans la console du navigateur:")
    print("-" * 60)
    print(js_test_code)
    print("-" * 60)

def test_template_structure():
    """Test 4: Vérifier la structure du template"""
    print("\n" + "=" * 60)
    print("TEST 4: Vérification du template")
    print("=" * 60)
    
    import os
    template_path = os.path.join(app.root_path, 'templates/file_manager/index.html')
    
    if os.path.exists(template_path):
        print(f"Template trouvé: {template_path}")
        with open(template_path, 'r') as f:
            content = f.read()
            
        # Vérifier les éléments clés
        checks = [
            ('id="classesList"', 'Element classesList'),
            ('classes-section', 'Section des classes'),
            ('file_manager.js', 'Import du JS file_manager'),
            ('Mes classes', 'Titre "Mes classes"')
        ]
        
        for search_str, description in checks:
            if search_str in content:
                print(f"✓ {description}: TROUVÉ")
                # Afficher le contexte
                index = content.find(search_str)
                context = content[max(0, index-50):index+100]
                print(f"  Contexte: ...{context}...")
            else:
                print(f"✗ {description}: NON TROUVÉ")
    else:
        print(f"✗ Template non trouvé: {template_path}")

def test_routes_registration():
    """Test 5: Vérifier l'enregistrement des routes"""
    print("\n" + "=" * 60)
    print("TEST 5: Routes enregistrées")
    print("=" * 60)
    
    with app.app_context():
        # Lister toutes les routes file_manager
        print("Routes file_manager disponibles:")
        for rule in app.url_map.iter_rules():
            if 'file_manager' in rule.rule:
                print(f"  - {rule.rule} [{', '.join(rule.methods - {'HEAD', 'OPTIONS'})}]")

if __name__ == '__main__':
    print("DIAGNOSTIC DU GESTIONNAIRE DE FICHIERS")
    print("=" * 60)
    
    # Exécuter tous les tests
    test_database_classes()
    test_route_access()
    test_javascript_errors()
    test_template_structure()
    test_routes_registration()
    
    print("\n" + "=" * 60)
    print("DIAGNOSTIC TERMINÉ")
    print("=" * 60)