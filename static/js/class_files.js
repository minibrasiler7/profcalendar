/**
 * Nouveau système de gestion des fichiers de classe
 * Plus simple, plus robuste, moins de bugs
 */

class ClassFileManager {
    constructor() {
        this.classes = [];
        this.openTrees = new Set(); // Classes dont l'arborescence est ouverte
        this.openFolders = new Set(); // Dossiers ouverts dans les arborescences
        this.selectedFile = null;
        
        this.initLocalStorage();
        this.loadClasses();
    }
    
    initLocalStorage() {
        // Restaurer l'état depuis localStorage
        try {
            const savedTrees = localStorage.getItem('classFileManager_openTrees');
            if (savedTrees) {
                this.openTrees = new Set(JSON.parse(savedTrees));
            }
            
            const savedFolders = localStorage.getItem('classFileManager_openFolders');
            if (savedFolders) {
                this.openFolders = new Set(JSON.parse(savedFolders));
            }
        } catch (e) {
            console.warn('Erreur lors du chargement de l\'état:', e);
        }
    }
    
    saveState() {
        // Sauvegarder l'état dans localStorage
        try {
            localStorage.setItem('classFileManager_openTrees', JSON.stringify([...this.openTrees]));
            localStorage.setItem('classFileManager_openFolders', JSON.stringify([...this.openFolders]));
        } catch (e) {
            console.warn('Erreur lors de la sauvegarde de l\'état:', e);
        }
    }
    
    async loadClasses() {
        try {
            const response = await fetch('/files/get-classes');
            const result = await response.json();
            
            if (result.success) {
                this.classes = result.classes;
                this.renderClasses();
                await this.restoreOpenTrees();
            }
        } catch (error) {
            console.error('Erreur lors du chargement des classes:', error);
            this.showNotification('error', 'Erreur lors du chargement des classes');
        }
    }
    
    renderClasses() {
        const container = document.getElementById('classesList');
        if (!container) return;
        
        if (this.classes.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted">
                    <i class="fas fa-chalkboard" style="font-size: 2rem; margin-bottom: 0.5rem; opacity: 0.3;"></i>
                    <p>Aucune classe trouvée</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = this.classes.map(classroom => `
            <div class="class-item" data-class-id="${classroom.id}">
                <div class="class-header" onclick="classFileManager.toggleClassTree(${classroom.id})">
                    <div>
                        <div class="class-name">${classroom.name}</div>
                        <div class="class-info">${classroom.student_count || 0} élève(s)</div>
                    </div>
                    <i class="fas fa-chevron-right class-toggle" id="toggle-${classroom.id}"></i>
                </div>
                <div class="class-tree" id="classTree-${classroom.id}" style="display: none;">
                    <!-- L'arborescence sera chargée ici -->
                </div>
            </div>
        `).join('');
        
        // Initialiser le drag & drop
        this.initDragAndDrop();
    }
    
    async toggleClassTree(classId) {
        const tree = document.getElementById(`classTree-${classId}`);
        const toggle = document.getElementById(`toggle-${classId}`);
        
        if (!tree || !toggle) return;
        
        if (tree.style.display === 'none') {
            // Ouvrir l'arborescence
            this.openTrees.add(classId);
            tree.style.display = 'block';
            toggle.classList.add('expanded');
            
            // Charger les fichiers si pas encore fait
            if (tree.innerHTML.trim() === '') {
                await this.loadClassFiles(classId);
            }
        } else {
            // Fermer l'arborescence
            this.openTrees.delete(classId);
            tree.style.display = 'none';
            toggle.classList.remove('expanded');
        }
        
        this.saveState();
    }
    
    async restoreOpenTrees() {
        for (const classId of this.openTrees) {
            const tree = document.getElementById(`classTree-${classId}`);
            const toggle = document.getElementById(`toggle-${classId}`);
            
            if (tree && toggle) {
                tree.style.display = 'block';
                toggle.classList.add('expanded');
                await this.loadClassFiles(classId);
            }
        }
    }
    
    async loadClassFiles(classId) {
        try {
            const response = await fetch(`/api/class-files/list/${classId}`);
            const result = await response.json();
            
            if (result.success) {
                this.renderClassFiles(classId, result.files);
            } else {
                console.error('Erreur:', result.message);
            }
        } catch (error) {
            console.error('Erreur lors du chargement des fichiers:', error);
        }
    }
    
    renderClassFiles(classId, files) {
        const tree = document.getElementById(`classTree-${classId}`);
        if (!tree) return;
        
        if (files.length === 0) {
            tree.innerHTML = `
                <div class="tree-empty">
                    <i class="fas fa-info-circle"></i>
                    <span>Aucun fichier dans cette classe</span>
                </div>
            `;
            return;
        }
        
        // Organiser les fichiers par structure
        const structure = this.buildFileStructure(files);
        tree.innerHTML = this.renderFileStructure(structure, classId);
        
        // Restaurer l'état des dossiers ouverts
        this.restoreOpenFolders();
    }
    
    buildFileStructure(files) {
        const structure = {
            folders: {},
            files: []
        };
        
        files.forEach(file => {
            if (file.folder_path) {
                // Fichier dans un dossier
                const pathParts = file.folder_path.split('/').filter(part => part.trim() !== '');
                let currentLevel = structure;
                
                pathParts.forEach((folderName, index) => {
                    if (!currentLevel.folders[folderName]) {
                        currentLevel.folders[folderName] = {
                            folders: {},
                            files: [],
                            fullPath: pathParts.slice(0, index + 1).join('/')
                        };
                    }
                    currentLevel = currentLevel.folders[folderName];
                });
                
                currentLevel.files.push(file);
            } else {
                // Fichier à la racine
                structure.files.push(file);
            }
        });
        
        return structure;
    }
    
    renderFileStructure(structure, classId, level = 0) {
        let html = '';
        const indent = level * 1.5;
        
        // Afficher les dossiers
        Object.keys(structure.folders).sort().forEach(folderName => {
            const folder = structure.folders[folderName];
            const folderId = `folder-${classId}-${folder.fullPath.replace(/[^a-zA-Z0-9]/g, '-')}`;
            const hasContent = Object.keys(folder.folders).length > 0 || folder.files.length > 0;
            
            html += `
                <div class="tree-folder" style="padding-left: ${indent}rem;">
                    <div class="tree-folder-header" onclick="window.classFileManager.toggleFolder('${folderId}')">
                        ${hasContent ? `<i class="fas fa-chevron-right tree-folder-toggle" id="toggle-${folderId}"></i>` : '<i class="fas fa-minus" style="opacity: 0.3; width: 12px;"></i>'}
                        <i class="fas fa-folder tree-item-icon"></i>
                        <span class="tree-item-name">${folderName}</span>
                        <span class="tree-item-count">(${folder.files.length})</span>
                    </div>
                    <div class="tree-folder-content" id="${folderId}" style="display: none;">
                        ${this.renderFileStructure(folder, classId, level + 1)}
                    </div>
                </div>
            `;
        });
        
        // Afficher les fichiers
        structure.files.sort((a, b) => a.original_filename.localeCompare(b.original_filename)).forEach(file => {
            const icon = this.getFileIcon(file.file_type);
            html += `
                <div class="tree-file" style="padding-left: ${indent}rem;" data-file-id="${file.id}" data-class-id="${classId}">
                    <i class="${icon} tree-item-icon"></i>
                    <span class="tree-item-name">${file.original_filename}</span>
                    <span class="tree-item-size">${this.formatSize(file.file_size)}</span>
                    <button class="tree-file-delete" onclick="window.classFileManager.deleteFile(${file.id}, ${classId})" title="Retirer de la classe">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            `;
        });
        
        return html;
    }
    
    toggleFolder(folderId) {
        const content = document.getElementById(folderId);
        const toggle = document.getElementById(`toggle-${folderId}`);
        
        if (content && toggle) {
            if (content.style.display === 'none') {
                content.style.display = 'block';
                toggle.classList.remove('fa-chevron-right');
                toggle.classList.add('fa-chevron-down');
                this.openFolders.add(folderId);
            } else {
                content.style.display = 'none';
                toggle.classList.remove('fa-chevron-down');
                toggle.classList.add('fa-chevron-right');
                this.openFolders.delete(folderId);
            }
            
            this.saveState();
        }
    }
    
    restoreOpenFolders() {
        for (const folderId of this.openFolders) {
            const content = document.getElementById(folderId);
            const toggle = document.getElementById(`toggle-${folderId}`);
            
            if (content && toggle) {
                content.style.display = 'block';
                toggle.classList.remove('fa-chevron-right');
                toggle.classList.add('fa-chevron-down');
            }
        }
    }
    
    async copyFileToClass(fileId, classId, folderPath = '') {
        try {
            const response = await fetch('/api/class-files/copy-file', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    file_id: fileId,
                    class_id: classId,
                    folder_path: folderPath
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showNotification('success', result.message);
                
                // Ouvrir et recharger l'arborescence
                this.openTrees.add(classId);
                await this.loadClassFiles(classId);
                
                const tree = document.getElementById(`classTree-${classId}`);
                const toggle = document.getElementById(`toggle-${classId}`);
                
                if (tree && toggle) {
                    tree.style.display = 'block';
                    toggle.classList.add('expanded');
                }
                
                this.saveState();
            } else {
                this.showNotification('error', result.message);
            }
        } catch (error) {
            console.error('Erreur:', error);
            this.showNotification('error', 'Erreur lors de la copie du fichier');
        }
    }
    
    async copyFolderToClass(folderId, classId, folderPath = '') {
        try {
            const response = await fetch('/api/class-files/copy-folder', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    folder_id: folderId,
                    class_id: classId,
                    folder_path: folderPath
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showNotification('success', result.message);
                
                // Ouvrir et recharger l'arborescence
                this.openTrees.add(classId);
                await this.loadClassFiles(classId);
                
                const tree = document.getElementById(`classTree-${classId}`);
                const toggle = document.getElementById(`toggle-${classId}`);
                
                if (tree && toggle) {
                    tree.style.display = 'block';
                    toggle.classList.add('expanded');
                }
                
                this.saveState();
            } else {
                this.showNotification('error', result.message);
            }
        } catch (error) {
            console.error('Erreur:', error);
            this.showNotification('error', 'Erreur lors de la copie du dossier');
        }
    }
    
    async deleteFile(fileId, classId) {
        if (!confirm('Êtes-vous sûr de vouloir retirer ce fichier de la classe ?')) return;
        
        try {
            const response = await fetch(`/api/class-files/delete/${fileId}`, {
                method: 'DELETE'
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showNotification('success', result.message);
                await this.loadClassFiles(classId);
            } else {
                this.showNotification('error', result.message);
            }
        } catch (error) {
            console.error('Erreur:', error);
            this.showNotification('error', 'Erreur lors de la suppression');
        }
    }
    
    initDragAndDrop() {
        // Gérer le drag & drop sur les en-têtes de classe
        document.querySelectorAll('.class-header').forEach(header => {
            header.addEventListener('dragover', this.handleDragOver.bind(this));
            header.addEventListener('dragleave', this.handleDragLeave.bind(this));
            header.addEventListener('drop', this.handleDrop.bind(this));
        });
    }
    
    handleDragOver(e) {
        e.preventDefault();
        e.currentTarget.classList.add('drag-over');
    }
    
    handleDragLeave(e) {
        e.currentTarget.classList.remove('drag-over');
    }
    
    async handleDrop(e) {
        e.preventDefault();
        const header = e.currentTarget;
        header.classList.remove('drag-over');
        
        const dragData = e.dataTransfer.getData('text/plain');
        const classId = parseInt(header.closest('.class-item').dataset.classId);
        
        if (dragData && classId) {
            if (dragData.startsWith('file:')) {
                const fileId = parseInt(dragData.replace('file:', ''));
                await this.copyFileToClass(fileId, classId);
            } else if (dragData.startsWith('folder:')) {
                const folderId = parseInt(dragData.replace('folder:', ''));
                await this.copyFolderToClass(folderId, classId);
            }
        }
    }
    
    getFileIcon(fileType) {
        switch (fileType) {
            case 'pdf': return 'fas fa-file-pdf';
            case 'png':
            case 'jpg':
            case 'jpeg': return 'fas fa-file-image';
            default: return 'fas fa-file';
        }
    }
    
    formatSize(size) {
        if (!size) return '0 B';
        
        const units = ['B', 'KB', 'MB', 'GB'];
        let unitIndex = 0;
        let fileSize = parseFloat(size);
        
        while (fileSize >= 1024 && unitIndex < units.length - 1) {
            fileSize /= 1024;
            unitIndex++;
        }
        
        return `${fileSize.toFixed(1)} ${units[unitIndex]}`;
    }
    
    showNotification(type, message) {
        // Utiliser la fonction existante ou créer une simple
        if (typeof showNotification === 'function') {
            showNotification(type, message);
        } else {
            // Fallback simple
            console.log(`${type.toUpperCase()}: ${message}`);
            alert(message);
        }
    }
}

// Initialiser le gestionnaire
let classFileManager;

document.addEventListener('DOMContentLoaded', function() {
    classFileManager = new ClassFileManager();
    
    // Exposer globalement pour l'intégration avec l'ancien système
    window.classFileManager = classFileManager;
});

// Fonctions globales pour compatibilité
function toggleClassTree(classId) {
    if (classFileManager) {
        classFileManager.toggleClassTree(classId);
    }
}

// Fonction pour remplacer l'ancienne fonction loadClassTree
async function loadClassTree(classId) {
    if (window.classFileManager) {
        await window.classFileManager.loadClassFiles(classId);
    }
}