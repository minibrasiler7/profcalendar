import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from datetime import datetime

class FileCombiner:
    def __init__(self, root):
        self.root = root
        self.root.title("Compilateur de fichiers Python")
        self.root.geometry("900x700")  # Fenêtre plus grande

        # Variables
        self.project_path = os.getcwd()
        self.file_vars = {}
        self.python_files = []

        self.setup_ui()
        self.scan_project()

    def setup_ui(self):
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configuration du redimensionnement
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)

        # Titre et chemin du projet
        title_label = ttk.Label(main_frame, text="Sélectionnez les fichiers à combiner",
                               font=("Arial", 12, "bold"))
        title_label.grid(row=0, column=0, pady=(0, 5), sticky=tk.W)

        path_label = ttk.Label(main_frame, text=f"Projet: {self.project_path}",
                              foreground="gray")
        path_label.grid(row=0, column=0, pady=(20, 10), sticky=tk.W)

        # Frame avec scrollbar pour la liste des fichiers
        list_frame = ttk.Frame(main_frame)
        list_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        # Canvas et scrollbar
        canvas = tk.Canvas(list_frame, bg="white", height=400)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        # Configurer le scrolling avec la molette
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        def _bind_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")

        canvas.bind('<Enter>', _bind_mousewheel)
        canvas.bind('<Leave>', _unbind_mousewheel)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas_window = canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Ajuster la largeur du frame interne à celle du canvas
        def configure_scroll_region(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(canvas_window, width=canvas.winfo_width())

        canvas.bind('<Configure>', configure_scroll_region)

        canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # Frame pour les boutons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, pady=(10, 0), sticky=(tk.W, tk.E))

        # Boutons de sélection
        select_all_btn = ttk.Button(button_frame, text="Sélectionner tout",
                                   command=self.select_all)
        select_all_btn.grid(row=0, column=0, padx=(0, 5))

        deselect_all_btn = ttk.Button(button_frame, text="Désélectionner tout",
                                     command=self.deselect_all)
        deselect_all_btn.grid(row=0, column=1, padx=5)

        # Bouton de validation
        validate_btn = ttk.Button(button_frame, text="Générer le fichier combiné",
                                 command=self.combine_files, style="Accent.TButton")
        validate_btn.grid(row=0, column=2, padx=(20, 0))

        # Configuration du style pour le bouton principal
        style = ttk.Style()
        style.configure("Accent.TButton", font=("Arial", 10, "bold"))

    def scan_project(self):
        """Scanne le projet pour trouver tous les fichiers Python"""
        self.python_files = []

        # Extensions de fichiers à inclure
        extensions = {
            '.py', '.pyw',           # Python
            '.js', '.jsx', '.ts', '.tsx',  # JavaScript/TypeScript
            '.html', '.htm',         # HTML
            '.css', '.scss', '.sass', '.less',  # CSS et préprocesseurs
            '.txt', '.md',           # Documentation
            '.yml', '.yaml',         # Configuration YAML
            '.json',                 # JSON
            '.cfg', '.ini',          # Configuration
            '.xml',                  # XML
            '.php',                  # PHP
            '.java',                 # Java
            '.c', '.cpp', '.h',      # C/C++
            '.cs',                   # C#
            '.rb',                   # Ruby
            '.go',                   # Go
            '.rs',                   # Rust
            '.swift',                # Swift
            '.kt',                   # Kotlin
            '.sql',                  # SQL
            '.sh', '.bash',          # Scripts shell
            '.bat', '.cmd',          # Scripts Windows
            '.dockerfile',           # Docker
            '.vue',                  # Vue.js
            '.svelte',               # Svelte
            '.astro'                 # Astro
        }

        # Dossiers à ignorer
        ignore_dirs = {'__pycache__', '.git', '.venv', 'venv', 'env', 'node_modules', '.pytest_cache'}

        for root, dirs, files in os.walk(self.project_path):
            # Filtrer les dossiers à ignorer
            dirs[:] = [d for d in dirs if d not in ignore_dirs]

            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, self.project_path)
                    self.python_files.append((rel_path, file_path))

        # Trier par chemin relatif
        self.python_files.sort(key=lambda x: x[0])

        self.create_file_checkboxes()

    def create_file_checkboxes(self):
        """Crée les cases à cocher pour chaque fichier"""
        # Nettoyer le frame précédent
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        self.file_vars = {}

        if not self.python_files:
            no_files_label = ttk.Label(self.scrollable_frame,
                                      text="Aucun fichier trouvé dans le projet",
                                      foreground="red")
            no_files_label.grid(row=0, column=0, pady=20)
            return

        for i, (rel_path, full_path) in enumerate(self.python_files):
            var = tk.BooleanVar()
            self.file_vars[rel_path] = var

            # Créer un frame pour chaque ligne pour un meilleur contrôle
            file_frame = ttk.Frame(self.scrollable_frame)
            file_frame.grid(row=i, column=0, sticky=(tk.W, tk.E), pady=1, padx=5)
            file_frame.columnconfigure(0, weight=1)

            checkbox = ttk.Checkbutton(file_frame, text=rel_path, variable=var)
            checkbox.grid(row=0, column=0, sticky=tk.W)

        # Forcer la mise à jour de la région de scroll
        self.scrollable_frame.update_idletasks()

    def select_all(self):
        """Sélectionne tous les fichiers"""
        for var in self.file_vars.values():
            var.set(True)

    def deselect_all(self):
        """Désélectionne tous les fichiers"""
        for var in self.file_vars.values():
            var.set(False)

    def combine_files(self):
        """Combine les fichiers sélectionnés en un seul fichier texte"""
        selected_files = [rel_path for rel_path, var in self.file_vars.items() if var.get()]

        if not selected_files:
            messagebox.showwarning("Aucune sélection", "Veuillez sélectionner au moins un fichier.")
            return

        # Demander où sauvegarder le fichier
        output_file = filedialog.asksaveasfilename(
            title="Enregistrer le fichier combiné",
            defaultextension=".txt",
            filetypes=[("Fichiers texte", "*.txt"), ("Tous les fichiers", "*.*")],
            initialfile=f"combined_files_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )

        if not output_file:
            return

        try:
            with open(output_file, 'w', encoding='utf-8') as outfile:
                # En-tête du fichier
                outfile.write(f"=== FICHIERS COMBINÉS ===\n")
                outfile.write(f"Généré le: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                outfile.write(f"Projet: {self.project_path}\n")
                outfile.write(f"Nombre de fichiers: {len(selected_files)}\n")
                outfile.write("="*50 + "\n\n")

                for rel_path in selected_files:
                    full_path = None
                    for rp, fp in self.python_files:
                        if rp == rel_path:
                            full_path = fp
                            break

                    if full_path and os.path.exists(full_path):
                        # En-tête du fichier
                        outfile.write(f"\n{'='*80}\n")
                        outfile.write(f"FICHIER: {rel_path}\n")
                        outfile.write(f"CHEMIN: {full_path}\n")
                        outfile.write(f"{'='*80}\n\n")

                        try:
                            with open(full_path, 'r', encoding='utf-8') as infile:
                                content = infile.read()
                                outfile.write(content)
                        except UnicodeDecodeError:
                            # Essayer avec d'autres encodages
                            try:
                                with open(full_path, 'r', encoding='latin-1') as infile:
                                    content = infile.read()
                                    outfile.write(content)
                            except Exception as e:
                                outfile.write(f"[ERREUR: Impossible de lire le fichier - {str(e)}]\n")
                        except Exception as e:
                            outfile.write(f"[ERREUR: {str(e)}]\n")

                        outfile.write(f"\n\n{'='*80}\n")
                        outfile.write(f"FIN DE: {rel_path}\n")
                        outfile.write(f"{'='*80}\n\n")

            messagebox.showinfo("Succès",
                              f"Fichier combiné créé avec succès!\n\n"
                              f"Fichiers combinés: {len(selected_files)}\n"
                              f"Sauvegardé dans: {output_file}")

        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la création du fichier:\n{str(e)}")

def main():
    root = tk.Tk()
    app = FileCombiner(root)
    root.mainloop()

if __name__ == "__main__":
    main()
