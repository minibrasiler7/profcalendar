#!/usr/bin/env python3
"""
Tests simples à exécuter depuis la ligne de commande
"""

def test_collaboration_restrictions():
    """Test des restrictions de collaboration"""
    print("🧪 TEST: Restrictions de Collaboration")
    print("=" * 40)
    
    print("1. Se connecter comme prof_sport@school.com")
    print("2. Aller sur http://127.0.0.1:5001/collaboration/")
    print("3. VÉRIFIER: Pas de bouton 'Devenir Maître' pour classe dérivée")
    print("4. Essayer: http://127.0.0.1:5001/collaboration/become-master/3")
    print("5. ATTENDU: Message d'erreur ou redirection")
    print()
    
    return input("✅ Test réussi ? (o/n): ").lower() == 'o'

def test_parent_aggregation():
    """Test d'agrégation des données parent"""
    print("🧪 TEST: Agrégation Données Parent")
    print("=" * 40)
    
    print("1. Se connecter comme marie.martin@parent.com")
    print("2. Aller sur le dashboard parent")
    print("3. Cliquer sur 'Notes' pour Alice")
    print("4. VÉRIFIER: Notes de Math + Français + Sport dans tableau unifié")
    print("5. VÉRIFIER: Notes TA en violet, notes normales en blanc")
    print()
    
    return input("✅ Test réussi ? (o/n): ").lower() == 'o'

def test_specialized_teacher_permissions():
    """Test des permissions enseignant spécialisé"""
    print("🧪 TEST: Permissions Enseignant Spécialisé")
    print("=" * 40)
    
    print("1. Se connecter comme prof_sport@school.com")
    print("2. Aller sur gestion des classes")
    print("3. Essayer de modifier Alice Martin")
    print("4. ATTENDU: Impossible de modifier, seulement supprimer")
    print("5. Essayer d'ajouter un élève")
    print("6. ATTENDU: Seulement les élèves de la classe du maître")
    print()
    
    return input("✅ Test réussi ? (o/n): ").lower() == 'o'

def test_collaboration_deletion():
    """Test de suppression de collaboration"""
    print("🧪 TEST: Suppression Collaboration")
    print("=" * 40)
    
    print("1. Se connecter comme prof_sport@school.com")
    print("2. Aller sur /collaboration/")
    print("3. Supprimer la collaboration avec prof_martin")
    print("4. VÉRIFIER: Classe dérivée Sport disparaît complètement")
    print("5. VÉRIFIER: Élèves de la classe dérivée supprimés")
    print("6. VÉRIFIER: Notes/absences de la classe dérivée supprimées")
    print()
    
    return input("✅ Test réussi ? (o/n): ").lower() == 'o'

def test_master_class_restrictions():
    """Test des restrictions maître de classe"""
    print("🧪 TEST: Restrictions Maître de Classe")
    print("=" * 40)
    
    print("1. Se connecter comme prof_durand@school.com")
    print("2. Aller sur /collaboration/")
    print("3. Essayer de devenir maître de la classe de prof_martin")
    print("4. ATTENDU: Bouton 'Déjà un Maître' ou pas de bouton")
    print("5. Essayer l'accès direct: /collaboration/become-master/1")
    print("6. ATTENDU: Message d'erreur")
    print()
    
    return input("✅ Test réussi ? (o/n): ").lower() == 'o'

def run_all_tests():
    """Exécuter tous les tests"""
    print("🚀 DÉBUT DES TESTS PROFCALENDAR")
    print("=" * 50)
    print("Assurez-vous que le serveur est lancé: python run.py")
    print("Et que vous avez des données de test")
    print()
    
    tests = [
        ("Restrictions Collaboration", test_collaboration_restrictions),
        ("Agrégation Parent", test_parent_aggregation),
        ("Permissions Spécialisé", test_specialized_teacher_permissions),
        ("Suppression Collaboration", test_collaboration_deletion),
        ("Restrictions Maître", test_master_class_restrictions),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        result = test_func()
        results.append((test_name, result))
        print(f"Résultat: {'✅ PASSÉ' if result else '❌ ÉCHOUÉ'}")
    
    print("\n" + "="*50)
    print("📊 RÉSULTATS FINAUX")
    print("="*50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSÉ" if result else "❌ ÉCHOUÉ"
        print(f"• {test_name}: {status}")
    
    print(f"\n📈 Score: {passed}/{total} ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("🎉 TOUS LES TESTS SONT PASSÉS!")
        print("L'application semble fonctionner correctement.")
    else:
        print("⚠️ CERTAINS TESTS ONT ÉCHOUÉ")
        print("Vérifiez les fonctionnalités qui ne marchent pas.")

if __name__ == "__main__":
    run_all_tests()