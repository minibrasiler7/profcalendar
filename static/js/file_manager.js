// Variables globales
let selectedItems = [];
let uploadQueue = [];
let isUploading = false;
let isDeleteMode = false;
let classes = [];
let selectedClassFile = null;

// Debug: ajouter un listener global pour voir si selectedClassFile change
window.setInterval(() => {
    if (selectedClassFile) {
        console.log('🔍 selectedClassFile global:', selectedClassFile);
    }
}, 5000); // Log toutes les 5 secondes si quelque chose est sélectionné

// Clés pour le localStorage
const TREE_STATE_KEY = 'fileManager_classTreeStates';
const FOLDER_STATE_KEY = 'fileManager_classFolderStates';

// Initialisation
document.addEventListener('DOMContentLoaded', function() {
    console.log('🔍 DOM chargé, initialisation en cours...');
    initDragAndDrop();
    initContextMenu();
    initKeyboardShortcuts();
    initDoubleClickHandler();
    initFileDragAndDrop();
    loadClasses();
    console.log('🔍 Initialisation terminée');
});

// Sauvegarder l'état des arborescences
function saveTreeStates() {
    const states = {};
    classes.forEach(classroom => {
        const tree = document.getElementById(`classTree-${classroom.id}`);
        if (tree) {
            states[classroom.id] = tree.style.display !== 'none';
        }
    });
    localStorage.setItem(TREE_STATE_KEY, JSON.stringify(states));
}

// Récupérer l'état des arborescences
function getTreeStates() {
    try {
        const states = localStorage.getItem(TREE_STATE_KEY);
        return states ? JSON.parse(states) : {};
    } catch (error) {
        console.error('Erreur lors de la lecture des états:', error);
        return {};
    }
}

// Charger les classes de l'utilisateur
async function loadClasses() {
    try {
        const response = await fetch('/file_manager/get-classes');
        const result = await response.json();

        if (result.success) {
            classes = result.classes;
            renderClasses();
            
            // Restaurer l'état des arborescences après le rendu
            await restoreTreeStates();
        }
    } catch (error) {
        console.error('Erreur lors du chargement des classes:', error);
    }
}

// Restaurer l'état des arborescences
async function restoreTreeStates() {
    const states = getTreeStates();
    
    for (const classId in states) {
        if (states[classId]) {
            // Cette classe était ouverte, la rouvrir
            const tree = document.getElementById(`classTree-${classId}`);
            const toggle = document.getElementById(`toggle-${classId}`);
            
            if (tree) {
                // Charger l'arborescence
                await loadClassTree(classId);
                
                // Afficher l'arborescence
                tree.style.display = 'block';
                if (toggle) {
                    toggle.classList.add('expanded');
                }
            }
        }
    }
}

// Afficher les classes
function renderClasses() {
    const classesList = document.getElementById('classesList');

    if (classes.length === 0) {
        classesList.innerHTML = `
            <div class="text-center text-muted">
                <i class="fas fa-chalkboard" style="font-size: 2rem; margin-bottom: 0.5rem; opacity: 0.3;"></i>
                <p>Aucune classe trouvée</p>
            </div>
        `;
        return;
    }

    classesList.innerHTML = classes.map(classroom => `
        <div class="class-item" data-class-id="${classroom.id}">
            <div class="class-header" onclick="toggleClassTree(${classroom.id})">
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

    // Ajouter les événements de drag & drop sur les en-têtes
    initClassDropZones();
}

// Initialiser le drag & drop vers les classes
function initClassDropZones() {
    const classHeaders = document.querySelectorAll('.class-header');

    classHeaders.forEach(classHeader => {
        classHeader.addEventListener('dragover', handleClassDragOver);
        classHeader.addEventListener('dragleave', handleClassDragLeave);
        classHeader.addEventListener('drop', handleClassDrop);
    });
}

// Basculer l'affichage de l'arborescence d'une classe
async function toggleClassTree(classId) {
    const tree = document.getElementById(`classTree-${classId}`);
    const toggle = document.getElementById(`toggle-${classId}`);

    if (tree.style.display === 'none') {
        // Charger l'arborescence si pas encore fait
        if (tree.innerHTML.trim() === '') {
            await loadClassTree(classId);
        }
        tree.style.display = 'block';
        toggle.classList.add('expanded');
    } else {
        tree.style.display = 'none';
        toggle.classList.remove('expanded');
    }
    
    // Sauvegarder l'état après chaque changement
    saveTreeStates();
}

// Charger l'arborescence des fichiers d'une classe
async function loadClassTree(classId) {
    try {
        const response = await fetch(`/file_manager/get-class-files/${classId}`);
        const result = await response.json();

        if (result.success) {
            renderClassTree(classId, result.files);
        } else {
            console.error('Erreur lors du chargement des fichiers:', result.message);
        }
    } catch (error) {
        console.error('Erreur:', error);
    }
}

// Afficher l'arborescence des fichiers d'une classe
function renderClassTree(classId, files) {
    const tree = document.getElementById(`classTree-${classId}`);

    if (files.length === 0) {
        tree.innerHTML = `
            <div class="tree-file" style="font-style: italic; color: #9CA3AF;">
                <i class="fas fa-info-circle"></i>
                <span>Aucun fichier dans cette classe</span>
            </div>
        `;
        return;
    }

    // Organiser les fichiers par structure hiérarchique
    const fileStructure = buildFileStructure(files);

    // Générer le HTML de l'arborescence
    const html = renderFileStructure(fileStructure, classId, 0);
    tree.innerHTML = html;

    // Ajouter les événements de drag & drop sur les dossiers
    initTreeFolderDropZones(classId);

    // Ajouter les événements de clic sur les dossiers
    initTreeFolderToggles(classId);
    
    // Ajouter les événements de clic sur les fichiers pour la sélection
    initClassFileSelection(classId);
    
    // Restaurer l'état des dossiers ouverts
    restoreFolderStates();
}

// Construire la structure hiérarchique des fichiers
function buildFileStructure(files) {
    const structure = {
        folders: {},
        files: []
    };

    files.forEach(file => {
        if (file.folder_name) {
            // Diviser le chemin du dossier
            const pathParts = file.folder_name.split('/').filter(part => part.trim() !== '');

            // Construire la structure récursivement
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

            // Ajouter le fichier au bon niveau
            currentLevel.files.push(file);
        } else {
            // Fichier à la racine
            structure.files.push(file);
        }
    });

    return structure;
}

// Générer le HTML de la structure de fichiers
function renderFileStructure(structure, classId, level = 0) {
    let html = '';
    const indent = 'padding-left: ' + (level * 1.5 + 1) + 'rem;';

    // Afficher les dossiers
    Object.keys(structure.folders).forEach(folderName => {
        const folder = structure.folders[folderName];
        const folderId = `folder-${classId}-${folder.fullPath.replace(/[^a-zA-Z0-9]/g, '-')}`;
        const hasContent = Object.keys(folder.folders).length > 0 || folder.files.length > 0;

        html += `
            <div class="tree-folder" style="${indent}"
                 data-folder-path="${folder.fullPath}"
                 data-class-id="${classId}">
                <div class="tree-folder-header" onclick="toggleTreeFolder('${folderId}')">
                    ${hasContent ? `<i class="fas fa-chevron-right tree-folder-toggle" id="toggle-${folderId}"></i>` : '<i class="fas fa-minus" style="opacity: 0.3;"></i>'}
                    <i class="fas fa-folder tree-item-icon"></i>
                    <span class="tree-item-name">${folderName}</span>
                </div>
                <div class="tree-folder-content" id="${folderId}" style="display: none;">
                    ${renderFileStructure(folder, classId, level + 1)}
                </div>
            </div>
        `;
    });

    // Afficher les fichiers (en excluant les marqueurs de dossiers vides)
    structure.files.forEach(file => {
        // Ne pas afficher les marqueurs de dossiers vides
        if (file.file_type === 'folder' && file.original_filename.startsWith('[Dossier vide:')) {
            return; // Ignorer ce fichier marqueur
        }
        
        const icon = getFileIcon(file.file_type);
        html += `
            <div class="tree-file" style="${indent}" data-file-id="${file.id}" data-class-id="${classId}">
                <i class="${icon} tree-item-icon"></i>
                <span class="tree-item-name">${file.original_filename}</span>
                <button class="tree-file-delete" onclick="deleteClassFile(${file.id}, ${classId})" title="Supprimer">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
    });

    return html;
}

// Sauvegarder l'état des dossiers ouverts
function saveFolderStates() {
    const states = {};
    document.querySelectorAll('.tree-folder-content').forEach(folder => {
        if (folder.id) {
            states[folder.id] = folder.style.display !== 'none';
        }
    });
    localStorage.setItem(FOLDER_STATE_KEY, JSON.stringify(states));
}

// Récupérer l'état des dossiers
function getFolderStates() {
    try {
        const states = localStorage.getItem(FOLDER_STATE_KEY);
        return states ? JSON.parse(states) : {};
    } catch (error) {
        console.error('Erreur lors de la lecture des états des dossiers:', error);
        return {};
    }
}

// Restaurer l'état des dossiers après le chargement de l'arborescence
function restoreFolderStates() {
    const states = getFolderStates();
    
    for (const folderId in states) {
        if (states[folderId]) {
            const content = document.getElementById(folderId);
            const toggle = document.getElementById(`toggle-${folderId}`);
            
            if (content && toggle) {
                content.style.display = 'block';
                toggle.classList.remove('fa-chevron-right');
                toggle.classList.add('fa-chevron-down');
            }
        }
    }
}

// Basculer l'affichage d'un dossier dans l'arborescence
function toggleTreeFolder(folderId) {
    const content = document.getElementById(folderId);
    const toggle = document.getElementById(`toggle-${folderId}`);

    if (content && toggle) {
        if (content.style.display === 'none') {
            content.style.display = 'block';
            toggle.classList.remove('fa-chevron-right');
            toggle.classList.add('fa-chevron-down');
        } else {
            content.style.display = 'none';
            toggle.classList.remove('fa-chevron-down');
            toggle.classList.add('fa-chevron-right');
        }
        
        // Sauvegarder l'état après chaque changement
        saveFolderStates();
    }
}

// Initialiser les événements de basculement des dossiers
function initTreeFolderToggles(classId) {
    // Les événements sont gérés par onclick dans le HTML
    // Pas besoin d'initialisation supplémentaire
}

// Initialiser la sélection des fichiers et dossiers de classe
function initClassFileSelection(classId) {
    const treeFiles = document.querySelectorAll(`.tree-file[data-class-id="${classId}"]`);
    const treeFolders = document.querySelectorAll(`.tree-folder[data-class-id="${classId}"]`);
    
    // Sélection des fichiers
    treeFiles.forEach(file => {
        file.addEventListener('click', function(e) {
            // Ignorer le clic sur le bouton de suppression
            if (e.target.closest('.tree-file-delete')) return;
            
            // Désélectionner tous les autres éléments
            document.querySelectorAll('.tree-file.selected, .tree-folder.selected').forEach(f => f.classList.remove('selected'));
            
            // Sélectionner ce fichier
            this.classList.add('selected');
            selectedClassFile = {
                type: 'file',
                id: this.dataset.fileId,
                classId: this.dataset.classId,
                element: this,
                name: this.querySelector('.tree-item-name').textContent
            };
            
            console.log('Fichier sélectionné:', selectedClassFile);
        });
    });
    
    // Sélection des dossiers
    treeFolders.forEach(folder => {
        folder.addEventListener('click', function(e) {
            // Ignorer le clic sur l'icône toggle et les éléments enfants
            if (e.target.closest('.tree-folder-toggle') || 
                e.target.closest('.tree-folder-content') ||
                e.target !== this && !e.target.classList.contains('tree-folder-header') &&
                !e.target.classList.contains('tree-item-name') &&
                !e.target.classList.contains('tree-item-icon')) {
                return;
            }
            
            e.stopPropagation();
            
            // Désélectionner tous les autres éléments
            document.querySelectorAll('.tree-file.selected, .tree-folder.selected').forEach(f => f.classList.remove('selected'));
            
            // Sélectionner ce dossier
            this.classList.add('selected');
            selectedClassFile = {
                type: 'folder',
                path: this.dataset.folderPath,
                classId: this.dataset.classId,
                element: this,
                name: this.dataset.folderPath.split('/').pop()
            };
            
            console.log('Dossier sélectionné:', selectedClassFile);
        });
    });
}

// Fonction pour supprimer un fichier de classe
async function deleteClassFile(fileId, classId) {
    console.log(`🔍 deleteClassFile appelée avec fileId=${fileId}, classId=${classId}`);

    try {
        const url = `/api/class-files/delete/${fileId}`;
        console.log(`🔍 Envoi requête DELETE vers: ${url}`);
        
        const response = await fetch(url, {
            method: 'DELETE'
        });

        console.log(`🔍 Réponse reçue:`, response.status, response.statusText);
        const result = await response.json();
        console.log(`🔍 Contenu de la réponse:`, result);

        if (result.success) {
            showNotification('success', 'Fichier supprimé de la classe');
            
            // Recharger l'arborescence de la classe
            console.log(`🔍 Rechargement de l'arborescence pour la classe ${classId}`);
            await loadClassTree(classId);
        } else {
            console.log(`❌ Erreur côté serveur: ${result.message}`);
            showNotification('error', result.message || 'Erreur lors de la suppression');
        }
    } catch (error) {
        console.error('❌ Erreur JavaScript:', error);
        showNotification('error', 'Erreur lors de la suppression du fichier');
    }
}

// Fonction pour supprimer un dossier entier d'une classe
async function deleteClassFolder(folderPath, classId) {

    try {
        const response = await fetch('/file_manager/delete-class-folder', {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                folder_path: folderPath,
                class_id: classId
            })
        });

        const result = await response.json();

        if (result.success) {
            showNotification('success', `Dossier "${folderPath}" supprimé de la classe`);
            
            // Recharger l'arborescence de la classe
            await loadClassTree(classId);
        } else {
            showNotification('error', result.message || 'Erreur lors de la suppression');
        }
    } catch (error) {
        console.error('Erreur:', error);
        showNotification('error', 'Erreur lors de la suppression du dossier');
    }
}

// Fonction pour supprimer l'élément sélectionné avec une popup de confirmation
function deleteSelectedClassItem() {
    console.log('🔍 deleteSelectedClassItem appelée');
    console.log('🔍 selectedClassFile:', selectedClassFile);
    
    if (!selectedClassFile || !selectedClassFile.element) {
        console.log('❌ Aucun élément sélectionné');
        showNotification('error', 'Aucun élément sélectionné');
        return;
    }

    const item = selectedClassFile;
    let confirmMessage = '';
    
    console.log('🔍 Type d\'élément:', item.type);
    
    if (item.type === 'file') {
        confirmMessage = `Êtes-vous sûr de vouloir supprimer le fichier "${item.name}" de la classe ?`;
    } else if (item.type === 'folder') {
        confirmMessage = `Êtes-vous sûr de vouloir supprimer le dossier "${item.name}" et tout son contenu de la classe ?`;
    } else {
        console.log('❌ Type d\'élément non reconnu:', item.type);
        showNotification('error', 'Type d\'élément non reconnu');
        return;
    }

    console.log('🔍 Message de confirmation:', confirmMessage);

    // Créer une popup de confirmation personnalisée
    showConfirmDialog(confirmMessage, async () => {
        console.log('🔍 Confirmation reçue, suppression en cours...');
        if (item.type === 'file') {
            await deleteClassFile(item.id, item.classId);
        } else if (item.type === 'folder') {
            await deleteClassFolder(item.path, item.classId);
        }
        
        // Désélectionner l'élément après suppression
        selectedClassFile = null;
    });
}

// Fonction pour afficher une popup de confirmation personnalisée
function showConfirmDialog(message, onConfirm) {
    // Créer le modal de confirmation
    const modal = document.createElement('div');
    modal.className = 'modal show';
    modal.style.zIndex = '1004';
    
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h3><i class="fas fa-exclamation-triangle" style="color: #F59E0B;"></i> Confirmation de suppression</h3>
            </div>
            <div class="modal-body">
                <p>${message}</p>
                <p style="font-size: 0.875rem; color: #6B7280; margin-top: 1rem;">
                    <i class="fas fa-info-circle"></i> Cette action ne supprimera l'élément que de cette classe, pas de vos documents personnels.
                </p>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-outline" onclick="closeConfirmDialog()">
                    <i class="fas fa-times"></i> Annuler
                </button>
                <button type="button" class="btn btn-danger" onclick="confirmDelete()">
                    <i class="fas fa-trash"></i> Supprimer
                </button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Stocker la fonction de confirmation
    window.currentConfirmAction = onConfirm;
}

// Fonction pour fermer le dialog de confirmation
function closeConfirmDialog() {
    const modal = document.querySelector('.modal[style*="1004"]');
    if (modal) {
        modal.remove();
    }
    window.currentConfirmAction = null;
}

// Fonction pour confirmer la suppression
function confirmDelete() {
    if (window.currentConfirmAction) {
        window.currentConfirmAction();
    }
    closeConfirmDialog();
}

// Obtenir l'icône d'un fichier selon son type
function getFileIcon(fileType) {
    switch(fileType) {
        case 'pdf': return 'fas fa-file-pdf';
        case 'png':
        case 'jpg':
        case 'jpeg': return 'fas fa-file-image';
        default: return 'fas fa-file';
    }
}

// Initialiser le drag & drop sur les dossiers de l'arborescence
function initTreeFolderDropZones(classId) {
    const treeFolders = document.querySelectorAll(`.tree-folder[data-class-id="${classId}"]`);

    treeFolders.forEach(treeFolder => {
        treeFolder.addEventListener('dragover', handleTreeFolderDragOver);
        treeFolder.addEventListener('dragleave', handleTreeFolderDragLeave);
        treeFolder.addEventListener('drop', handleTreeFolderDrop);
    });
}

// Nouvelle fonction pour gérer le double-clic sur les fichiers
function initDoubleClickHandler() {
    const fileGrid = document.getElementById('fileGrid');

    if (fileGrid) {
        fileGrid.addEventListener('dblclick', (e) => {
            if (isDeleteMode) return;

            const fileItem = e.target.closest('.file-item.file');
            if (fileItem) {
                e.preventDefault();
                e.stopPropagation();

                const fileId = fileItem.dataset.id;
                const fileType = getFileTypeFromItem(fileItem);

                // Pour les images et PDFs, ouvrir l'aperçu dans un nouvel onglet
                if (['png', 'jpg', 'jpeg', 'pdf'].includes(fileType)) {
                    openFileInNewTab(fileId);
                } else {
                    // Pour les autres types, télécharger directement
                    downloadFileDirectly(fileId);
                }
            }
        });

        // Gérer le double-clic sur les dossiers pour les ouvrir
        fileGrid.addEventListener('dblclick', (e) => {
            if (isDeleteMode) return;

            const folderItem = e.target.closest('.file-item.folder');
            if (folderItem) {
                e.preventDefault();
                e.stopPropagation();

                const folderId = folderItem.dataset.id;
                openFolder(folderId);
            }
        });
    }
}

// Initialiser le drag & drop des fichiers vers les classes
function initFileDragAndDrop() {
    const fileItems = document.querySelectorAll('.file-item.file');
    const folderItems = document.querySelectorAll('.file-item.folder');

    // Fichiers
    fileItems.forEach(fileItem => {
        fileItem.addEventListener('dragstart', handleFileDragStart);
        fileItem.addEventListener('dragend', handleFileDragEnd);
    });

    // Dossiers
    folderItems.forEach(folderItem => {
        folderItem.addEventListener('dragstart', handleFolderDragStart);
        folderItem.addEventListener('dragend', handleFileDragEnd);
    });
}

// Gestion du début de drag d'un dossier
function handleFolderDragStart(e) {
    if (isDeleteMode) {
        e.preventDefault();
        return;
    }

    const folderId = e.target.dataset.id;
    e.dataTransfer.setData('text/plain', `folder:${folderId}`);
    e.target.classList.add('dragging');
}

// Gestion du début de drag d'un fichier
function handleFileDragStart(e) {
    if (isDeleteMode) {
        e.preventDefault();
        return;
    }

    const fileId = e.target.dataset.id;
    e.dataTransfer.setData('text/plain', `file:${fileId}`);
    e.target.classList.add('dragging');
}

// Gestion de la fin de drag d'un fichier
function handleFileDragEnd(e) {
    e.target.classList.remove('dragging');
}

// Gestion du drag over une classe
function handleClassDragOver(e) {
    e.preventDefault();
    e.target.closest('.class-header').classList.add('drag-over');
}

// Gestion du drag leave une classe
function handleClassDragLeave(e) {
    e.target.closest('.class-header').classList.remove('drag-over');
}

// Gestion du drop sur une classe
async function handleClassDrop(e) {
    e.preventDefault();
    const classHeader = e.target.closest('.class-header');
    classHeader.classList.remove('drag-over');

    const dragData = e.dataTransfer.getData('text/plain');
    const classId = e.target.closest('.class-item').dataset.classId;

    if (dragData && classId) {
        if (dragData.startsWith('file:')) {
            const fileId = dragData.replace('file:', '');
            await copyFileToClass(fileId, classId);
        } else if (dragData.startsWith('folder:')) {
            const folderId = dragData.replace('folder:', '');
            await copyFolderToClass(folderId, classId);
        }
    }
}

// Fonctions supprimées - retour à l'ancien système

// Gestion du drag over un dossier d'arborescence
function handleTreeFolderDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    const treeFolder = e.target.closest('.tree-folder');
    if (treeFolder) {
        treeFolder.classList.add('drag-over');
    }
}

// Gestion du drag leave un dossier d'arborescence
function handleTreeFolderDragLeave(e) {
    e.stopPropagation();
    const treeFolder = e.target.closest('.tree-folder');
    if (treeFolder && !treeFolder.contains(e.relatedTarget)) {
        treeFolder.classList.remove('drag-over');
    }
}

// Gestion du drop sur un dossier d'arborescence
async function handleTreeFolderDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    const treeFolder = e.target.closest('.tree-folder');
    if (treeFolder) {
        treeFolder.classList.remove('drag-over');

        const dragData = e.dataTransfer.getData('text/plain');
        const classId = treeFolder.dataset.classId;
        const folderPath = treeFolder.dataset.folderPath;

        if (dragData && classId && folderPath) {
            if (dragData.startsWith('file:')) {
                const fileId = dragData.replace('file:', '');
                await copyFileToClassFolder(fileId, classId, folderPath);
            } else if (dragData.startsWith('folder:')) {
                const folderId = dragData.replace('folder:', '');
                await copyFolderToClassFolder(folderId, classId, folderPath);
            }
        }
    }
}

// Copier un dossier complet vers une classe
async function copyFolderToClass(folderId, classId) {
    try {
        const response = await fetch('/api/class-files/copy-folder', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                folder_id: folderId,
                class_id: classId
            })
        });

        const result = await response.json();

        if (result.success) {
            const className = classes.find(c => c.id == classId)?.name || 'la classe';
            showNotification('success', `Dossier copié dans ${className}`);

            // Ouvrir et recharger l'arborescence de la classe
            const tree = document.getElementById(`classTree-${classId}`);
            const toggle = document.getElementById(`toggle-${classId}`);
            
            // Recharger l'arborescence
            await loadClassTree(classId);
            
            // S'assurer que l'arborescence est visible
            if (tree && tree.style.display === 'none') {
                tree.style.display = 'block';
                if (toggle) {
                    toggle.classList.add('expanded');
                }
                // Sauvegarder l'état
                saveTreeStates();
            }
        } else {
            showNotification('error', result.message || 'Erreur lors de la copie');
        }
    } catch (error) {
        console.error('Erreur:', error);
        showNotification('error', 'Erreur lors de la copie du dossier');
    }
}

// Copier un fichier vers un dossier spécifique d'une classe
async function copyFileToClassFolder(fileId, classId, folderName) {
    try {
        const response = await fetch('/file_manager/copy-to-class-folder', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                file_id: fileId,
                class_id: classId,
                folder_name: folderName
            })
        });

        const result = await response.json();

        if (result.success) {
            showNotification('success', `Fichier copié dans ${folderName}`);

            // Recharger l'arborescence
            await loadClassTree(classId);
        } else {
            showNotification('error', result.message || 'Erreur lors de la copie');
        }
    } catch (error) {
        console.error('Erreur:', error);
        showNotification('error', 'Erreur lors de la copie du fichier');
    }
}

// Copier un dossier vers un dossier spécifique d'une classe
async function copyFolderToClassFolder(folderId, classId, folderName) {
    try {
        const response = await fetch('/file_manager/copy-folder-to-class-folder', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                folder_id: folderId,
                class_id: classId,
                folder_name: folderName
            })
        });

        const result = await response.json();

        if (result.success) {
            showNotification('success', `Dossier copié dans ${folderName}`);

            // Recharger l'arborescence
            await loadClassTree(classId);
        } else {
            showNotification('error', result.message || 'Erreur lors de la copie');
        }
    } catch (error) {
        console.error('Erreur:', error);
        showNotification('error', 'Erreur lors de la copie du dossier');
    }
}

// Copier un fichier vers une classe
async function copyFileToClass(fileId, classId) {
    try {
        const response = await fetch('/api/class-files/copy-file', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                file_id: fileId,
                class_id: classId
            })
        });

        const result = await response.json();

        if (result.success) {
            const className = classes.find(c => c.id == classId)?.name || 'la classe';
            showNotification('success', `Fichier copié dans ${className}`);

            // Ouvrir et recharger l'arborescence de la classe
            const tree = document.getElementById(`classTree-${classId}`);
            const toggle = document.getElementById(`toggle-${classId}`);
            
            // Recharger l'arborescence
            await loadClassTree(classId);
            
            // S'assurer que l'arborescence est visible
            if (tree && tree.style.display === 'none') {
                tree.style.display = 'block';
                if (toggle) {
                    toggle.classList.add('expanded');
                }
            }
        } else {
            showNotification('error', result.message || 'Erreur lors de la copie');
        }
    } catch (error) {
        console.error('Erreur:', error);
        showNotification('error', 'Erreur lors de la copie du fichier');
    }
}

// Mode suppression multiple
function toggleDeleteMode() {
    isDeleteMode = !isDeleteMode;
    const deleteModeBtn = document.getElementById('deleteModeBtn');
    const deleteActions = document.getElementById('deleteActions');
    const checkboxes = document.querySelectorAll('.item-checkbox');
    const fileItems = document.querySelectorAll('.file-item');

    if (isDeleteMode) {
        deleteModeBtn.classList.add('active');
        deleteModeBtn.innerHTML = '<i class="fas fa-times"></i> Annuler';
        deleteActions.style.display = 'block';

        checkboxes.forEach(checkbox => {
            checkbox.style.display = 'block';
        });

        fileItems.forEach(item => {
            item.classList.add('delete-mode');
        });

        // Ajouter les événements de sélection
        initCheckboxEvents();
    } else {
        cancelDeleteMode();
    }
}

function cancelDeleteMode() {
    isDeleteMode = false;
    const deleteModeBtn = document.getElementById('deleteModeBtn');
    const deleteActions = document.getElementById('deleteActions');
    const checkboxes = document.querySelectorAll('.item-checkbox');
    const fileItems = document.querySelectorAll('.file-item');

    deleteModeBtn.classList.remove('active');
    deleteModeBtn.innerHTML = '<i class="fas fa-trash"></i> Supprimer';
    deleteActions.style.display = 'none';

    checkboxes.forEach(checkbox => {
        checkbox.style.display = 'none';
        checkbox.querySelector('input').checked = false;
    });

    fileItems.forEach(item => {
        item.classList.remove('delete-mode');
    });

    updateDeleteButton();
}

// Initialiser les événements des cases à cocher
function initCheckboxEvents() {
    const checkboxes = document.querySelectorAll('.delete-checkbox');

    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', updateDeleteButton);
    });
}

// Mettre à jour le bouton de suppression
function updateDeleteButton() {
    const selectedCheckboxes = document.querySelectorAll('.delete-checkbox:checked');
    const deleteBtn = document.getElementById('deleteSelectedBtn');

    const count = selectedCheckboxes.length;
    deleteBtn.innerHTML = `<i class="fas fa-trash"></i> Supprimer les ${count} élément(s)`;
    deleteBtn.disabled = count === 0;
}

// Supprimer les éléments sélectionnés
async function deleteSelectedItems() {
    const selectedCheckboxes = document.querySelectorAll('.delete-checkbox:checked');

    if (selectedCheckboxes.length === 0) return;

    const items = Array.from(selectedCheckboxes).map(checkbox => ({
        id: checkbox.dataset.id,
        type: checkbox.dataset.type
    }));

    try {
        const response = await fetch('/file_manager/delete-multiple', {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ items })
        });

        const result = await response.json();

        if (result.success) {
            showNotification('success', `${items.length} élément(s) supprimé(s)`);
            cancelDeleteMode();
            location.reload();
        } else {
            showNotification('error', result.message || 'Erreur lors de la suppression');
        }
    } catch (error) {
        console.error('Erreur:', error);
        showNotification('error', 'Erreur lors de la suppression');
    }
}

// Fonction pour obtenir le type de fichier depuis l'élément DOM
function getFileTypeFromItem(fileItem) {
    const icon = fileItem.querySelector('.item-icon i');
    if (icon) {
        if (icon.classList.contains('fa-file-pdf')) return 'pdf';
        if (icon.classList.contains('fa-file-image')) return 'jpg';
    }

    // Fallback: essayer de déduire du nom du fichier
    const fileName = fileItem.querySelector('.item-name').textContent;
    const extension = fileName.split('.').pop().toLowerCase();
    return extension;
}

// Fonction pour ouvrir un fichier dans un nouvel onglet
function openFileInNewTab(fileId) {
    const previewUrl = `/file_manager/preview/${fileId}`;
    window.open(previewUrl, '_blank');
}

// Fonction pour télécharger un fichier directement
function downloadFileDirectly(fileId) {
    const downloadUrl = `/file_manager/download/${fileId}`;

    // Créer un lien temporaire pour déclencher le téléchargement
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.style.display = 'none';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Gestion du drag & drop
function initDragAndDrop() {
    const fileExplorer = document.getElementById('fileExplorer');
    const dropZone = document.getElementById('dropZone');

    // Prévenir le comportement par défaut
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        fileExplorer.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    // Afficher la zone de drop
    ['dragenter', 'dragover'].forEach(eventName => {
        fileExplorer.addEventListener(eventName, (e) => {
            // Ne pas afficher si c'est un drag de fichier interne
            if (!e.dataTransfer.types.includes('Files')) return;
            dropZone.classList.add('active');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        fileExplorer.addEventListener(eventName, () => {
            dropZone.classList.remove('active');
        });
    });

    // Gérer le drop
    fileExplorer.addEventListener('drop', handleDrop);
}

// Gérer le drop de fichiers
async function handleDrop(e) {
    const dt = e.dataTransfer;
    const items = dt.items;

    if (items && items.length > 0) {
        // Utiliser DataTransferItemList pour gérer les dossiers
        const entries = [];
        
        for (let i = 0; i < items.length; i++) {
            const item = items[i];
            if (item.kind === 'file') {
                const entry = item.webkitGetAsEntry ? item.webkitGetAsEntry() : item.getAsEntry();
                if (entry) {
                    entries.push(entry);
                }
            }
        }
        
        if (entries.length > 0) {
            await handleFileSystemEntries(entries);
        }
    } else if (dt.files.length > 0) {
        // Fallback pour les navigateurs qui ne supportent pas webkitGetAsEntry
        handleFiles(dt.files);
    }
}

// Gérer les entrées du système de fichiers (dossiers et fichiers)
async function handleFileSystemEntries(entries) {
    showNotification('info', 'Analyse de la structure en cours...');
    
    // Structure pour stocker tous les fichiers avec leur chemin
    const fileStructure = {
        folders: new Set(),
        files: []
    };
    
    // Parcourir récursivement toutes les entrées
    for (const entry of entries) {
        await traverseFileSystem(entry, '', fileStructure);
    }
    
    // Créer d'abord tous les dossiers
    if (fileStructure.folders.size > 0) {
        await createFolderStructure(Array.from(fileStructure.folders));
    }
    
    // Ensuite uploader tous les fichiers
    if (fileStructure.files.length > 0) {
        showNotification('info', `Upload de ${fileStructure.files.length} fichier(s) en cours...`);
        await uploadFilesWithStructure(fileStructure.files);
    }
}

// Parcourir récursivement le système de fichiers
async function traverseFileSystem(entry, path, fileStructure) {
    if (entry.isFile) {
        // C'est un fichier
        const file = await new Promise((resolve) => {
            entry.file(resolve);
        });
        
        fileStructure.files.push({
            file: file,
            path: path,
            relativePath: path + file.name
        });
    } else if (entry.isDirectory) {
        // C'est un dossier
        const folderPath = path + entry.name + '/';
        fileStructure.folders.add(folderPath);
        
        // Lire le contenu du dossier
        const dirReader = entry.createReader();
        let entries = [];
        
        // Lire tous les fichiers du dossier (peut nécessiter plusieurs appels)
        const readEntries = async () => {
            const results = await new Promise((resolve) => {
                dirReader.readEntries(resolve);
            });
            
            if (results.length > 0) {
                entries = entries.concat(results);
                await readEntries();
            }
        };
        
        await readEntries();
        
        // Parcourir récursivement chaque entrée
        for (const childEntry of entries) {
            await traverseFileSystem(childEntry, folderPath, fileStructure);
        }
    }
}

// Créer la structure de dossiers
async function createFolderStructure(folderPaths) {
    // Trier les chemins pour créer les dossiers parents en premier
    folderPaths.sort((a, b) => a.split('/').length - b.split('/').length);
    
    try {
        const response = await fetch('/file_manager/create-folder-structure', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                folders: folderPaths,
                parent_id: currentFolderId
            })
        });
        
        const result = await response.json();
        
        if (!result.success) {
            showNotification('error', 'Erreur lors de la création des dossiers');
            return false;
        }
        
        return true;
    } catch (error) {
        console.error('Erreur:', error);
        showNotification('error', 'Erreur lors de la création de la structure');
        return false;
    }
}

// Uploader les fichiers avec leur structure
async function uploadFilesWithStructure(filesData) {
    const totalFiles = filesData.length;
    let uploadedCount = 0;
    
    showUploadProgress();
    
    for (const fileData of filesData) {
        const formData = new FormData();
        formData.append('file', fileData.file);
        formData.append('folder_path', fileData.path);
        
        if (currentFolderId) {
            formData.append('parent_folder_id', currentFolderId);
        }
        
        try {
            const xhr = new XMLHttpRequest();
            
            // Mise à jour de la progression
            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable) {
                    const fileProgress = (e.loaded / e.total) * 100;
                    const totalProgress = ((uploadedCount + fileProgress / 100) / totalFiles) * 100;
                    updateUploadProgress(totalProgress, `${fileData.file.name} (${uploadedCount + 1}/${totalFiles})`);
                }
            });
            
            // Promesse pour gérer la réponse
            await new Promise((resolve, reject) => {
                xhr.onload = () => {
                    if (xhr.status === 200) {
                        uploadedCount++;
                        resolve(JSON.parse(xhr.responseText));
                    } else {
                        reject(new Error(`Upload failed: ${xhr.status}`));
                    }
                };
                xhr.onerror = reject;
                
                xhr.open('POST', '/file_manager/upload-with-structure');
                xhr.send(formData);
            });
            
        } catch (error) {
            console.error(`Erreur lors de l'upload de ${fileData.file.name}:`, error);
        }
    }
    
    hideUploadProgress();
    showNotification('success', `${uploadedCount} fichier(s) uploadé(s) avec succès`);
    
    // Recharger la page
    setTimeout(() => location.reload(), 1500);
}

// Gérer la sélection de fichiers
function handleFileSelect(e) {
    const files = e.target.files;
    handleFiles(files);
}

// Traiter les fichiers sélectionnés
function handleFiles(files) {
    ([...files]).forEach(file => {
        if (validateFile(file)) {
            uploadQueue.push(file);
        }
    });

    if (uploadQueue.length > 0) {
        processUploadQueue();
    }
}

// Valider un fichier
function validateFile(file) {
    const allowedTypes = ['application/pdf', 'image/png', 'image/jpeg', 'image/jpg'];
    const maxSize = 80 * 1024 * 1024; // 80 MB

    if (!allowedTypes.includes(file.type)) {
        showNotification('error', `Type de fichier non autorisé: ${file.name}`);
        return false;
    }

    if (file.size > maxSize) {
        showNotification('error', `Fichier trop volumineux: ${file.name} (max 80 MB)`);
        return false;
    }

    return true;
}

// Traiter la file d'upload
async function processUploadQueue() {
    if (isUploading || uploadQueue.length === 0) return;

    isUploading = true;
    showUploadProgress();

    while (uploadQueue.length > 0) {
        const file = uploadQueue.shift();
        await uploadFile(file);
    }

    isUploading = false;
    hideUploadProgress();

    // Recharger la page pour afficher les nouveaux fichiers
    location.reload();
}

// Uploader un fichier
async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    if (currentFolderId) {
        formData.append('folder_id', currentFolderId);
    }

    try {
        const xhr = new XMLHttpRequest();

        // Mise à jour de la progression
        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const percentComplete = (e.loaded / e.total) * 100;
                updateUploadProgress(percentComplete, file.name);
            }
        });

        // Promesse pour gérer la réponse
        const response = await new Promise((resolve, reject) => {
            xhr.onload = () => {
                if (xhr.status === 200) {
                    resolve(JSON.parse(xhr.responseText));
                } else {
                    reject(new Error(`Upload failed: ${xhr.status}`));
                }
            };
            xhr.onerror = reject;

            xhr.open('POST', '/file_manager/upload');
            xhr.send(formData);
        });

        if (response.success) {
            showNotification('success', `${file.name} uploadé avec succès`);
        } else {
            showNotification('error', response.message || `Erreur lors de l'upload de ${file.name}`);
        }
    } catch (error) {
        console.error('Erreur upload:', error);
        showNotification('error', `Erreur lors de l'upload de ${file.name}`);
    }
}

// Afficher la progression d'upload
function showUploadProgress() {
    const progress = document.getElementById('uploadProgress');
    progress.classList.add('show');
}

// Masquer la progression d'upload
function hideUploadProgress() {
    const progress = document.getElementById('uploadProgress');
    progress.classList.remove('show');

    // Réinitialiser
    document.getElementById('progressFill').style.width = '0%';
    document.getElementById('progressPercent').textContent = '0%';
    document.getElementById('progressInfo').textContent = '';
}

// Mettre à jour la progression
function updateUploadProgress(percent, filename) {
    document.getElementById('progressFill').style.width = percent + '%';
    document.getElementById('progressPercent').textContent = Math.round(percent) + '%';
    document.getElementById('progressInfo').textContent = filename;
}

// Créer un nouveau dossier
function showNewFolderModal() {
    document.getElementById('newFolderModal').classList.add('show');
    document.getElementById('folderName').focus();
}

// Créer le dossier
async function createFolder(e) {
    e.preventDefault();

    const name = document.getElementById('folderName').value;
    const color = document.querySelector('input[name="folderColor"]:checked').value;

    try {
        const response = await fetch('/file_manager/create-folder', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                name: name,
                color: color,
                parent_id: currentFolderId
            })
        });

        const result = await response.json();

        if (result.success) {
            showNotification('success', result.message);
            closeModal('newFolderModal');
            location.reload();
        } else {
            showNotification('error', result.message || 'Erreur lors de la création du dossier');
        }
    } catch (error) {
        console.error('Erreur:', error);
        showNotification('error', 'Erreur lors de la création du dossier');
    }
}

// Ouvrir un dossier
function openFolder(folderId) {
    window.location.href = `/files?folder=${folderId}`;
}

// Afficher le sélecteur de couleur pour un dossier
function showColorPicker(folderId) {
    // Pour simplifier, on pourrait créer un petit modal de sélection de couleur
    const colors = ['#4F46E5', '#7C3AED', '#EC4899', '#F59E0B', '#10B981', '#3B82F6', '#6B7280', '#EF4444'];
    const color = prompt('Choisissez une couleur (hex):', '#4F46E5');

    if (color && colors.includes(color)) {
        updateFolderColor(folderId, color);
    }
}

// Mettre à jour la couleur d'un dossier
async function updateFolderColor(folderId, color) {
    try {
        const response = await fetch('/file_manager/update-folder-color', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                id: folderId,
                color: color
            })
        });

        const result = await response.json();

        if (result.success) {
            showNotification('success', result.message);
            location.reload();
        } else {
            showNotification('error', result.message || 'Erreur lors de la mise à jour');
        }
    } catch (error) {
        console.error('Erreur:', error);
        showNotification('error', 'Erreur lors de la mise à jour');
    }
}

// Prévisualiser un fichier
function previewFile(fileId, fileType) {
    const modal = document.getElementById('previewModal');
    const content = document.getElementById('previewContent');
    const title = document.getElementById('previewTitle');

    title.textContent = 'Aperçu';

    if (fileType === 'pdf') {
        content.innerHTML = `<iframe src="/file_manager/preview/${fileId}"></iframe>`;
    } else {
        content.innerHTML = `<img src="/file_manager/preview/${fileId}" alt="Aperçu">`;
    }

    modal.classList.add('show');
}

// Renommer un élément
function renameItem(type, id, currentName) {
    const modal = document.getElementById('renameModal');
    document.getElementById('renameType').value = type;
    document.getElementById('renameId').value = id;
    document.getElementById('renameName').value = currentName;

    modal.classList.add('show');
    document.getElementById('renameName').focus();
    document.getElementById('renameName').select();
}

// Sauvegarder le renommage
async function saveRename(e) {
    e.preventDefault();

    const type = document.getElementById('renameType').value;
    const id = document.getElementById('renameId').value;
    const name = document.getElementById('renameName').value;

    try {
        const response = await fetch('/file_manager/rename', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                type: type,
                id: id,
                name: name
            })
        });

        const result = await response.json();

        if (result.success) {
            showNotification('success', result.message);
            closeModal('renameModal');
            location.reload();
        } else {
            showNotification('error', result.message || 'Erreur lors du renommage');
        }
    } catch (error) {
        console.error('Erreur:', error);
        showNotification('error', 'Erreur lors du renommage');
    }
}

// Supprimer un fichier
async function deleteFile(fileId) {
    if (!confirm('Êtes-vous sûr de vouloir supprimer ce fichier ?')) return;

    try {
        const response = await fetch(`/file_manager/delete-file/${fileId}`, {
            method: 'DELETE'
        });

        const result = await response.json();

        if (result.success) {
            showNotification('success', result.message);
            location.reload();
        } else {
            showNotification('error', result.message || 'Erreur lors de la suppression');
        }
    } catch (error) {
        console.error('Erreur:', error);
        showNotification('error', 'Erreur lors de la suppression');
    }
}

// Supprimer un dossier
async function deleteFolder(folderId) {
    if (!confirm('Êtes-vous sûr de vouloir supprimer ce dossier et tout son contenu ?')) return;

    try {
        const response = await fetch(`/file_manager/delete-folder/${folderId}`, {
            method: 'DELETE'
        });

        const result = await response.json();

        if (result.success) {
            showNotification('success', result.message);
            location.reload();
        } else {
            showNotification('error', result.message || 'Erreur lors de la suppression');
        }
    } catch (error) {
        console.error('Erreur:', error);
        showNotification('error', 'Erreur lors de la suppression');
    }
}

// Fermer un modal
function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('show');
}

// Menu contextuel
function initContextMenu() {
    const fileGrid = document.getElementById('fileGrid');
    const fileExplorer = document.getElementById('fileExplorer');

    // Menu contextuel sur les items
    fileGrid.addEventListener('contextmenu', (e) => {
        e.preventDefault();

        const item = e.target.closest('.file-item');
        if (item) {
            showContextMenu(e, item);
        }
    });

    // Menu contextuel dans l'espace vide
    fileExplorer.addEventListener('contextmenu', (e) => {
        e.preventDefault();

        // Vérifier si on n'est pas sur un item
        if (!e.target.closest('.file-item')) {
            showEmptySpaceContextMenu(e);
        }
    });

    // Fermer le menu en cliquant ailleurs et désélectionner les fichiers de classe
    document.addEventListener('click', (e) => {
        // Fermer le menu contextuel
        const menu = document.querySelector('.context-menu');
        if (menu) menu.remove();
        
        // Désélectionner les fichiers de classe si on clique ailleurs
        if (!e.target.closest('.tree-file') && !e.target.closest('.tree-file-delete')) {
            document.querySelectorAll('.tree-file.selected').forEach(f => f.classList.remove('selected'));
            selectedClassFile = null;
        }
    });
}

// Menu contextuel dans l'espace vide
function showEmptySpaceContextMenu(e) {
    // Supprimer tout menu existant
    const existingMenu = document.querySelector('.context-menu');
    if (existingMenu) existingMenu.remove();

    const menu = document.createElement('div');
    menu.className = 'context-menu show';
    menu.style.left = e.pageX + 'px';
    menu.style.top = e.pageY + 'px';

    menu.innerHTML = `
        <div class="context-menu-item" onclick="showNewFolderModal(); this.parentElement.remove();">
            <i class="fas fa-folder-plus"></i> Nouveau dossier
        </div>
        <div class="context-menu-item" onclick="document.getElementById('fileInput').click(); this.parentElement.remove();">
            <i class="fas fa-upload"></i> Uploader un fichier
        </div>
    `;

    document.body.appendChild(menu);
}

// Afficher le menu contextuel
function showContextMenu(e, item) {
    if (isDeleteMode) return;

    // Supprimer tout menu existant
    const existingMenu = document.querySelector('.context-menu');
    if (existingMenu) existingMenu.remove();

    const type = item.dataset.type;
    const id = item.dataset.id;
    const name = item.querySelector('.item-name').textContent;

    const menu = document.createElement('div');
    menu.className = 'context-menu show';
    menu.style.left = e.pageX + 'px';
    menu.style.top = e.pageY + 'px';

    if (type === 'folder') {
        menu.innerHTML = `
            <div class="context-menu-item" onclick="openFolder(${id})">
                <i class="fas fa-folder-open"></i> Ouvrir
            </div>
            <div class="context-menu-item" onclick="renameItem('folder', ${id}, '${name}')">
                <i class="fas fa-edit"></i> Renommer
            </div>
            <div class="context-menu-separator"></div>
            <div class="context-menu-item danger" onclick="deleteFolder(${id})">
                <i class="fas fa-trash"></i> Supprimer
            </div>
        `;
    } else {
        menu.innerHTML = `
            <div class="context-menu-item" onclick="previewFile(${id}, '${item.querySelector('.item-icon i').classList.contains('fa-file-pdf') ? 'pdf' : 'image'}')">
                <i class="fas fa-eye"></i> Aperçu
            </div>
            <a class="context-menu-item" href="/file_manager/download/${id}">
                <i class="fas fa-download"></i> Télécharger
            </a>
            <div class="context-menu-item" onclick="renameItem('file', ${id}, '${name}')">
                <i class="fas fa-edit"></i> Renommer
            </div>
            <div class="context-menu-separator"></div>
            <div class="context-menu-item danger" onclick="deleteFile(${id})">
                <i class="fas fa-trash"></i> Supprimer
            </div>
        `;
    }

    document.body.appendChild(menu);
}

// Raccourcis clavier
function initKeyboardShortcuts() {
    console.log('🔍 Initialisation des raccourcis clavier');
    document.addEventListener('keydown', (e) => {
        console.log('🔍 Touche pressée:', e.key);
        // Escape pour fermer les modals ou annuler le mode suppression
        if (e.key === 'Escape') {
            const modals = document.querySelectorAll('.modal.show');
            modals.forEach(modal => modal.classList.remove('show'));

            if (isDeleteMode) {
                cancelDeleteMode();
            }
        }

        // Ctrl/Cmd + N pour nouveau dossier
        if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
            e.preventDefault();
            showNewFolderModal();
        }

        // Ctrl/Cmd + U pour upload
        if ((e.ctrlKey || e.metaKey) && e.key === 'u') {
            e.preventDefault();
            document.getElementById('fileInput').click();
        }

        // Delete/Backspace pour activer le mode suppression ou supprimer un élément de classe sélectionné
        if (e.key === 'Delete' || e.key === 'Backspace') {
            console.log('🔍 Touche Delete/Backspace pressée:', e.key);
            console.log('🔍 selectedClassFile:', selectedClassFile);
            e.preventDefault();
            
            // Si un élément de classe est sélectionné, le supprimer avec confirmation
            if (selectedClassFile && selectedClassFile.element) {
                console.log('🔍 Suppression d\'un élément de classe');
                deleteSelectedClassItem();
            } 
            // Sinon, activer le mode suppression pour les fichiers principaux
            else if (!isDeleteMode) {
                console.log('🔍 Activation du mode suppression');
                toggleDeleteMode();
            } else {
                console.log('🔍 Aucune action (mode suppression déjà actif)');
            }
        }
    });
}

// Notifications
function showNotification(type, message) {
    // Utiliser la fonction existante ou en créer une simple
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem 1.5rem;
        background-color: ${type === 'success' ? '#D1FAE5' : '#FEE2E2'};
        color: ${type === 'success' ? '#065F46' : '#991B1B'};
        border-radius: 0.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        display: flex;
        align-items: center;
        gap: 0.5rem;
        z-index: 1003;
        animation: slideInRight 0.3s ease;
        max-width: 400px;
    `;

    notification.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i>
        <span>${message}</span>
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}

// Animations CSS
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);
