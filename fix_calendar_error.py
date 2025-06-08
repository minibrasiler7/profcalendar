#!/usr/bin/env python
"""
Script pour localiser et corriger l'erreur dans calendar_view.html
"""

import os
import re

def fix_calendar_view():
    # Chemin du fichier
    file_path = 'templates/planning/calendar_view.html'

    if not os.path.exists(file_path):
        print(f"❌ Fichier non trouvé : {file_path}")
        return False

    # Lire le fichier
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Pattern à chercher
    old_pattern = r'(\s*){% if planning\.title %}\s*\n\s*<div class="planning-title">{{ planning\.title }}</div>\s*\n\s*{% endif %}'

    # Nouveau code
    new_code = '''                        {% if planning.title %}
                        <div class="planning-title">
                            {% if planning and planning.count_checklist_items is defined %}
                                {% set total = planning.count_checklist_items() %}
                                {% if total > 0 %}
                                    {% set checked = planning.count_checked_items() %}
                                    <span class="checklist-indicator" title="{{ checked }}/{{ total }} tâches complétées">
                                        {% if checked == total %}
                                            <i class="fas fa-check-circle" style="color: #10B981;"></i>
                                        {% elif checked > 0 %}
                                            <i class="fas fa-tasks" style="color: #F59E0B;"></i>
                                        {% else %}
                                            <i class="fas fa-times-circle" style="color: #EF4444;"></i>
                                        {% endif %}
                                    </span>
                                {% endif %}
                            {% endif %}
                            {{ planning.title }}
                        </div>
                        {% endif %}'''

    # Chercher et remplacer
    matches = list(re.finditer(old_pattern, content, re.MULTILINE))

    if not matches:
        print("⚠️  Pattern exact non trouvé. Recherche alternative...")

        # Recherche plus simple
        simple_pattern = r'<div class="planning-title">{{ planning\.title }}</div>'
        matches = list(re.finditer(simple_pattern, content))

        if matches:
            print(f"✓ Trouvé {len(matches)} occurrence(s) du pattern simple")

            # Afficher les lignes
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                if 'planning-title' in line and 'planning.title' in line:
                    print(f"  Ligne {i}: {line.strip()}")

            # Faire une sauvegarde
            backup_path = file_path + '.backup'
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"\n📦 Sauvegarde créée : {backup_path}")

            # Instructions manuelles
            print("\n📝 Instructions pour corriger manuellement :")
            print("1. Ouvrez le fichier : templates/planning/calendar_view.html")
            print(f"2. Allez à la ligne contenant : <div class=\"planning-title\">{{{{ planning.title }}}}</div>")
            print("3. Remplacez cette section par le code fourni dans 'Version ultra-sûre pour calendar_view.html'")

            return False
    else:
        print(f"✓ Pattern trouvé à {len(matches)} endroit(s)")

        # Remplacer
        new_content = re.sub(old_pattern, new_code, content, flags=re.MULTILINE)

        # Sauvegarder
        backup_path = file_path + '.backup'
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"📦 Sauvegarde créée : {backup_path}")

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"✅ Fichier corrigé : {file_path}")

        return True

if __name__ == "__main__":
    print("🔧 Correction de l'erreur calendar_view\n")

    if fix_calendar_view():
        print("\n✅ Correction appliquée avec succès !")
        print("\n🚀 Prochaines étapes :")
        print("1. Redémarrez l'application (Ctrl+C puis python run.py)")
        print("2. Testez le calendrier")
    else:
        print("\n⚠️  Correction manuelle nécessaire")
        print("\nSi vous préférez, vous pouvez aussi :")
        print("- Utiliser le code dans 'Fix simple et direct pour calendar_view.html'")
        print("- Ou temporairement désactiver les indicateurs en gardant juste {{ planning.title }}")
