import os
from pathlib import Path

def consolidate_project(project_path=".", output_file="projet_consolide.txt", extensions=None):
    """
    Consolide tous les fichiers de code d'un projet en un seul fichier.

    Args:
        project_path (str): Chemin vers le projet (par défaut: dossier actuel)
        output_file (str): Nom du fichier de sortie
        extensions (list): Extensions à inclure (par défaut: py, html, css, js)
    """

    if extensions is None:
        extensions = ['.py', '.html', '.css', '.js', '.jsx', '.ts', '.tsx', '.vue']

    # Dossiers à ignorer
    ignore_dirs = {
        '__pycache__', '.git', 'node_modules', 'venv', '.venv', 'env', '.env',
        'dist', 'build', '.idea', '.vscode', 'htmlcov', '.pytest_cache',
        '.mypy_cache', 'logs', 'tmp', 'temp'
    }

    project_path = Path(project_path).resolve()

    with open(output_file, 'w', encoding='utf-8') as output:
        # En-tête du fichier
        output.write("=" * 80 + "\n")
        output.write(f"CONSOLIDATION DU PROJET: {project_path.name}\n")
        output.write(f"Généré depuis: {project_path}\n")
        output.write(f"Extensions incluses: {', '.join(extensions)}\n")
        output.write("=" * 80 + "\n\n")

        # Compteurs
        total_files = 0
        total_lines = 0

        # Parcourir tous les fichiers
        for root, dirs, files in os.walk(project_path):
            # Filtrer les dossiers à ignorer
            dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith('.')]

            root_path = Path(root)

            for file in sorted(files):
                file_path = root_path / file

                # Vérifier l'extension
                if file_path.suffix.lower() in extensions:
                    try:
                        # Calculer le chemin relatif
                        relative_path = file_path.relative_to(project_path)

                        # En-tête du fichier
                        output.write("\n" + "=" * 80 + "\n")
                        output.write(f"FICHIER: {file}\n")
                        output.write(f"LOCALISATION: {relative_path}\n")
                        output.write(f"CHEMIN COMPLET: {file_path}\n")
                        output.write("=" * 80 + "\n\n")

                        # Lire et écrire le contenu
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            output.write(content)

                            # Compter les lignes
                            lines_count = len(content.splitlines())
                            total_lines += lines_count

                        output.write("\n\n")
                        total_files += 1

                        print(f"✓ Ajouté: {relative_path} ({lines_count} lignes)")

                    except Exception as e:
                        print(f"✗ Erreur avec {file_path}: {e}")
                        output.write(f"[ERREUR DE LECTURE: {e}]\n\n")

        # Résumé final
        output.write("\n" + "=" * 80 + "\n")
        output.write("RÉSUMÉ DE LA CONSOLIDATION\n")
        output.write("=" * 80 + "\n")
        output.write(f"Fichiers traités: {total_files}\n")
        output.write(f"Lignes totales: {total_lines}\n")
        output.write(f"Extensions incluses: {', '.join(extensions)}\n")
        output.write("=" * 80 + "\n")

    print(f"\n🎉 Consolidation terminée !")
    print(f"📁 Fichiers traités: {total_files}")
    print(f"📝 Lignes totales: {total_lines}")
    print(f"💾 Fichier de sortie: {output_file}")

def main():
    """Fonction principale avec options personnalisables"""

    # Configuration personnalisable
    projet_path = "."  # Changez pour le chemin de votre projet
    fichier_sortie = "projet_consolide.txt"

    # Extensions à inclure (ajoutez/supprimez selon vos besoins)
    extensions_incluses = [
        '.py',      # Python
        '.html',    # HTML
        '.css',     # CSS
        '.js',      # JavaScript
        '.jsx',     # React JSX
        '.ts',      # TypeScript
        '.tsx',     # TypeScript React
        '.vue',     # Vue.js
        '.php',     # PHP
        '.java',    # Java
        '.cpp',     # C++
        '.c',       # C
        '.h',       # Headers C/C++
        '.json',    # JSON
        '.xml',     # XML
        '.sql',     # SQL
        '.md',      # Markdown
        '.txt',     # Texte
        '.yml',     # YAML
        '.yaml'     # YAML
    ]

    print("🚀 Démarrage de la consolidation du projet...")
    print(f"📂 Dossier source: {os.path.abspath(projet_path)}")
    print(f"📄 Fichier de sortie: {fichier_sortie}")

    consolidate_project(
        project_path=projet_path,
        output_file=fichier_sortie,
        extensions=extensions_incluses
    )

if __name__ == "__main__":
    main()
