#!/usr/bin/env python3
"""
Analyse statique du code ProfCalendar pour détecter les problèmes potentiels
"""

import os
import re
import ast

class CodeAnalyzer:
    def __init__(self, project_path="."):
        self.project_path = project_path
        self.issues = []
        
    def log_issue(self, severity, file_path, line_num, issue_type, description):
        """Enregistrer un problème détecté"""
        self.issues.append({
            "severity": severity,  # "CRITICAL", "HIGH", "MEDIUM", "LOW"
            "file": file_path,
            "line": line_num,
            "type": issue_type,
            "description": description
        })
    
    def analyze_sql_injection_risks(self):
        """Analyser les risques d'injection SQL"""
        print("🔍 Analyse des risques d'injection SQL...")
        
        patterns = [
            r'\.query\([^)]*%.*\)',  # .query("SELECT * FROM table WHERE id = %s" % user_input)
            r'\.execute\([^)]*%.*\)',  # .execute("SELECT * FROM table WHERE id = %s" % user_input)
            r'f".*SELECT.*{.*}"',  # f"SELECT * FROM table WHERE id = {user_input}"
            r'".*SELECT.*"\s*\+',  # "SELECT * FROM table WHERE id = " + user_input
        ]
        
        for root, dirs, files in os.walk(self.project_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                            for i, line in enumerate(lines, 1):
                                for pattern in patterns:
                                    if re.search(pattern, line):
                                        self.log_issue("HIGH", file_path, i, "SQL_INJECTION", 
                                                     f"Possible injection SQL: {line.strip()}")
                    except Exception as e:
                        continue
    
    def analyze_permission_checks(self):
        """Analyser les vérifications de permissions"""
        print("🔐 Analyse des vérifications de permissions...")
        
        # Chercher les routes sans @login_required ou @teacher_required
        for root, dirs, files in os.walk(self.project_path):
            for file in files:
                if file.endswith('.py') and 'routes' in file:
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            lines = content.split('\n')
                            
                            for i, line in enumerate(lines):
                                if '@' in line and '.route(' in line:
                                    # Route trouvée, vérifier si elle a une protection
                                    route_line = i
                                    protected = False
                                    
                                    # Chercher les décorateurs de protection dans les 5 lignes précédentes
                                    for j in range(max(0, i-5), i):
                                        if any(dec in lines[j] for dec in ['@login_required', '@teacher_required', '@parent_required']):
                                            protected = True
                                            break
                                    
                                    if not protected and 'POST' in line:
                                        self.log_issue("CRITICAL", file_path, i+1, "UNPROTECTED_ROUTE",
                                                     f"Route POST non protégée: {line.strip()}")
                                    elif not protected and any(sensitive in line for sensitive in ['delete', 'edit', 'admin']):
                                        self.log_issue("HIGH", file_path, i+1, "UNPROTECTED_ROUTE",
                                                     f"Route sensible non protégée: {line.strip()}")
                    except Exception as e:
                        continue
    
    def analyze_database_operations(self):
        """Analyser les opérations de base de données dangereuses"""
        print("🗄️ Analyse des opérations de base de données...")
        
        dangerous_patterns = [
            (r'\.delete\(\)', "MEDIUM", "DELETE_WITHOUT_FILTER", "Suppression sans filtre explicite"),
            (r'db\.session\.commit\(\).*except', "LOW", "COMMIT_IN_EXCEPTION", "Commit dans un bloc d'exception"),
            (r'Student\.query\.get\([^)]*request\.[^)]*\)', "HIGH", "UNSAFE_ID_ACCESS", "Accès ID depuis request non validé"),
            (r'\.filter_by\([^)]*request\.[^)]*\)', "MEDIUM", "UNSAFE_FILTER", "Filtre avec données request non validées"),
        ]
        
        for root, dirs, files in os.walk(self.project_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                            for i, line in enumerate(lines, 1):
                                for pattern, severity, issue_type, description in dangerous_patterns:
                                    if re.search(pattern, line):
                                        self.log_issue(severity, file_path, i, issue_type,
                                                     f"{description}: {line.strip()}")
                    except Exception as e:
                        continue
    
    def analyze_collaboration_logic(self):
        """Analyser spécifiquement la logique de collaboration"""
        print("🤝 Analyse de la logique de collaboration...")
        
        collaboration_file = os.path.join(self.project_path, "routes", "collaboration.py")
        if os.path.exists(collaboration_file):
            with open(collaboration_file, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                
                # Vérifier la protection de become_master
                become_master_found = False
                for i, line in enumerate(lines):
                    if 'def become_master' in line:
                        become_master_found = True
                        # Vérifier les protections dans les 20 lignes suivantes
                        checks = []
                        for j in range(i, min(i+20, len(lines))):
                            if 'existing_master' in lines[j]:
                                checks.append("existing_master")
                            if 'is_derived_class' in lines[j]:
                                checks.append("is_derived_class") 
                            if 'is_specialized_teacher' in lines[j]:
                                checks.append("is_specialized_teacher")
                        
                        if len(checks) < 3:
                            self.log_issue("CRITICAL", collaboration_file, i+1, "INCOMPLETE_PROTECTION",
                                         f"become_master manque des vérifications: {checks}")
                        break
                
                if not become_master_found:
                    self.log_issue("HIGH", collaboration_file, 0, "MISSING_FUNCTION", "Fonction become_master non trouvée")
    
    def analyze_parent_data_aggregation(self):
        """Analyser l'agrégation des données parent"""
        print("👨‍👩‍👧‍👦 Analyse de l'agrégation des données parent...")
        
        parent_file = os.path.join(self.project_path, "routes", "parent_auth.py")
        if os.path.exists(parent_file):
            with open(parent_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Vérifier la fonction get_all_linked_students
                if 'def get_all_linked_students' not in content:
                    self.log_issue("CRITICAL", parent_file, 0, "MISSING_FUNCTION",
                                 "Fonction get_all_linked_students manquante")
                
                # Vérifier les routes parent
                critical_routes = ['get_student_grades', 'get_student_attendance', 'get_student_sanctions']
                for route in critical_routes:
                    if f'def {route}' not in content:
                        self.log_issue("HIGH", parent_file, 0, "MISSING_ROUTE", f"Route {route} manquante")
                    elif 'get_all_linked_students' not in content:
                        self.log_issue("CRITICAL", parent_file, 0, "NO_AGGREGATION",
                                     f"Route {route} n'utilise pas l'agrégation multi-classes")
    
    def analyze_template_security(self):
        """Analyser la sécurité des templates"""
        print("📄 Analyse de la sécurité des templates...")
        
        template_path = os.path.join(self.project_path, "templates")
        if os.path.exists(template_path):
            for root, dirs, files in os.walk(template_path):
                for file in files:
                    if file.endswith('.html'):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                
                                # Vérifier les variables non échappées
                                if '{{' in content and '|safe' in content:
                                    self.log_issue("MEDIUM", file_path, 0, "UNSAFE_TEMPLATE",
                                                 "Variables marquées comme 'safe' détectées")
                                
                                # Vérifier les formulaires sans CSRF
                                if '<form' in content and 'csrf_token' not in content:
                                    self.log_issue("HIGH", file_path, 0, "NO_CSRF",
                                                 "Formulaire sans protection CSRF")
                        except Exception as e:
                            continue
    
    def generate_report(self):
        """Générer le rapport d'analyse"""
        print("\n" + "="*60)
        print("📊 RAPPORT D'ANALYSE STATIQUE")
        print("="*60)
        
        # Compter par sévérité
        severity_counts = {}
        for issue in self.issues:
            severity = issue['severity']
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        print(f"\n📈 RÉSUMÉ:")
        print(f"🔴 CRITICAL: {severity_counts.get('CRITICAL', 0)}")
        print(f"🟠 HIGH: {severity_counts.get('HIGH', 0)}")
        print(f"🟡 MEDIUM: {severity_counts.get('MEDIUM', 0)}")
        print(f"🟢 LOW: {severity_counts.get('LOW', 0)}")
        print(f"📊 TOTAL: {len(self.issues)}")
        
        # Grouper par type
        type_counts = {}
        for issue in self.issues:
            issue_type = issue['type']
            type_counts[issue_type] = type_counts.get(issue_type, 0) + 1
        
        print(f"\n🏷️ TYPES DE PROBLÈMES:")
        for issue_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"• {issue_type}: {count}")
        
        # Afficher les problèmes critiques
        critical_issues = [i for i in self.issues if i['severity'] == 'CRITICAL']
        if critical_issues:
            print(f"\n🚨 PROBLÈMES CRITIQUES ({len(critical_issues)}):")
            for issue in critical_issues:
                print(f"• {issue['file']}:{issue['line']} - {issue['description']}")
        
        # Afficher les problèmes haute priorité
        high_issues = [i for i in self.issues if i['severity'] == 'HIGH']
        if high_issues:
            print(f"\n⚠️ PROBLÈMES HAUTE PRIORITÉ ({len(high_issues)}):")
            for issue in high_issues[:5]:  # Limiter à 5 pour la lisibilité
                print(f"• {issue['file']}:{issue['line']} - {issue['description']}")
            if len(high_issues) > 5:
                print(f"... et {len(high_issues) - 5} autres")
        
        return self.issues
    
    def run_analysis(self):
        """Exécuter toutes les analyses"""
        print("🔍 DÉBUT DE L'ANALYSE STATIQUE")
        print("="*40)
        
        self.analyze_sql_injection_risks()
        self.analyze_permission_checks()
        self.analyze_database_operations()
        self.analyze_collaboration_logic()
        self.analyze_parent_data_aggregation()
        self.analyze_template_security()
        
        return self.generate_report()

if __name__ == "__main__":
    analyzer = CodeAnalyzer()
    issues = analyzer.run_analysis()
    
    print(f"\n💡 RECOMMANDATIONS:")
    print("1. Corriger d'abord tous les problèmes CRITICAL")
    print("2. Réviser les problèmes HIGH priorité")
    print("3. Tester manuellement les fonctionnalités critiques")
    print("4. Ajouter des tests unitaires pour les fonctions sensibles")
    print("5. Effectuer un audit de sécurité complet")