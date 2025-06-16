#!/usr/bin/env python3
"""
Scénarios de test pour ProfCalendar - Rapport de tests
"""

import requests
import json
from datetime import datetime

class TestRunner:
    def __init__(self, base_url="http://127.0.0.1:5001"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
        
    def log_test(self, test_name, status, details=""):
        """Enregistrer le résultat d'un test"""
        result = {
            "test": test_name,
            "status": status,  # "PASS", "FAIL", "ERROR"
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        print(f"{'✅' if status == 'PASS' else '❌' if status == 'FAIL' else '⚠️'} {test_name}: {status}")
        if details:
            print(f"   📝 {details}")
    
    def test_teacher_login(self, email, password, expected_success=True):
        """Test de connexion enseignant"""
        try:
            response = self.session.post(f"{self.base_url}/auth/login", data={
                "email": email,
                "password": password
            }, allow_redirects=False)
            
            if expected_success:
                if response.status_code in [200, 302]:
                    self.log_test(f"Connexion enseignant {email}", "PASS")
                    return True
                else:
                    self.log_test(f"Connexion enseignant {email}", "FAIL", f"Status: {response.status_code}")
                    return False
            else:
                if response.status_code not in [200, 302]:
                    self.log_test(f"Connexion refusée {email}", "PASS")
                    return True
                else:
                    self.log_test(f"Connexion refusée {email}", "FAIL", "Connexion réussie alors qu'elle devrait échouer")
                    return False
        except Exception as e:
            self.log_test(f"Connexion enseignant {email}", "ERROR", str(e))
            return False
    
    def test_parent_login(self, email, password, expected_success=True):
        """Test de connexion parent"""
        try:
            response = self.session.post(f"{self.base_url}/parent/login", data={
                "email": email,
                "password": password
            }, allow_redirects=False)
            
            if expected_success:
                if response.status_code in [200, 302]:
                    self.log_test(f"Connexion parent {email}", "PASS")
                    return True
                else:
                    self.log_test(f"Connexion parent {email}", "FAIL", f"Status: {response.status_code}")
                    return False
            else:
                if response.status_code not in [200, 302]:
                    self.log_test(f"Connexion refusée parent {email}", "PASS")
                    return True
                else:
                    self.log_test(f"Connexion refusée parent {email}", "FAIL", "Connexion réussie alors qu'elle devrait échouer")
                    return False
        except Exception as e:
            self.log_test(f"Connexion parent {email}", "ERROR", str(e))
            return False
    
    def test_page_access(self, url, expected_status=200, test_name=None):
        """Test d'accès à une page"""
        if not test_name:
            test_name = f"Accès à {url}"
        
        try:
            response = self.session.get(f"{self.base_url}{url}", allow_redirects=False)
            if response.status_code == expected_status:
                self.log_test(test_name, "PASS")
                return True
            else:
                self.log_test(test_name, "FAIL", f"Status: {response.status_code}, attendu: {expected_status}")
                return False
        except Exception as e:
            self.log_test(test_name, "ERROR", str(e))
            return False
    
    def test_collaboration_restrictions(self):
        """Test des restrictions de collaboration"""
        # Test que les enseignants spécialisés ne peuvent pas devenir maîtres
        try:
            response = self.session.get(f"{self.base_url}/collaboration/")
            if response.status_code == 200:
                # Vérifier si la page contient les bonnes restrictions
                content = response.text
                if "Déjà un Maître" in content or "devient maître" not in content:
                    self.log_test("Restrictions collaboration", "PASS", "Restrictions visibles dans l'interface")
                    return True
                else:
                    self.log_test("Restrictions collaboration", "FAIL", "Restrictions non appliquées dans l'interface")
                    return False
            else:
                self.log_test("Restrictions collaboration", "FAIL", f"Impossible d'accéder à la page: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Restrictions collaboration", "ERROR", str(e))
            return False
    
    def test_parent_data_aggregation(self, student_id=1):
        """Test d'agrégation des données parent"""
        try:
            # Test grades
            response = self.session.get(f"{self.base_url}/parent/student/{student_id}/grades")
            if response.status_code == 200:
                data = response.json()
                if "subjects_data" in data and "all_evaluations" in data:
                    self.log_test("Agrégation données notes parent", "PASS")
                else:
                    self.log_test("Agrégation données notes parent", "FAIL", "Structure de données incorrecte")
                    return False
            else:
                self.log_test("Agrégation données notes parent", "FAIL", f"Status: {response.status_code}")
                return False
            
            # Test attendance
            response = self.session.get(f"{self.base_url}/parent/student/{student_id}/attendance")
            if response.status_code == 200:
                data = response.json()
                if "attendance_data" in data:
                    self.log_test("Agrégation données présence parent", "PASS")
                else:
                    self.log_test("Agrégation données présence parent", "FAIL", "Structure de données incorrecte")
                    return False
            else:
                self.log_test("Agrégation données présence parent", "FAIL", f"Status: {response.status_code}")
                return False
            
            return True
        except Exception as e:
            self.log_test("Agrégation données parent", "ERROR", str(e))
            return False
    
    def run_all_tests(self):
        """Exécuter tous les tests"""
        print("🧪 DÉBUT DES TESTS PROFCALENDAR")
        print("=" * 50)
        
        # Tests de base - vérification que le serveur répond
        print("\n📡 Tests de connectivité")
        self.test_page_access("/", 200, "Page d'accueil accessible")
        self.test_page_access("/auth/login", 200, "Page de connexion enseignant accessible")
        self.test_page_access("/parent/login", 200, "Page de connexion parent accessible")
        
        # Tests de connexion avec des comptes fictifs pour vérifier la logique
        print("\n🔐 Tests de connexion")
        # Ces tests vont échouer car les comptes n'existent pas, mais on vérifie la logique
        self.test_teacher_login("test@test.com", "wrongpass", expected_success=False)
        self.test_parent_login("test@test.com", "wrongpass", expected_success=False)
        
        # Tests d'accès aux pages protégées (doivent rediriger)
        print("\n🛡️ Tests de sécurité")
        self.test_page_access("/planning/manage_classes", 302, "Redirection page protégée enseignant")
        self.test_page_access("/parent/dashboard", 302, "Redirection page protégée parent")
        self.test_page_access("/collaboration/", 302, "Redirection page collaboration")
        
        # Tests d'API sans authentification (doivent échouer)
        print("\n🔒 Tests API sans auth")
        self.test_page_access("/parent/student/1/grades", 302, "API parent protégée")
        self.test_page_access("/planning/add-student", 405, "API enseignant protégée")
        
        print("\n" + "=" * 50)
        print("📊 RÉSUMÉ DES TESTS")
        
        total_tests = len(self.test_results)
        passed = len([t for t in self.test_results if t["status"] == "PASS"])
        failed = len([t for t in self.test_results if t["status"] == "FAIL"])
        errors = len([t for t in self.test_results if t["status"] == "ERROR"])
        
        print(f"Total: {total_tests}")
        print(f"✅ Réussis: {passed}")
        print(f"❌ Échoués: {failed}")
        print(f"⚠️ Erreurs: {errors}")
        print(f"📈 Taux de réussite: {(passed/total_tests*100):.1f}%")
        
        # Rapport détaillé des problèmes
        problems = [t for t in self.test_results if t["status"] in ["FAIL", "ERROR"]]
        if problems:
            print(f"\n🚨 PROBLÈMES DÉTECTÉS ({len(problems)}):")
            for problem in problems:
                print(f"• {problem['test']}: {problem['status']}")
                if problem['details']:
                    print(f"  → {problem['details']}")
        
        return self.test_results

def manual_test_scenarios():
    """Scénarios de test manuels à effectuer"""
    
    print("\n" + "=" * 60)
    print("📋 SCÉNARIOS DE TEST MANUELS À EFFECTUER")
    print("=" * 60)
    
    scenarios = [
        {
            "category": "🔐 Authentification",
            "tests": [
                "Se connecter avec un compte enseignant valide",
                "Se connecter avec un compte parent valide", 
                "Tenter une connexion avec des identifiants invalides",
                "Vérifier la déconnexion automatique après timeout",
                "Tester l'accès aux pages protégées sans connexion"
            ]
        },
        {
            "category": "👨‍🏫 Gestion Enseignants",
            "tests": [
                "Créer une nouvelle classe",
                "Ajouter des élèves à une classe",
                "Modifier les informations d'un élève",
                "Supprimer un élève d'une classe",
                "Créer des évaluations et attribuer des notes",
                "Gérer les présences/absences",
                "Appliquer des sanctions (coches)"
            ]
        },
        {
            "category": "🤝 Collaborations",
            "tests": [
                "Devenir maître de classe pour une classe originale",
                "Générer un code d'accès pour collaboration",
                "Se lier à un maître de classe avec un code",
                "Créer une classe dérivée depuis une collaboration",
                "Vérifier qu'un enseignant spécialisé ne peut pas devenir maître de sa classe dérivée",
                "Vérifier qu'une classe avec maître ne peut avoir un second maître",
                "Tester la suppression d'une collaboration",
                "Vérifier que les données des classes dérivées sont supprimées"
            ]
        },
        {
            "category": "👨‍👩‍👧‍👦 Interface Parents", 
            "tests": [
                "Inscription d'un nouveau parent",
                "Liaison parent-enseignant avec code classe",
                "Ajout d'un enfant supplémentaire dans une autre classe",
                "Consultation des notes d'un enfant (tableau unifié)",
                "Vérification des couleurs TA vs notes normales",
                "Consultation des absences/retards",
                "Consultation des sanctions (coches)",
                "Soumission d'une justification d'absence",
                "Vérifier l'agrégation des données multi-classes"
            ]
        },
        {
            "category": "📊 Données Multi-Classes",
            "tests": [
                "Élève présent dans classe originale ET dérivée",
                "Notes dans les deux classes visibles pour les parents", 
                "Absences dans les deux classes agrégées",
                "Sanctions dans les deux classes agrégées",
                "Modification d'un élève dans classe originale",
                "Vérifier la synchronisation avec classe dérivée"
            ]
        },
        {
            "category": "🔒 Sécurité & Permissions",
            "tests": [
                "Enseignant spécialisé ne peut modifier que ses élèves",
                "Enseignant spécialisé ne peut ajouter que des élèves du maître",
                "Parent ne peut voir que ses enfants",
                "Tentative d'accès direct aux données d'autres utilisateurs",
                "Vérification des CSRF tokens sur les formulaires",
                "Test d'injection SQL dans les champs de recherche"
            ]
        },
        {
            "category": "🐛 Cas Limites",
            "tests": [
                "Suppression d'un élève ayant des notes/absences/sanctions",
                "Suppression d'une classe avec des collaborations",
                "Maître de classe qui supprime sa maîtrise",
                "Code d'accès expiré ou épuisé",
                "Parent lié à plusieurs enseignants",
                "Élève sans email parent",
                "Classe sans élèves",
                "Évaluation sans notes",
                "Caractères spéciaux dans les noms"
            ]
        }
    ]
    
    for scenario in scenarios:
        print(f"\n{scenario['category']}")
        print("-" * 40)
        for i, test in enumerate(scenario['tests'], 1):
            print(f"{i:2d}. {test}")
    
    print(f"\n💡 POINTS D'ATTENTION PARTICULIERS")
    print("-" * 40)
    print("1. Vérifier que les enseignants spécialisés ne voient PAS le bouton 'Devenir Maître'")
    print("2. Confirmer que les notes TA sont en violet dans l'interface parent")
    print("3. Tester l'agrégation des données parent avec des élèves dans plusieurs classes")
    print("4. Vérifier que la suppression d'une collaboration supprime bien les classes dérivées")
    print("5. Confirmer que les permissions d'édition d'élèves sont respectées")
    print("6. Tester les cas où un élève existe dans classe originale mais pas dérivée")
    print("7. Vérifier la gestion des erreurs pour les élèves sans données parent")

if __name__ == "__main__":
    # Tests automatisés
    runner = TestRunner()
    results = runner.run_all_tests()
    
    # Scénarios manuels
    manual_test_scenarios()
    
    print(f"\n🎯 RECOMMANDATIONS")
    print("=" * 50)
    print("1. Créer les comptes de test avec le script SQL/Python")
    print("2. Effectuer les tests manuels dans l'ordre des catégories")
    print("3. Noter tous les problèmes rencontrés avec captures d'écran")
    print("4. Tester sur différents navigateurs (Chrome, Firefox, Safari)")
    print("5. Vérifier le responsive design sur mobile/tablette")
    print("6. Tester les performances avec beaucoup de données")