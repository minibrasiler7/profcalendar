# 🧪 RAPPORT DE TESTS - PROFCALENDAR

## 📋 Résumé Exécutif

Ce rapport détaille les tests recommandés et les problèmes potentiels identifiés dans l'application ProfCalendar, en se concentrant sur le système de collaboration enseignants-parents et la gestion des classes dérivées.

## 🎯 Comptes de Test Recommandés

### 👨‍🏫 Enseignants
- **prof_martin** (martin@school.com) - Maître de classe Math 6ème A
- **prof_durand** (durand@school.com) - Maître de classe Français 6ème A  
- **prof_sport** (sport@school.com) - Enseignant spécialisé (collabore avec prof_martin)
- **prof_smith** (smith@school.com) - Enseignant normal sans maîtrise

### 👨‍👩‍👧‍👦 Parents
- **marie.martin@parent.com** - Mère d'Alice (élève dans 2 classes)
- **sophie.durand@parent.com** - Mère de Bob (élève dans 2 classes)
- **anne.petit@parent.com** - Mère de Claire (1 classe seulement)

### 🎓 Élèves
- **Alice Martin** - Présente dans classe Math ET Français (test agrégation)
- **Bob Durand** - Présent dans classe Math ET Français + classe Sport dérivée
- **Claire Petit** - Présente uniquement en Math

## 🚨 PROBLÈMES CRITIQUES IDENTIFIÉS

### 1. **🔒 Sécurité des Permissions**

#### Problème Potentiel: Bypass des Restrictions
```python
# Dans routes/planning.py - Vérifier que cette logique est hermétique
def can_edit_student(student_id, current_user):
    # Si un enseignant spécialisé trouve un moyen de contourner cette vérification
    # il pourrait modifier des élèves qu'il ne devrait pas
```

**Test Critique**: 
- Enseignant spécialisé tente de modifier directement l'URL: `/planning/edit-student/123`
- Vérifier que l'erreur 403 est bien renvoyée

#### Problème Potentiel: Injection dans les Requêtes
```python
# Dans routes/parent_auth.py ligne 423-430
grades_query = db.session.query(EvaluationGrade, Evaluation, Classroom).join(...)
# Si student_id n'est pas validé, risque d'accès aux données d'autres élèves
```

**Test Critique**:
- Parent tente d'accéder: `/parent/student/999/grades` (élève qui n'est pas le sien)
- Vérifier que l'erreur 403 est bien renvoyée

### 2. **🔗 Intégrité des Données Multi-Classes**

#### Problème Potentiel: Désynchronisation
```python
# Quand un élève est modifié dans la classe originale
# Les copies dans les classes dérivées pourraient ne pas être mises à jour
```

**Tests Critiques**:
1. Modifier un élève dans classe originale → Vérifier synchronisation dans classe dérivée
2. Supprimer un élève de classe originale → Vérifier suppression dans classe dérivée
3. Ajouter un élève à classe originale → Vérifier qu'il n'apparaît PAS automatiquement dans dérivée

#### Problème Potentiel: Orphelins de Données
```python
# Si une collaboration est supprimée brutalement
# Risque de laisser des données orphelines
```

**Test Critique**:
- Supprimer une collaboration → Vérifier que TOUTES les données dérivées sont supprimées

### 3. **👨‍👩‍👧‍👦 Agrégation des Données Parents**

#### Problème Potentiel: Données Dupliquées/Manquantes
```python
# Dans get_all_linked_students() - ligne 21-48
# Si la logique de liaison est incorrecte, les parents pourraient voir :
# - Des données dupliquées
# - Des données manquantes
# - Des données d'autres élèves
```

**Tests Critiques**:
1. Parent avec enfant dans classe originale + dérivée → Vérifier agrégation correcte
2. Parent avec enfant dans plusieurs classes différentes → Vérifier séparation
3. Parent nouveau → Vérifier qu'il ne voit pas d'autres enfants

### 4. **🤝 Système de Collaboration**

#### Problème Potentiel: Classes Maîtres Multiples
```python
# Malgré les protections, vérifier qu'il n'y a pas de race condition
# permettant à 2 enseignants de devenir maîtres simultanément
```

**Test Critique**:
- 2 enseignants cliquent "Devenir Maître" en même temps pour la même classe

#### Problème Potentiel: Codes d'Accès
```python
# Vérifier que les codes expirés/épuisés sont bien gérés
```

**Tests Critiques**:
1. Utiliser un code d'accès expiré
2. Utiliser un code d'accès déjà épuisé
3. Réutiliser le même code plusieurs fois

## 🧪 SCÉNARIOS DE TEST PRIORITAIRES

### 🔥 **CRITIQUE - À tester en priorité**

1. **Test de Sécurité des Permissions**
   ```
   1. Connexion comme enseignant spécialisé (prof_sport)
   2. Tenter d'accéder directement à: /planning/edit-student/[ID_ELEVE_AUTRE_CLASSE]
   3. Résultat attendu: Erreur 403 ou redirection
   4. Résultat problématique: Accès accordé
   ```

2. **Test d'Agrégation Parent Multi-Classes**
   ```
   1. Connexion comme parent (marie.martin@parent.com)
   2. Aller sur dashboard → Voir notes d'Alice
   3. Vérifier que TOUTES les notes apparaissent (Math + Français + Sport si existe)
   4. Vérifier que les notes TA sont en violet
   5. Résultat problématique: Notes manquantes ou dupliquées
   ```

3. **Test de Restriction Maître de Classe**
   ```
   1. Connexion comme enseignant spécialisé (prof_sport)
   2. Aller sur /collaboration/
   3. Vérifier qu'il n'y a PAS de bouton "Devenir Maître" pour sa classe dérivée
   4. Tenter d'accéder directement à: /collaboration/become-master/[ID_CLASSE_DERIVEE]
   5. Résultat attendu: Erreur ou message d'interdiction
   ```

### ⚠️ **IMPORTANT - À tester ensuite**

4. **Test de Suppression de Collaboration**
   ```
   1. Connexion comme enseignant spécialisé
   2. Supprimer une collaboration
   3. Vérifier que la classe dérivée disparaît complètement
   4. Vérifier que les élèves de la classe dérivée sont supprimés
   5. Vérifier que les notes/absences de la classe dérivée sont supprimées
   ```

5. **Test de Synchronisation des Données**
   ```
   1. Connexion comme maître de classe (prof_martin)
   2. Modifier les informations d'un élève (Alice)
   3. Vérifier que les modifications apparaissent dans la classe dérivée Sport
   4. Vérifier que le parent voit les données mises à jour
   ```

## 🐛 BUGS POTENTIELS À SURVEILLER

### 1. **Erreurs de Référence**
- `'SharedClassroom' is not defined` - Corrigé mais surveiller les imports
- Variables undefined dans les templates Jinja2

### 2. **Contraintes Base de Données**
- `NOT NULL constraint failed: evaluation_grades.student_id` - Corrigé mais surveiller
- Suppressions en cascade qui échouent

### 3. **Logique Métier**
- Élèves fantômes dans les classes dérivées
- Parents qui voient des enfants qui ne sont plus dans leurs classes
- Maîtres de classe multiples pour la même classe

### 4. **Interface Utilisateur**
- Boutons qui s'affichent alors qu'ils ne devraient pas
- CSS selector invalides dans JavaScript
- Formulaires qui ne se soumettent pas

## 📊 MÉTRIQUES DE PERFORMANCE À VÉRIFIER

1. **Temps de chargement dashboard parent** (avec beaucoup d'élèves)
2. **Temps de calcul agrégation notes** (multi-classes)
3. **Mémoire utilisée** lors de suppressions en masse
4. **Requêtes SQL** générées (éviter N+1)

## 🔧 OUTILS DE TEST RECOMMANDÉS

1. **Tests Manuels**: Navigation dans l'interface
2. **Tests Navigateur**: Developer Tools pour voir les erreurs JS
3. **Tests Base de Données**: Vérifier l'intégrité des données
4. **Tests de Charge**: Beaucoup d'élèves/notes/absences

## ✅ CHECKLIST DE VALIDATION

- [ ] Enseignant spécialisé ne peut pas devenir maître de classe dérivée
- [ ] Enseignant spécialisé ne peut pas modifier élèves d'autres classes  
- [ ] Parent voit toutes les données de ses enfants (multi-classes)
- [ ] Suppression collaboration supprime toutes données dérivées
- [ ] Notes TA affichées en violet dans interface parent
- [ ] Permissions respectées pour tous les types d'utilisateurs
- [ ] Pas d'erreurs JavaScript dans la console
- [ ] Pas d'erreurs SQL dans les logs serveur
- [ ] Interface responsive sur mobile
- [ ] Temps de réponse acceptable (<2s)

---

**Conclusion**: Le système semble robuste mais nécessite des tests approfondis notamment sur la sécurité des permissions et l'agrégation des données multi-classes. Les zones les plus à risque sont les interactions entre classes originales et dérivées.