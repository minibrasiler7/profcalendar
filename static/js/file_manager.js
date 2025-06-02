// Variables globales
let selectedItems = [];
let uploadQueue = [];
let isUploading = false;

// Initialisation
document.addEventListener('DOMContentLoaded', function() {
    initDragAndDrop();
    initContextMenu();
    initKeyboardShortcuts();
    initDoubleClickHandler(); // Nouvelle fonction pour le double-clic
});

// Nouvelle fonction pour gérer le double-clic sur les fichiers
function initDoubleClickHandler() {
    const fileGrid = document.getElementById('fileGrid');

    if (fileGrid) {
        fileGrid.addEventListener('dblclick', (e) => {
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
    const previewUrl = `/files/preview/${fileId}`;
    window.open(previewUrl, '_blank');
}

// Fonction pour télécharger un fichier directement
function downloadFileDirectly(fileId) {
    const downloadUrl = `/files/download/${fileId}`;

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
        fileExplorer.addEventListener(eventName, () => {
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
function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;

    handleFiles(files);
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

            xhr.open('POST', '/files/upload');
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
        const response = await fetch('/files/create-folder', {
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
        const response = await fetch('/files/update-folder-color', {
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
        content.innerHTML = `<iframe src="/files/preview/${fileId}"></iframe>`;
    } else {
        content.innerHTML = `<img src="/files/preview/${fileId}" alt="Aperçu">`;
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
        const response = await fetch('/files/rename', {
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
        const response = await fetch(`/files/delete-file/${fileId}`, {
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
        const response = await fetch(`/files/delete-folder/${folderId}`, {
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

    fileGrid.addEventListener('contextmenu', (e) => {
        e.preventDefault();

        const item = e.target.closest('.file-item');
        if (item) {
            showContextMenu(e, item);
        }
    });

    // Fermer le menu en cliquant ailleurs
    document.addEventListener('click', () => {
        const menu = document.querySelector('.context-menu');
        if (menu) menu.remove();
    });
}

// Afficher le menu contextuel
function showContextMenu(e, item) {
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
            <a class="context-menu-item" href="/files/download/${id}">
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
    document.addEventListener('keydown', (e) => {
        // Escape pour fermer les modals
        if (e.key === 'Escape') {
            const modals = document.querySelectorAll('.modal.show');
            modals.forEach(modal => modal.classList.remove('show'));
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
