/**
 * UnifiedPDFViewer - Composant PDF unifié avec outils avancés
 * Version: 2.0.0
 * Auteur: TeacherPlanner
 * 
 * Fonctionnalités:
 * - Mode adaptatif (complet, prévisualisation, étudiant)
 * - Outils d'annotation avancés
 * - Recherche de texte
 * - Navigation optimisée
 * - Sauvegarde automatique
 * - Interface moderne et responsive
 */

class UnifiedPDFViewer {
    constructor(containerId, options = {}) {
        // Configuration par mode d'utilisation
        this.modes = {
            'teacher': {
                name: 'Mode Enseignant',
                annotations: true,
                tools: ['pen', 'highlighter', 'eraser', 'ruler', 'compass', 'protractor', 'arc', 'text', 'arrow', 'rectangle', 'circle', 'grid'],
                features: ['search', 'thumbnails', 'ruler', 'laser', 'present'],
                colors: ['#000000', '#EF4444', '#F59E0B', '#22C55E', '#3B82F6', '#8B5CF6', '#EC4899'],
                permissions: ['save', 'export', 'share']
            },
            'student': {
                name: 'Mode Étudiant',
                annotations: true,
                tools: ['highlighter', 'text', 'grid'],
                features: ['search', 'thumbnails'],
                colors: ['#F59E0B', '#22C55E', '#3B82F6', '#EC4899'],
                permissions: ['save']
            },
            'preview': {
                name: 'Mode Aperçu',
                annotations: false,
                tools: [],
                features: ['search'],
                colors: [],
                permissions: []
            }
        };

        // Options par défaut
        this.options = {
            mode: 'teacher',
            enableKeyboardShortcuts: true,
            enableTouchGestures: true,
            autoSave: true,
            saveDelay: 3000,
            maxZoom: 3.0,
            minZoom: 0.5,
            zoomStep: 0.25,
            viewMode: 'continuous', // 'single' ou 'continuous'
            pageSpacing: 20, // Espacement entre les pages en mode continu
            apiEndpoints: {
                saveAnnotations: '/api/save-annotations',
                loadAnnotations: '/api/load-annotations',
                search: '/api/search-pdf'
            },
            debug: false,
            language: 'fr',
            ...options
        };

        // Configuration du mode
        this.currentMode = this.modes[this.options.mode] || this.modes.teacher;
        
        // Initialisation des propriétés
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        if (!this.container) {
            throw new Error(`Container "${containerId}" non trouvé`);
        }

        // État PDF
        this.pdfDoc = null;
        this.currentPage = 1;
        this.totalPages = 0;
        this.currentScale = 1.5; // Augmenter l'échelle par défaut de 1.0 à 1.5 (50% plus large)
        this.rotation = 0;
        this.isLoading = false;
        this.fileId = null;
        this.fileName = '';
        this.pages = new Map(); // Stockage des pages rendues
        this.pageElements = new Map(); // Éléments DOM des pages

        // État annotations
        this.annotations = new Map(); // page -> annotations[]
        this.currentTool = this.currentMode.tools[0] || 'pen';
        this.currentColor = this.currentMode.colors[0] || '#000000';
        this.currentLineWidth = 2;
        this.isDrawing = false;
        this.lastPoint = null;
        this.undoStack = new Map(); // page -> undo operations[]
        this.redoStack = new Map();

        // Fonctionnalité ligne droite automatique (style iPad)
        this.straightLineTimer = null;
        this.straightLineTimeout = 2000; // 2 secondes par défaut
        this.drawingPath = []; // Points du trait en cours
        this.startPoint = null; // Point de départ pour la ligne droite
        this.isStabilized = false; // Flag pour éviter les multiples conversions
        this.currentStrokeImageData = null; // Sauvegarde du canvas avant le trait actuel
        
        // Variables pour l'outil rapporteur
        this.protractorState = 'initial'; // 'initial', 'drawing_first_line', 'waiting_validation', 'drawing_second_line'
        this.protractorCenterPoint = null;
        this.protractorFirstPoint = null;
        this.protractorSecondPoint = null;
        this.protractorValidationTimer = null;
        this.protractorValidationTimeout = 1500; // 1.5 secondes
        this.protractorCanvasState = null;
        this.protractorAngleElement = null;
        // Aimantation aux angles entiers
        this.protractorSnapToInteger = true; // Activer l'aimantation par défaut
        this.protractorSnapTolerance = 2; // Tolérance d'aimantation en degrés
        this.protractorSnappedPoint = null; // Point corrigé par l'aimantation

        // Outil règle
        this.rulerStartPoint = null; // Point de départ de la règle
        this.rulerCurrentPoint = null; // Point actuel de la règle
        this.rulerMeasureElement = null; // Élément d'affichage de la mesure
        this.rulerCanvasState = null; // Sauvegarde du canvas pour la prévisualisation
        this.a4PixelsPerCm = 28.35; // Pixels par cm pour A4 à 72 DPI (approximation)

        // Outil compas
        this.compassCenterPoint = null; // Point central du compas
        this.compassCurrentPoint = null; // Point actuel du compas
        this.compassRadiusElement = null; // Élément d'affichage du rayon
        this.compassCanvasState = null; // Sauvegarde du canvas pour la prévisualisation

        // Outil arc de cercle
        this.arcState = 'initial'; // 'initial', 'drawing_radius', 'waiting_validation', 'drawing_arc'
        this.arcCenterPoint = null; // Point central de l'arc
        this.arcRadiusPoint = null; // Point définissant le rayon
        this.arcEndPoint = null; // Point de fin de l'arc
        this.arcValidationTimer = null;
        this.arcValidationTimeout = 1500; // 1.5 secondes comme le rapporteur
        this.arcCanvasState = null; // Sauvegarde du canvas
        this.arcRadiusElement = null; // Élément d'affichage du rayon pendant le tracé
        this.arcAngleElement = null; // Élément d'affichage de l'angle pendant le tracé
        // Aimantation aux angles entiers pour l'arc
        this.arcSnapToInteger = true; // Activer l'aimantation par défaut
        this.arcSnapTolerance = 2; // Tolérance d'aimantation en degrés
        this.arcSnappedEndPoint = null; // Point corrigé par l'aimantation

        // Menu contextuel miniatures
        this.currentContextMenu = null;
        this.contextMenuPageNumber = null;

        // Outil flèche
        this.arrowStartPoint = null; // Point de départ de la flèche
        this.arrowEndPoint = null; // Point d'arrivée de la flèche
        this.arrowCanvasState = null; // Sauvegarde du canvas pour la prévisualisation
        this.arrowLengthElement = null; // Élément d'affichage de la longueur

        // Outil rectangle
        this.rectangleStartPoint = null; // Point de départ du rectangle
        this.rectangleEndPoint = null; // Point d'arrivée du rectangle
        this.rectangleCanvasState = null; // Sauvegarde du canvas pour la prévisualisation
        this.rectangleMeasureElement = null; // Élément d'affichage des dimensions

        // Outil cercle
        this.circleStartPoint = null; // Point de départ du cercle (centre)
        this.circleEndPoint = null; // Point d'arrivée du cercle (définit le rayon)
        this.circleCanvasState = null; // Sauvegarde du canvas pour la prévisualisation
        this.circleMeasureElement = null; // Élément d'affichage du rayon

        // Outil grille
        this.gridSize = 20; // Taille de la grille en pixels (par défaut)
        this.gridVisible = new Map(); // page -> boolean - visibilité de la grille par page
        this.gridColor = '#CCCCCC'; // Couleur de la grille
        this.gridOpacity = 0.5; // Opacité de la grille

        // État interface
        this.isFullscreen = false;
        this.showSidebar = true;
        this.showToolbar = true;
        this.searchResults = [];
        this.currentSearchIndex = -1;

        // Événements
        this.eventListeners = new Map();
        this.saveTimeout = null;

        // Initialisation
        this.init();
    }

    /**
     * Initialisation du composant
     */
    init() {
        this.log('Initialisation du PDF Viewer en mode:', this.options.mode);
        
        // Créer l'interface
        this.createInterface();
        
        // Initialiser les événements
        this.initEventListeners();
        
        // Raccourcis clavier
        if (this.options.enableKeyboardShortcuts) {
            this.initKeyboardShortcuts();
        }

        // Gestes tactiles
        if (this.options.enableTouchGestures) {
            this.initTouchGestures();
        }

        this.log('PDF Viewer initialisé avec succès');
    }

    /**
     * Création de l'interface utilisateur
     */
    createInterface() {
        this.container.innerHTML = `
            <div class="unified-pdf-viewer" data-mode="${this.options.mode}">
                <!-- Barre d'outils principale -->
                <div class="pdf-toolbar" id="pdf-toolbar">
                    ${this.createToolbar()}
                </div>
                
                <!-- Corps principal -->
                <div class="pdf-main">
                    <!-- Barre latérale -->
                    <div class="pdf-sidebar" id="pdf-sidebar" ${!this.showSidebar ? 'style="display: none;"' : ''}>
                        ${this.createSidebar()}
                    </div>
                    
                    <!-- Zone de visualisation -->
                    <div class="pdf-viewer-area">
                        <!-- Barre d'outils d'annotation -->
                        ${this.currentMode.annotations ? `<div class="pdf-annotation-toolbar">${this.createAnnotationToolbar()}</div>` : ''}
                        
                        <!-- Conteneur PDF -->
                        <div class="pdf-container" id="pdf-container">
                            <div class="pdf-loading" id="pdf-loading">
                                <div class="spinner"></div>
                                <p>Chargement du PDF...</p>
                            </div>
                            <div class="pdf-pages-container" id="pdf-pages-container">
                                <!-- Les pages seront générées dynamiquement ici -->
                            </div>
                        </div>
                        
                        <!-- Contrôles de navigation -->
                        <div class="pdf-nav-controls">
                            ${this.createNavigationControls()}
                        </div>
                    </div>
                </div>
                
                <!-- Boîtes de dialogue -->
                ${this.createDialogs()}
                
                <!-- Curseur personnalisé pour la gomme -->
                <div class="eraser-cursor" id="eraser-cursor"></div>
            </div>
        `;

        // Initialiser les références DOM
        this.initDOMReferences();
        
        // Configurer le mode d'affichage initial
        this.setupViewMode();
        
        // Activer l'outil par défaut si les annotations sont disponibles
        if (this.currentMode.annotations && this.currentTool) {
            setTimeout(() => {
                this.setCurrentTool(this.currentTool);
                this.log(`Outil par défaut activé: ${this.currentTool}`);
            }, 100);
        }
    }

    /**
     * Configuration du mode d'affichage
     */
    setupViewMode() {
        if (this.options.viewMode === 'continuous') {
            this.elements.container?.classList.add('continuous-view');
        } else {
            this.elements.container?.classList.add('single-view');
        }
    }

    /**
     * Création de la barre d'outils principale
     */
    createToolbar() {
        const tools = [];
        
        // Outils de fichier
        tools.push(`
            <div class="toolbar-group">
                <button class="btn-tool" id="btn-open-file" title="Ouvrir un fichier">
                    <i class="fas fa-folder-open"></i>
                </button>
                ${this.currentMode.permissions.includes('save') ? `
                    <button class="btn-tool" id="btn-save" title="Sauvegarder">
                        <i class="fas fa-save"></i>
                    </button>
                ` : ''}
                ${this.currentMode.permissions.includes('export') ? `
                    <button class="btn-tool" id="btn-export" title="Exporter">
                        <i class="fas fa-download"></i>
                    </button>
                ` : ''}
            </div>
        `);

        // Outils de navigation
        tools.push(`
            <div class="toolbar-group">
                <button class="btn-tool" id="btn-prev-page" title="Page précédente">
                    <i class="fas fa-chevron-left"></i>
                </button>
                <span class="page-info">
                    <input type="number" id="current-page-input" min="1" value="1" title="Page actuelle"> 
                    / <span id="total-pages">0</span>
                </span>
                <button class="btn-tool" id="btn-next-page" title="Page suivante">
                    <i class="fas fa-chevron-right"></i>
                </button>
            </div>
        `);

        // Outils de zoom et vue
        tools.push(`
            <div class="toolbar-group">
                <button class="btn-tool" id="btn-zoom-out" title="Zoom arrière">
                    <i class="fas fa-search-minus"></i>
                </button>
                <select id="zoom-select" title="Niveau de zoom">
                    <option value="fit-width">Ajuster largeur</option>
                    <option value="fit-page">Ajuster page</option>
                    <option value="0.5">50%</option>
                    <option value="0.75">75%</option>
                    <option value="1">100%</option>
                    <option value="1.25">125%</option>
                    <option value="1.5" selected>150%</option>
                    <option value="2">200%</option>
                    <option value="3">300%</option>
                </select>
                <button class="btn-tool" id="btn-zoom-in" title="Zoom avant">
                    <i class="fas fa-search-plus"></i>
                </button>
                <button class="btn-tool ${this.options.viewMode === 'continuous' ? 'active' : ''}" id="btn-view-mode" title="Basculer mode d'affichage">
                    <i class="fas ${this.options.viewMode === 'continuous' ? 'fa-list' : 'fa-square'}"></i>
                </button>
            </div>
        `);

        // Outils de présentation
        if (this.currentMode.features.includes('present')) {
            tools.push(`
                <div class="toolbar-group">
                    <button class="btn-tool" id="btn-rotate-left" title="Rotation gauche">
                        <i class="fas fa-undo"></i>
                    </button>
                    <button class="btn-tool" id="btn-rotate-right" title="Rotation droite">
                        <i class="fas fa-redo"></i>
                    </button>
                    <button class="btn-tool" id="btn-fullscreen" title="Plein écran">
                        <i class="fas fa-expand"></i>
                    </button>
                </div>
            `);
        }

        // Outils de recherche
        if (this.currentMode.features.includes('search')) {
            tools.push(`
                <div class="toolbar-group search-group">
                    <input type="text" id="search-input" placeholder="Rechercher dans le document...">
                    <button class="btn-tool" id="btn-search" title="Rechercher">
                        <i class="fas fa-search"></i>
                    </button>
                    <button class="btn-tool" id="btn-search-prev" title="Résultat précédent" disabled>
                        <i class="fas fa-chevron-up"></i>
                    </button>
                    <button class="btn-tool" id="btn-search-next" title="Résultat suivant" disabled>
                        <i class="fas fa-chevron-down"></i>
                    </button>
                    <span class="search-info" id="search-info"></span>
                </div>
            `);
        }

        return tools.join('');
    }

    /**
     * Création de la barre latérale
     */
    createSidebar() {
        const tabs = [];

        let isFirstTab = true;
        
        // Onglet miniatures
        if (this.currentMode.features.includes('thumbnails')) {
            tabs.push(`
                <div class="sidebar-tab${isFirstTab ? ' active' : ''}" data-tab="thumbnails">
                    <i class="fas fa-th"></i> Pages
                </div>
            `);
            isFirstTab = false;
        }

        // Onglet annotations
        if (this.currentMode.annotations) {
            tabs.push(`
                <div class="sidebar-tab${isFirstTab ? ' active' : ''}" data-tab="annotations">
                    <i class="fas fa-sticky-note"></i> Annotations
                </div>
            `);
            isFirstTab = false;
        }

        // Onglet recherche
        if (this.currentMode.features.includes('search')) {
            tabs.push(`
                <div class="sidebar-tab${isFirstTab ? ' active' : ''}" data-tab="search">
                    <i class="fas fa-search"></i> Recherche
                </div>
            `);
            isFirstTab = false;
        }

        const firstPanelActive = this.currentMode.features.includes('thumbnails') ? 'thumbnails' : 
                                this.currentMode.annotations ? 'annotations' : 'search';

        return `
            <div class="sidebar-tabs">
                ${tabs.join('')}
            </div>
            <div class="sidebar-content">
                <div class="sidebar-panel${firstPanelActive === 'thumbnails' ? ' active' : ''}" id="thumbnails-panel">
                    <div class="thumbnails-container" id="thumbnails-container">
                        <!-- Miniatures générées dynamiquement -->
                    </div>
                </div>
                <div class="sidebar-panel${firstPanelActive === 'annotations' ? ' active' : ''}" id="annotations-panel">
                    <div class="annotations-list" id="annotations-list">
                        <!-- Liste d'annotations -->
                    </div>
                </div>
                <div class="sidebar-panel${firstPanelActive === 'search' ? ' active' : ''}" id="search-panel">
                    <div class="search-results" id="search-results">
                        <!-- Résultats de recherche -->
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Création de la barre d'outils d'annotation
     */
    createAnnotationToolbar() {
        if (!this.currentMode.annotations) return '';

        const tools = [];

        // Outils de dessin
        this.currentMode.tools.forEach(tool => {
            const icons = {
                'pen': 'fa-pen',
                'highlighter': 'fa-highlighter',
                'eraser': 'fa-eraser',
                'ruler': 'fa-ruler',
                'compass': 'fa-circle-dot',
                'protractor': 'fa-angle-right',
                'arc': 'fa-circle-notch',
                'text': 'fa-font',
                'arrow': 'fa-arrow-right',
                'rectangle': 'fa-square',
                'circle': 'fa-circle',
                'grid': 'fa-th'
            };

            const names = {
                'pen': 'Stylo',
                'highlighter': 'Surligneur',
                'eraser': 'Gomme',
                'ruler': 'Règle',
                'compass': 'Compas',
                'protractor': 'Rapporteur',
                'arc': 'Arc',
                'text': 'Texte',
                'arrow': 'Flèche',
                'rectangle': 'Rectangle',
                'circle': 'Cercle',
                'grid': 'Grille'
            };

            tools.push(`
                <button class="btn-annotation-tool ${tool === this.currentTool ? 'active' : ''}" 
                        data-tool="${tool}" title="${names[tool]}">
                    <i class="fas ${icons[tool]}"></i>
                </button>
            `);
        });

        // Palette de couleurs
        const colorPalette = this.currentMode.colors.map(color => 
            `<button class="color-btn ${color === this.currentColor ? 'active' : ''}" 
                     data-color="${color}" 
                     style="background-color: ${color}" 
                     title="Couleur ${color}"></button>`
        ).join('');

        // Épaisseur du trait
        const strokeWidths = [1, 2, 3, 5, 8].map(width => 
            `<button class="stroke-btn ${width === this.currentLineWidth ? 'active' : ''}" 
                     data-width="${width}" title="Épaisseur ${width}px">
                <div class="stroke-preview" style="height: ${width}px;"></div>
             </button>`
        ).join('');

        return `
            <div class="annotation-tools">
                ${tools.join('')}
            </div>
            <div class="color-palette">
                ${colorPalette}
            </div>
            <div class="stroke-options">
                ${strokeWidths}
            </div>
            <div class="annotation-actions">
                <button class="btn-tool" id="btn-undo" title="Annuler">
                    <i class="fas fa-undo"></i>
                </button>
                <button class="btn-tool" id="btn-redo" title="Refaire">
                    <i class="fas fa-redo"></i>
                </button>
                <button class="btn-tool" id="btn-clear-page" title="Effacer la page">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;
    }

    /**
     * Création des contrôles de navigation
     */
    createNavigationControls() {
        return `
            <div class="nav-left">
                <button class="btn-nav" id="btn-nav-prev" title="Page précédente">
                    <i class="fas fa-chevron-left"></i>
                </button>
            </div>
            <div class="nav-center">
                <span class="page-indicator" id="page-indicator">1 / 1</span>
            </div>
            <div class="nav-right">
                <button class="btn-nav" id="btn-nav-next" title="Page suivante">
                    <i class="fas fa-chevron-right"></i>
                </button>
            </div>
        `;
    }

    /**
     * Création des boîtes de dialogue
     */
    createDialogs() {
        return `
            <!-- Dialog de recherche avancée -->
            <div class="dialog" id="search-dialog">
                <div class="dialog-content">
                    <h3>Recherche avancée</h3>
                    <div class="search-options">
                        <label><input type="checkbox" id="search-case-sensitive"> Sensible à la casse</label>
                        <label><input type="checkbox" id="search-whole-words"> Mots entiers uniquement</label>
                        <label><input type="checkbox" id="search-regex"> Expression régulière</label>
                    </div>
                    <div class="dialog-actions">
                        <button class="btn-secondary" id="btn-search-cancel">Annuler</button>
                        <button class="btn-primary" id="btn-search-start">Rechercher</button>
                    </div>
                </div>
            </div>

            <!-- Dialog d'export -->
            <div class="dialog" id="export-dialog">
                <div class="dialog-content">
                    <h3>Exporter le document</h3>
                    <div class="export-options">
                        <label><input type="radio" name="export-type" value="pdf" checked> PDF avec annotations</label>
                        <label><input type="radio" name="export-type" value="images"> Images (PNG)</label>
                        <label><input type="radio" name="export-type" value="annotations"> Annotations uniquement</label>
                    </div>
                    <div class="page-range">
                        <label>Pages :</label>
                        <label><input type="radio" name="page-range" value="all" checked> Toutes</label>
                        <label><input type="radio" name="page-range" value="current"> Page actuelle</label>
                        <label><input type="radio" name="page-range" value="range"> Plage : 
                            <input type="text" id="page-range-input" placeholder="ex: 1-5, 8, 10-12">
                        </label>
                    </div>
                    <div class="dialog-actions">
                        <button class="btn-secondary" id="btn-export-cancel">Annuler</button>
                        <button class="btn-primary" id="btn-export-start">Exporter</button>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Initialisation des références DOM
     */
    initDOMReferences() {
        this.elements = {
            container: document.getElementById('pdf-container'),
            pagesContainer: document.getElementById('pdf-pages-container'),
            loading: document.getElementById('pdf-loading'),
            toolbar: document.getElementById('pdf-toolbar'),
            sidebar: document.getElementById('pdf-sidebar'),
            
            // Navigation
            prevPage: document.getElementById('btn-prev-page'),
            nextPage: document.getElementById('btn-next-page'),
            currentPageInput: document.getElementById('current-page-input'),
            totalPages: document.getElementById('total-pages'),
            pageIndicator: document.getElementById('page-indicator'),
            
            // Zoom et mode d'affichage
            zoomSelect: document.getElementById('zoom-select'),
            zoomIn: document.getElementById('btn-zoom-in'),
            zoomOut: document.getElementById('btn-zoom-out'),
            viewModeBtn: document.getElementById('btn-view-mode'),
            
            // Recherche
            searchInput: document.getElementById('search-input'),
            searchBtn: document.getElementById('btn-search'),
            searchPrev: document.getElementById('btn-search-prev'),
            searchNext: document.getElementById('btn-search-next'),
            searchInfo: document.getElementById('search-info'),
            
            // Miniatures
            thumbnailsContainer: document.getElementById('thumbnails-container'),
            
            // Annotations
            annotationsList: document.getElementById('annotations-list'),
            
            // Curseur personnalisé
            eraserCursor: document.getElementById('eraser-cursor')
        };

        // Les canvas seront créés dynamiquement pour chaque page en mode continu
    }

    /**
     * Chargement d'un fichier PDF
     */
    async loadPDF(url, fileId = null) {
        try {
            this.showLoading(true);
            this.fileId = fileId;
            this.fileName = url.split('/').pop();
            
            this.log('Chargement du PDF:', url);

            // Configuration de PDF.js
            const loadingTask = pdfjsLib.getDocument({
                url: url,
                cMapUrl: 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/cmaps/',
                cMapPacked: true
            });

            this.pdfDoc = await loadingTask.promise;
            this.totalPages = this.pdfDoc.numPages;
            
            this.log(`PDF chargé: ${this.totalPages} pages`);

            // Mettre à jour l'interface
            this.updatePageInfo();
            
            // Initialiser le rendu selon le mode
            if (this.options.viewMode === 'continuous') {
                await this.renderAllPages();
            } else {
                await this.renderPage(1);
            }
            
            // Ajuster automatiquement à la largeur si souhaité
            // Décommentez la ligne suivante pour ajuster automatiquement à la largeur
            // this.fitToWidth();
            
            // Générer les miniatures avec un délai pour éviter les conflits
            if (this.currentMode.features.includes('thumbnails')) {
                setTimeout(() => {
                    this.generateThumbnails();
                }, 500);
            }
            
            // Charger les annotations existantes
            if (this.currentMode.annotations && this.fileId) {
                await this.loadAnnotations();
            }

            this.showLoading(false);
            
            // Activer l'outil par défaut (stylo) après le chargement du PDF
            if (this.currentMode.annotations) {
                this.setCurrentTool('pen');
                this.log('✏️ Stylo activé par défaut après chargement du PDF');
            }
            
            this.emit('pdf-loaded', { totalPages: this.totalPages, fileName: this.fileName });
            
        } catch (error) {
            this.showLoading(false);
            this.showError('Erreur lors du chargement du PDF: ' + error.message);
            this.log('Erreur chargement PDF:', error);
        }
    }

    /**
     * Rendu de toutes les pages en mode continu
     */
    async renderAllPages() {
        if (!this.pdfDoc) return;

        this.log('Rendu de toutes les pages en mode continu');
        
        // Vider le conteneur
        this.elements.pagesContainer.innerHTML = '';
        this.pageElements.clear();

        // Créer et rendre chaque page
        for (let pageNum = 1; pageNum <= this.totalPages; pageNum++) {
            await this.createPageElement(pageNum);
        }

        // Configurer la détection de page visible
        this.setupPageVisibilityObserver();
        
        // Initialiser l'historique undo/redo avec un état vide pour chaque page
        this.initializeUndoHistory();
        
        this.log('Toutes les pages rendues');
        this.log(`Pages stockées dans pageElements:`, Array.from(this.pageElements.keys()));
        this.log(`Dernière page créée:`, this.pageElements.get(this.totalPages));
        
        // Debug: Vérifier la hauteur totale du conteneur
        setTimeout(() => {
            const container = this.elements.pagesContainer;
            if (container) {
                this.log('Hauteur du conteneur des pages:', container.scrollHeight);
                this.log('Nombre d\'éléments pages dans le DOM:', container.children.length);
                this.log('Position de la dernière page:', container.lastElementChild?.offsetTop);
            }
        }, 1000);
    }

    /**
     * Création d'un élément de page
     */
    async createPageElement(pageNum) {
        try {
            const page = await this.pdfDoc.getPage(pageNum);
            const viewport = page.getViewport({ 
                scale: this.currentScale, 
                rotation: this.rotation 
            });

            // Créer le conteneur de la page
            const pageContainer = document.createElement('div');
            pageContainer.className = 'pdf-page-container';
            pageContainer.dataset.pageNumber = pageNum;
            pageContainer.style.marginBottom = `${this.options.pageSpacing}px`;

            // Créer le canvas principal
            const canvas = document.createElement('canvas');
            canvas.className = 'pdf-canvas';
            canvas.width = viewport.width;
            canvas.height = viewport.height;
            canvas.dataset.pageNumber = pageNum;

            // Créer le canvas d'annotation si nécessaire
            let annotationCanvas = null;
            if (this.currentMode.annotations) {
                annotationCanvas = document.createElement('canvas');
                annotationCanvas.className = 'pdf-annotation-layer';
                annotationCanvas.width = viewport.width;
                annotationCanvas.height = viewport.height;
                annotationCanvas.dataset.pageNumber = pageNum;
                annotationCanvas.style.position = 'absolute';
                annotationCanvas.style.top = '0';
                annotationCanvas.style.left = '0';
                annotationCanvas.style.pointerEvents = 'none';
            }

            // Ajouter un indicateur de page
            const pageIndicator = document.createElement('div');
            pageIndicator.className = 'page-number-indicator';
            pageIndicator.textContent = pageNum;

            // Assembler le conteneur
            pageContainer.style.position = 'relative';
            pageContainer.appendChild(canvas);
            if (annotationCanvas) {
                pageContainer.appendChild(annotationCanvas);
            }
            pageContainer.appendChild(pageIndicator);

            // Ajouter au conteneur principal
            this.elements.pagesContainer.appendChild(pageContainer);

            // Stocker les références
            this.pageElements.set(pageNum, {
                container: pageContainer,
                canvas: canvas,
                annotationCanvas: annotationCanvas,
                ctx: canvas.getContext('2d'),
                annotationCtx: annotationCanvas?.getContext('2d'),
                viewport: viewport
            });

            // Rendre la page PDF
            const ctx = canvas.getContext('2d');
            await page.render({ canvasContext: ctx, viewport }).promise;

            // Rendre les annotations
            if (this.currentMode.annotations && annotationCanvas) {
                this.renderPageAnnotations(pageNum);
            }

            // Configurer les événements d'annotation pour cette page
            if (this.currentMode.annotations && annotationCanvas) {
                this.setupPageAnnotationEvents(pageNum, annotationCanvas);
            }

            this.log(`Page ${pageNum} créée et rendue`);

        } catch (error) {
            this.log('Erreur création page', pageNum, error);
        }
    }

    /**
     * Rendu d'une page (mode page unique)
     */
    async renderPage(pageNum) {
        if (!this.pdfDoc || pageNum < 1 || pageNum > this.totalPages) {
            return;
        }

        if (this.options.viewMode === 'continuous') {
            // En mode continu, juste scroller vers la page
            this.scrollToPage(pageNum);
            return;
        }

        try {
            this.currentPage = pageNum;
            this.log(`Rendu de la page ${pageNum}`);

            // Vider le conteneur et créer une seule page
            this.elements.pagesContainer.innerHTML = '';
            await this.createPageElement(pageNum);
            
            // Initialiser l'historique pour cette page
            this.initializeUndoHistory();

            // Mettre à jour l'interface
            this.updatePageInfo();
            this.updateNavigationState();

            this.emit('page-rendered', { pageNum });

        } catch (error) {
            this.showError('Erreur lors du rendu de la page: ' + error.message);
            this.log('Erreur rendu page:', error);
        }
    }

    /**
     * Scroll vers une page spécifique en mode continu
     */
    scrollToPage(pageNum) {
        const pageElement = this.pageElements.get(pageNum);
        this.log(`Tentative scroll vers page ${pageNum}, élément trouvé:`, !!pageElement);
        
        if (pageElement && pageElement.container) {
            this.log(`Scroll vers page ${pageNum} - Container:`, pageElement.container);
            this.log(`OffsetTop de la page ${pageNum}:`, pageElement.container.offsetTop);
            
            // Vérifier si l'élément est bien dans le DOM
            if (!document.contains(pageElement.container)) {
                this.log(`ERREUR: La page ${pageNum} n'est pas dans le DOM!`);
                return;
            }
            
            // Méthode 1: Scroll direct vers la position
            const targetScrollTop = pageElement.container.offsetTop - 20; // Petit offset
            this.log(`Scroll vers position:`, targetScrollTop);
            
            this.elements.container.scrollTo({
                top: targetScrollTop,
                behavior: 'smooth'
            });
            
            this.currentPage = pageNum;
            this.updatePageInfo();
        } else {
            this.log(`Impossible de scroller vers page ${pageNum} - élément non trouvé`);
        }
    }

    /**
     * Configuration de l'observateur de visibilité des pages
     */
    setupPageVisibilityObserver() {
        if (!('IntersectionObserver' in window)) return;

        const observer = new IntersectionObserver((entries) => {
            let mostVisiblePage = null;
            let maxVisibility = 0;

            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const pageNum = parseInt(entry.target.dataset.pageNumber);
                    const visibility = entry.intersectionRatio;
                    
                    if (visibility > maxVisibility) {
                        maxVisibility = visibility;
                        mostVisiblePage = pageNum;
                    }
                }
            });

            if (mostVisiblePage && mostVisiblePage !== this.currentPage) {
                this.currentPage = mostVisiblePage;
                this.updatePageInfo();
                this.updateThumbnailSelection();
            }
        }, {
            root: null, // Utiliser le viewport par défaut
            threshold: [0.1, 0.5, 0.9]
        });

        // Observer toutes les pages
        this.pageElements.forEach((element, pageNum) => {
            observer.observe(element.container);
        });

        this.pageObserver = observer;
    }

    /**
     * Gestion des événements
     */
    initEventListeners() {
        // Navigation
        this.elements.prevPage?.addEventListener('click', () => this.previousPage());
        this.elements.nextPage?.addEventListener('click', () => this.nextPage());
        this.elements.currentPageInput?.addEventListener('change', (e) => {
            const pageNum = parseInt(e.target.value);
            if (pageNum >= 1 && pageNum <= this.totalPages) {
                this.goToPage(pageNum);
            }
        });

        // Zoom
        this.elements.zoomSelect?.addEventListener('change', (e) => this.setZoom(e.target.value));
        this.elements.zoomIn?.addEventListener('click', () => this.zoomIn());
        this.elements.zoomOut?.addEventListener('click', () => this.zoomOut());

        // Recherche
        this.elements.searchBtn?.addEventListener('click', () => this.search());
        this.elements.searchInput?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') this.search();
        });
        this.elements.searchPrev?.addEventListener('click', () => this.searchPrevious());
        this.elements.searchNext?.addEventListener('click', () => this.searchNext());

        // Annotations (si disponibles)
        if (this.currentMode.annotations) {
            this.initAnnotationEvents();
        }

        // Redimensionnement
        window.addEventListener('resize', () => this.handleResize());

        // Boutons supplémentaires si disponibles
        document.getElementById('btn-open-file')?.addEventListener('click', () => this.openFileDialog());
        document.getElementById('btn-save')?.addEventListener('click', () => this.saveAnnotations());
        document.getElementById('btn-export')?.addEventListener('click', () => this.showExportDialog());
        document.getElementById('btn-rotate-left')?.addEventListener('click', () => this.rotateLeft());
        document.getElementById('btn-rotate-right')?.addEventListener('click', () => this.rotateRight());
        document.getElementById('btn-fullscreen')?.addEventListener('click', () => this.toggleFullscreen());
        
        // Bouton de basculement de mode d'affichage
        this.elements.viewModeBtn?.addEventListener('click', () => this.toggleViewMode());

        // Navigation des boutons du bas
        document.getElementById('btn-nav-prev')?.addEventListener('click', () => this.previousPage());
        document.getElementById('btn-nav-next')?.addEventListener('click', () => this.nextPage());
        
        // Gestion des onglets de la sidebar
        document.querySelectorAll('.sidebar-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                const tabName = e.currentTarget.dataset.tab;
                this.activateSidebarTab(tabName);
            });
        });
    }

    /**
     * Raccourcis clavier
     */
    initKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                return; // Ignorer si on écrit dans un champ
            }

            switch (e.key) {
                case 'ArrowLeft':
                case 'PageUp':
                    e.preventDefault();
                    this.previousPage();
                    break;
                case 'ArrowRight':
                case 'PageDown':
                    e.preventDefault();
                    this.nextPage();
                    break;
                case 'Home':
                    e.preventDefault();
                    this.goToPage(1);
                    break;
                case 'End':
                    e.preventDefault();
                    this.goToPage(this.totalPages);
                    break;
                case '+':
                    if (e.ctrlKey || e.metaKey) {
                        e.preventDefault();
                        this.zoomIn();
                    }
                    break;
                case '-':
                    if (e.ctrlKey || e.metaKey) {
                        e.preventDefault();
                        this.zoomOut();
                    }
                    break;
                case 'f':
                    if (e.ctrlKey || e.metaKey) {
                        e.preventDefault();
                        this.elements.searchInput?.focus();
                    }
                    break;
                case 'F11':
                    e.preventDefault();
                    this.toggleFullscreen();
                    break;
                case 'v':
                    if (e.ctrlKey || e.metaKey) {
                        e.preventDefault();
                        this.toggleViewMode();
                    }
                    break;
                case 'z':
                    if (e.ctrlKey || e.metaKey) {
                        e.preventDefault();
                        if (e.shiftKey) {
                            this.redo(); // Ctrl+Shift+Z = Redo
                        } else {
                            this.undo(); // Ctrl+Z = Undo
                        }
                    }
                    break;
                case 'y':
                    if (e.ctrlKey || e.metaKey) {
                        e.preventDefault();
                        this.redo(); // Ctrl+Y = Redo
                    }
                    break;
            }
        });
    }

    // ... (Les autres méthodes seront dans la suite)

    /**
     * Utilitaires
     */
    log(...args) {
        if (this.options.debug) {
            console.log('[UnifiedPDFViewer]', ...args);
        }
    }

    emit(eventName, data = {}) {
        const event = new CustomEvent(eventName, { detail: data });
        this.container.dispatchEvent(event);
    }

    showLoading(show) {
        if (this.elements.loading) {
            this.elements.loading.style.display = show ? 'flex' : 'none';
        }
    }

    showError(message) {
        // Implémentation d'affichage d'erreur
        console.error('[UnifiedPDFViewer] Erreur:', message);
        // Ici on pourrait ajouter une notification toast
    }

    updatePageInfo() {
        if (this.elements.currentPageInput) {
            this.elements.currentPageInput.value = this.currentPage;
        }
        if (this.elements.totalPages) {
            this.elements.totalPages.textContent = this.totalPages;
        }
        if (this.elements.pageIndicator) {
            this.elements.pageIndicator.textContent = `${this.currentPage} / ${this.totalPages}`;
        }
        
        // Mettre à jour l'état des boutons undo/redo pour la page courante
        this.updateUndoRedoButtons();
    }

    updateNavigationState() {
        if (this.elements.prevPage) {
            this.elements.prevPage.disabled = this.currentPage <= 1;
        }
        if (this.elements.nextPage) {
            this.elements.nextPage.disabled = this.currentPage >= this.totalPages;
        }
    }

    // Navigation
    previousPage() {
        if (this.currentPage > 1) {
            this.renderPage(this.currentPage - 1);
        }
    }

    nextPage() {
        if (this.currentPage < this.totalPages) {
            this.renderPage(this.currentPage + 1);
        }
    }

    goToPage(pageNum) {
        if (pageNum >= 1 && pageNum <= this.totalPages && pageNum !== this.currentPage) {
            this.renderPage(pageNum);
        }
    }

    // Zoom
    zoomIn() {
        const newScale = Math.min(this.currentScale + this.options.zoomStep, this.options.maxZoom);
        this.setZoom(newScale);
    }

    zoomOut() {
        const newScale = Math.max(this.currentScale - this.options.zoomStep, this.options.minZoom);
        this.setZoom(newScale);
    }

    setZoom(value) {
        if (typeof value === 'string') {
            switch (value) {
                case 'fit-width':
                    this.fitToWidth();
                    return;
                case 'fit-page':
                    this.fitToPage();
                    return;
                default:
                    value = parseFloat(value);
            }
        }

        if (isNaN(value) || value < this.options.minZoom || value > this.options.maxZoom) {
            return;
        }

        this.currentScale = value;
        this.renderPage(this.currentPage);
        
        if (this.elements.zoomSelect) {
            this.elements.zoomSelect.value = value.toString();
        }
    }

    fitToWidth() {
        // Implémentation ajustement largeur
        const containerWidth = this.elements.container.clientWidth - 40; // padding
        if (this.pdfDoc && this.currentPage) {
            this.pdfDoc.getPage(this.currentPage).then(page => {
                const viewport = page.getViewport({ scale: 1 });
                const scale = containerWidth / viewport.width;
                this.setZoom(scale);
            });
        }
    }

    fitToPage() {
        // Implémentation ajustement page
        const containerWidth = this.elements.container.clientWidth - 40;
        const containerHeight = this.elements.container.clientHeight - 40;
        
        if (this.pdfDoc && this.currentPage) {
            this.pdfDoc.getPage(this.currentPage).then(page => {
                const viewport = page.getViewport({ scale: 1 });
                const scaleX = containerWidth / viewport.width;
                const scaleY = containerHeight / viewport.height;
                const scale = Math.min(scaleX, scaleY);
                this.setZoom(scale);
            });
        }
    }

    // Recherche
    async search(query = null) {
        // Implémentation de recherche sera ajoutée
        console.log('Recherche:', query || this.elements.searchInput?.value);
    }

    /**
     * Basculer entre mode continu et page unique
     */
    async toggleViewMode() {
        const newMode = this.options.viewMode === 'continuous' ? 'single' : 'continuous';
        this.log(`Basculement vers mode: ${newMode}`);
        
        // Sauvegarder la page actuelle
        const currentPageBeforeSwitch = this.currentPage;
        
        // Mettre à jour le mode
        this.options.viewMode = newMode;
        
        // Mettre à jour l'interface
        this.updateViewModeButton();
        
        // Détruire l'observateur existant si il existe
        if (this.pageObserver) {
            this.pageObserver.disconnect();
            this.pageObserver = null;
        }
        
        // Re-rendre selon le nouveau mode
        if (newMode === 'continuous') {
            await this.renderAllPages();
            // Scroller vers la page actuelle
            this.scrollToPage(currentPageBeforeSwitch);
        } else {
            await this.renderPage(currentPageBeforeSwitch);
        }
        
        this.emit('view-mode-changed', { mode: newMode, currentPage: currentPageBeforeSwitch });
    }
    
    /**
     * Mettre à jour le bouton de mode d'affichage
     */
    updateViewModeButton() {
        if (this.elements.viewModeBtn) {
            const isContinuous = this.options.viewMode === 'continuous';
            this.elements.viewModeBtn.classList.toggle('active', isContinuous);
            
            const icon = this.elements.viewModeBtn.querySelector('i');
            if (icon) {
                icon.className = isContinuous ? 'fas fa-list' : 'fas fa-square';
            }
            
            this.elements.viewModeBtn.title = isContinuous ? 'Mode page unique' : 'Mode continu';
        }
    }
    
    /**
     * Mettre à jour la sélection des miniatures
     */
    updateThumbnailSelection() {
        const thumbnails = document.querySelectorAll('.thumbnail-item');
        thumbnails.forEach(thumb => {
            const pageNum = parseInt(thumb.dataset.pageNumber);
            thumb.classList.toggle('active', pageNum === this.currentPage);
        });
    }
    
    /**
     * Activer un onglet de la sidebar
     */
    activateSidebarTab(tabName) {
        // Désactiver tous les onglets
        document.querySelectorAll('.sidebar-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        
        // Désactiver tous les panels
        document.querySelectorAll('.sidebar-panel').forEach(panel => {
            panel.classList.remove('active');
        });
        
        // Activer l'onglet et le panel correspondants
        const activeTab = document.querySelector(`.sidebar-tab[data-tab="${tabName}"]`);
        const activePanel = document.getElementById(`${tabName}-panel`);
        
        if (activeTab) activeTab.classList.add('active');
        if (activePanel) activePanel.classList.add('active');
        
        this.log(`Onglet activé: ${tabName}`);
    }

    // Méthodes publiques pour contrôle externe
    destroy() {
        // Nettoyage lors de la destruction
        if (this.saveTimeout) {
            clearTimeout(this.saveTimeout);
        }
        if (this.pageObserver) {
            this.pageObserver.disconnect();
        }
        this.eventListeners.clear();
    }

    // Gestion du redimensionnement
    handleResize() {
        // Ajuster si nécessaire lors du redimensionnement
        setTimeout(() => {
            if (this.elements.zoomSelect?.value === 'fit-width') {
                this.fitToWidth();
            } else if (this.elements.zoomSelect?.value === 'fit-page') {
                this.fitToPage();
            }
        }, 100);
    }

    /**
     * Initialisation des événements d'annotation
     */
    initAnnotationEvents() {
        // Sélecteurs d'outils
        document.querySelectorAll('.btn-annotation-tool').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const tool = e.currentTarget.dataset.tool;
                this.setCurrentTool(tool);
            });
        });

        // Palette de couleurs
        document.querySelectorAll('.color-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const color = e.currentTarget.dataset.color;
                this.setCurrentColor(color);
            });
        });

        // Épaisseur du trait
        document.querySelectorAll('.stroke-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const width = parseInt(e.currentTarget.dataset.width);
                this.setCurrentLineWidth(width);
            });
        });

        // Boutons Annuler/Refaire
        document.getElementById('btn-undo')?.addEventListener('click', () => this.undo());
        document.getElementById('btn-redo')?.addEventListener('click', () => this.redo());
        document.getElementById('btn-clear-page')?.addEventListener('click', () => this.clearCurrentPage());
    }
    
    /**
     * Configuration des événements d'annotation pour une page spécifique
     */
    setupPageAnnotationEvents(pageNum, annotationCanvas) {
        // Événements de dessin sur le canvas d'annotation
        annotationCanvas.addEventListener('mousedown', (e) => this.startDrawing(e, pageNum));
        annotationCanvas.addEventListener('mousemove', (e) => this.draw(e, pageNum));
        annotationCanvas.addEventListener('mouseup', (e) => this.stopDrawing(e, pageNum));
        annotationCanvas.addEventListener('mouseout', (e) => this.stopDrawing(e, pageNum));

        // Support tactile
        annotationCanvas.addEventListener('touchstart', (e) => {
            e.preventDefault();
            const touch = e.touches[0];
            const mouseEvent = new MouseEvent('mousedown', {
                clientX: touch.clientX,
                clientY: touch.clientY
            });
            this.startDrawing(mouseEvent, pageNum);
        });

        annotationCanvas.addEventListener('touchmove', (e) => {
            e.preventDefault();
            const touch = e.touches[0];
            const mouseEvent = new MouseEvent('mousemove', {
                clientX: touch.clientX,
                clientY: touch.clientY
            });
            this.draw(mouseEvent, pageNum);
        });

        annotationCanvas.addEventListener('touchend', (e) => {
            e.preventDefault();
            this.stopDrawing(null, pageNum);
        });
    }
    
    /**
     * Méthodes d'annotation de base
     */
    setCurrentTool(tool) {
        // Supprimer toute zone de texte active lors du changement d'outil
        if (this.currentTool === 'text' && tool !== 'text') {
            this.removeActiveTextInput();
        }
        
        this.currentTool = tool;
        document.querySelectorAll('.btn-annotation-tool').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tool === tool);
        });
        
        // Mettre à jour la palette de couleurs selon l'outil
        this.updateColorPalette(tool);
        
        // Ajuster l'épaisseur par défaut selon l'outil
        if (tool === 'highlighter' && this.currentLineWidth < 5) {
            this.setCurrentLineWidth(8); // Épaisseur plus importante pour le surligneur
        } else if (tool === 'pen' && this.currentLineWidth > 5) {
            this.setCurrentLineWidth(2); // Épaisseur normale pour le stylo
        }
        
        // Activer/désactiver les événements sur tous les canvas d'annotation
        const annotationCanvases = document.querySelectorAll('.pdf-annotation-layer');
        this.log(`Nombre de canvas d'annotation trouvés: ${annotationCanvases.length}`);
        
        annotationCanvases.forEach((canvas, index) => {
            if (tool) {
                canvas.style.pointerEvents = 'all';
                canvas.style.cursor = tool === 'pen' ? 'crosshair' : 
                                     tool === 'highlighter' ? 'crosshair' :
                                     tool === 'eraser' ? 'none' :
                                     tool === 'text' ? 'text' : 'default';
                this.log(`Canvas ${index} activé pour l'outil ${tool}`);
            } else {
                canvas.style.pointerEvents = 'none';
                canvas.style.cursor = 'default';
                this.log(`Canvas ${index} désactivé`);
            }
        });
        
        // Gestion du curseur personnalisé pour la gomme
        if (this.elements.eraserCursor) {
            if (tool === 'eraser') {
                this.elements.eraserCursor.style.display = 'block';
                this.updateEraserCursorSize();
                this.setupEraserCursorEvents();
            } else {
                this.elements.eraserCursor.style.display = 'none';
                this.removeEraserCursorEvents();
            }
        }
        
        this.log(`Outil sélectionné: ${tool}, canvases configurés: ${annotationCanvases.length}`);
    }
    
    /**
     * Met à jour la taille du curseur de la gomme
     */
    updateEraserCursorSize() {
        if (!this.elements.eraserCursor) return;
        
        const size = this.currentLineWidth * 8; // Taille plus proportionnelle
        this.elements.eraserCursor.style.width = `${size}px`;
        this.elements.eraserCursor.style.height = `${size}px`;
        // Centrage parfait avec transform au lieu de margin
        this.elements.eraserCursor.style.transform = `translate(-50%, -50%)`;
        
        this.log(`Taille curseur gomme mise à jour: ${size}px`);
    }
    
    /**
     * Configure les événements de suivi de souris pour le curseur de la gomme
     */
    setupEraserCursorEvents() {
        this.eraserMouseMoveHandler = (e) => {
            if (!this.elements.eraserCursor) return;
            
            // Positionnement par rapport à la fenêtre pour un alignement parfait
            this.elements.eraserCursor.style.left = `${e.clientX}px`;
            this.elements.eraserCursor.style.top = `${e.clientY}px`;
            this.elements.eraserCursor.style.opacity = '0.7';
        };
        
        this.eraserMouseLeaveHandler = () => {
            if (this.elements.eraserCursor) {
                this.elements.eraserCursor.style.opacity = '0';
            }
        };
        
        this.eraserMouseEnterHandler = () => {
            if (this.elements.eraserCursor) {
                this.elements.eraserCursor.style.opacity = '0.7';
            }
        };
        
        // Attacher les événements au document pour un suivi global
        document.addEventListener('mousemove', this.eraserMouseMoveHandler);
        
        // Attacher les événements aux canvas d'annotation pour la visibilité
        const annotationCanvases = document.querySelectorAll('.pdf-annotation-layer');
        annotationCanvases.forEach(canvas => {
            canvas.addEventListener('mouseenter', this.eraserMouseEnterHandler);
            canvas.addEventListener('mouseleave', this.eraserMouseLeaveHandler);
        });
        
        // Événement global pour masquer quand on sort complètement
        if (this.elements.container) {
            this.elements.container.addEventListener('mouseleave', this.eraserMouseLeaveHandler);
        }
        
        this.log('Événements curseur gomme configurés avec positionnement global');
    }
    
    /**
     * Supprime les événements de suivi de souris pour le curseur de la gomme
     */
    removeEraserCursorEvents() {
        // Supprimer l'événement global
        if (this.eraserMouseMoveHandler) {
            document.removeEventListener('mousemove', this.eraserMouseMoveHandler);
        }
        
        // Supprimer les événements des canvas
        const annotationCanvases = document.querySelectorAll('.pdf-annotation-layer');
        annotationCanvases.forEach(canvas => {
            if (this.eraserMouseEnterHandler) {
                canvas.removeEventListener('mouseenter', this.eraserMouseEnterHandler);
            }
            if (this.eraserMouseLeaveHandler) {
                canvas.removeEventListener('mouseleave', this.eraserMouseLeaveHandler);
            }
        });
        
        // Supprimer l'événement du conteneur
        if (this.elements.container && this.eraserMouseLeaveHandler) {
            this.elements.container.removeEventListener('mouseleave', this.eraserMouseLeaveHandler);
        }
        
        this.log('Événements curseur gomme supprimés');
    }
    
    /**
     * Met à jour la palette de couleurs selon l'outil sélectionné
     */
    updateColorPalette(tool) {
        const colorPalette = document.querySelector('.color-palette');
        if (!colorPalette) return;
        
        let colors;
        if (tool === 'highlighter') {
            // Couleurs fluos pour le surligneur
            colors = [
                '#FF004F', // Rose/magenta fluo
                '#FDFF00', // Jaune fluo
                '#66FF00', // Vert lime fluo
                '#00F3FF', // Cyan fluo
                '#9F00FF'  // Violet fluo
            ];
        } else {
            // Couleurs normales pour les autres outils
            colors = this.currentMode.colors;
        }
        
        // Reconstruire la palette de couleurs
        const colorButtons = colors.map(color => 
            `<button class="color-btn ${color === this.currentColor ? 'active' : ''}" 
                     data-color="${color}" 
                     style="background-color: ${color}" 
                     title="Couleur ${color}"></button>`
        ).join('');
        
        colorPalette.innerHTML = colorButtons;
        
        // Réattacher les événements
        colorPalette.querySelectorAll('.color-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const color = e.currentTarget.dataset.color;
                this.setCurrentColor(color);
            });
        });
        
        // Si la couleur actuelle n'est pas dans la nouvelle palette, prendre la première
        if (!colors.includes(this.currentColor)) {
            this.setCurrentColor(colors[0]);
        }
        
        this.log(`Palette de couleurs mise à jour pour l'outil: ${tool}`);
    }
    
    setCurrentColor(color) {
        this.currentColor = color;
        document.querySelectorAll('.color-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.color === color);
        });
    }
    
    setCurrentLineWidth(width) {
        this.currentLineWidth = width;
        document.querySelectorAll('.stroke-btn').forEach(btn => {
            btn.classList.toggle('active', parseInt(btn.dataset.width) === width);
        });
        
        // Mettre à jour la taille du curseur de la gomme si elle est active
        if (this.currentTool === 'eraser') {
            this.updateEraserCursorSize();
        }
    }
    
    startDrawing(e, pageNum) {
        if (!this.currentMode.annotations) {
            this.log('Annotations désactivées pour ce mode');
            return;
        }
        
        this.log(`Début du dessin sur page ${pageNum}, outil: ${this.currentTool}`);
        this.isDrawing = true;
        const rect = e.target.getBoundingClientRect();
        this.lastPoint = {
            x: e.clientX - rect.left,
            y: e.clientY - rect.top
        };
        
        this.log(`Point de départ: x=${this.lastPoint.x}, y=${this.lastPoint.y}`);
        
        // Ne pas sauvegarder ici - on sauvegarde après l'action complétée
        
        // Initialiser la fonctionnalité ligne droite pour le stylo
        if (this.currentTool === 'pen') {
            this.startPoint = { ...this.lastPoint };
            this.drawingPath = [{ ...this.lastPoint }];
            this.isStabilized = false;
            
            // Sauvegarder l'état du canvas avant de commencer le trait
            const pageElement = this.pageElements.get(pageNum);
            if (pageElement?.annotationCanvas) {
                const ctx = pageElement.annotationCtx;
                this.currentStrokeImageData = ctx.getImageData(0, 0, pageElement.annotationCanvas.width, pageElement.annotationCanvas.height);
                this.log('📸 État du canvas sauvegardé avant le trait');
            }
            
            // Démarrer le timer pour la ligne droite automatique
            this.straightLineTimer = setTimeout(() => {
                this.convertToStraightLine(pageNum);
            }, this.straightLineTimeout);
            
            this.log('Timer ligne droite démarré pour le stylo');
        }

        // Initialiser l'outil règle
        if (this.currentTool === 'ruler') {
            this.rulerStartPoint = { ...this.lastPoint };
            this.rulerCurrentPoint = { ...this.lastPoint };
            this.createRulerMeasureElement();
            this.log('📏 Outil règle initialisé');
        }

        // Initialiser l'outil compas
        if (this.currentTool === 'compass') {
            this.compassCenterPoint = { ...this.lastPoint };
            this.compassCurrentPoint = { ...this.lastPoint };
            this.createCompassRadiusElement();
            this.log('🧭 Outil compas initialisé');
        }

        // Initialiser l'outil rapporteur
        if (this.currentTool === 'protractor') {
            if (this.protractorState === 'initial') {
                // Premier clic : définir le centre de l'angle
                this.protractorCenterPoint = { ...this.lastPoint };
                this.protractorFirstPoint = { ...this.lastPoint };
                this.protractorState = 'drawing_first_line';
                this.createProtractorAngleElement();
                this.log('📐 Outil rapporteur initialisé - centre défini');
            }
        }

        // Initialiser l'outil arc de cercle
        if (this.currentTool === 'arc') {
            if (this.arcState === 'initial') {
                // Sauvegarder l'état canvas PROPRE avant tout dessin
                const pageElement = this.pageElements.get(pageNum);
                if (pageElement?.annotationCtx && !this.arcCanvasState) {
                    this.arcCanvasState = pageElement.annotationCtx.getImageData(0, 0, pageElement.annotationCtx.canvas.width, pageElement.annotationCtx.canvas.height);
                    this.log('💾 État canvas propre sauvegardé pour arc');
                }
                
                // Premier clic : définir le centre de l'arc
                this.arcCenterPoint = { ...this.lastPoint };
                this.arcRadiusPoint = { ...this.lastPoint };
                this.arcState = 'drawing_radius';
                this.createArcRadiusElement();
                this.log('🌙 Outil arc initialisé - centre défini');
            }
        }
        
        // Initialiser l'outil texte
        if (this.currentTool === 'text') {
            // Ne pas démarrer le mode dessin pour le texte
            this.isDrawing = false;
            
            // Si il y a déjà une zone de texte active, la finaliser d'abord
            if (this.activeTextInput) {
                this.log('📝 Zone de texte existante détectée - finalisation');
                this.finalizeText(this.activeTextInput);
                return; // Ne pas créer de nouvelle zone
            }
            
            // Créer une zone de texte à la position du clic (avec délai pour éviter la propagation)
            setTimeout(() => {
                this.createTextInput(pageNum, this.lastPoint);
            }, 50);
            this.log('📝 Outil texte activé - zone de texte créée');
            return; // Arrêter ici pour l'outil texte
        }
        
        // Initialiser l'outil flèche
        if (this.currentTool === 'arrow') {
            // Sauvegarder l'état du canvas pour la prévisualisation
            const pageElement = this.pageElements.get(pageNum);
            if (pageElement?.annotationCtx && !this.arrowCanvasState) {
                this.arrowCanvasState = pageElement.annotationCtx.getImageData(0, 0, pageElement.annotationCtx.canvas.width, pageElement.annotationCtx.canvas.height);
            }
            
            this.arrowStartPoint = { ...this.lastPoint };
            this.arrowEndPoint = { ...this.lastPoint };
            this.createArrowLengthElement();
            this.log('➡️ Outil flèche initialisé - point de départ défini');
        }
        
        // Initialiser l'outil rectangle
        if (this.currentTool === 'rectangle') {
            // Sauvegarder l'état du canvas pour la prévisualisation
            const pageElement = this.pageElements.get(pageNum);
            if (pageElement?.annotationCtx && !this.rectangleCanvasState) {
                this.rectangleCanvasState = pageElement.annotationCtx.getImageData(0, 0, pageElement.annotationCtx.canvas.width, pageElement.annotationCtx.canvas.height);
            }
            
            this.rectangleStartPoint = { ...this.lastPoint };
            this.rectangleEndPoint = { ...this.lastPoint };
            this.createRectangleMeasureElement();
            this.log('⬜ Outil rectangle initialisé - point de départ défini');
        }
        
        // Initialiser l'outil cercle
        if (this.currentTool === 'circle') {
            // Sauvegarder l'état du canvas pour la prévisualisation
            const pageElement = this.pageElements.get(pageNum);
            if (pageElement?.annotationCtx && !this.circleCanvasState) {
                this.circleCanvasState = pageElement.annotationCtx.getImageData(0, 0, pageElement.annotationCtx.canvas.width, pageElement.annotationCtx.canvas.height);
            }
            
            this.circleStartPoint = { ...this.lastPoint };
            this.circleEndPoint = { ...this.lastPoint };
            this.createCircleMeasureElement();
            this.log('⭕ Outil cercle initialisé - centre défini');
        }

        // Outil grille - basculer la visibilité
        if (this.currentTool === 'grid') {
            const currentVisibility = this.gridVisible.get(pageNum) || false;
            this.gridVisible.set(pageNum, !currentVisibility);
            this.toggleGridDisplay(pageNum);
            this.log(`🔲 Grille ${!currentVisibility ? 'activée' : 'désactivée'} pour page ${pageNum}`);
            
            // Empêcher le mode dessin pour la grille
            this.isDrawing = false;
            return; // Arrêter ici pour l'outil grille
        }
        
        const pageElement = this.pageElements.get(pageNum);
        if (pageElement?.annotationCanvas) {
            pageElement.annotationCanvas.style.pointerEvents = 'all';
            this.log(`Canvas d'annotation activé pour page ${pageNum}`);
            
            // Pour le surligneur, commencer un nouveau chemin continu
            if (this.currentTool === 'highlighter') {
                const ctx = pageElement.annotationCtx;
                ctx.globalCompositeOperation = 'source-over';
                ctx.globalAlpha = 0.01; // 1% d'opacité pour un contrôle ultra-fin
                ctx.strokeStyle = this.currentColor;
                ctx.lineWidth = this.currentLineWidth * 3;
                ctx.lineCap = 'round'; // Changer en round pour les extrémités
                ctx.lineJoin = 'round'; // Changer en round pour les jointures
                
                // Commencer un nouveau chemin
                ctx.beginPath();
                ctx.moveTo(this.lastPoint.x, this.lastPoint.y);
            }
        } else {
            this.log(`ERREUR: Canvas d'annotation non trouvé pour page ${pageNum}`);
        }
    }
    
    draw(e, pageNum) {
        if (!this.isDrawing || !this.currentMode.annotations) return;
        
        const pageElement = this.pageElements.get(pageNum);
        if (!pageElement?.annotationCtx) {
            this.log(`ERREUR: Context d'annotation non trouvé pour page ${pageNum}`);
            return;
        }
        
        const rect = e.target.getBoundingClientRect();
        const currentPoint = {
            x: e.clientX - rect.left,
            y: e.clientY - rect.top
        };
        
        // Logs de débogage pour le premier trait
        if (!this.drawingLogged) {
            this.log(`Dessin en cours: page ${pageNum}, outil: ${this.currentTool}, couleur: ${this.currentColor}, épaisseur: ${this.currentLineWidth}`);
            this.log(`Point actuel: x=${currentPoint.x}, y=${currentPoint.y}`);
            this.drawingLogged = true;
        }
        
        const ctx = pageElement.annotationCtx;
        
        if (this.currentTool === 'eraser') {
            ctx.globalCompositeOperation = 'destination-out';
            ctx.strokeStyle = this.currentColor;
            // Utiliser la même taille que le curseur visuel
            ctx.lineWidth = this.currentLineWidth * 8;
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';
            
            ctx.beginPath();
            ctx.moveTo(this.lastPoint.x, this.lastPoint.y);
            ctx.lineTo(currentPoint.x, currentPoint.y);
            ctx.stroke();
        } else if (this.currentTool === 'highlighter') {
            // Pour le surligneur, continuer le chemin existant pour un trait continu
            ctx.lineTo(currentPoint.x, currentPoint.y);
            ctx.stroke();
            
            // Remettre l'opacité à 1% pour le prochain segment
            ctx.globalAlpha = 0.01;
        } else if (this.currentTool === 'ruler') {
            // Pour la règle, dessiner la ligne en temps réel
            this.rulerCurrentPoint = { ...currentPoint };
            this.drawRulerPreview(pageNum);
            this.updateRulerMeasure(pageNum);
        } else if (this.currentTool === 'compass') {
            // Pour le compas, dessiner le cercle en temps réel
            this.compassCurrentPoint = { ...currentPoint };
            this.drawCompassPreview(pageNum);
            this.updateCompassRadius(pageNum);
        } else if (this.currentTool === 'protractor') {
            // Pour le rapporteur, gérer les différents états
            if (this.protractorState === 'drawing_first_line') {
                this.protractorFirstPoint = { ...currentPoint };
                this.drawProtractorFirstLinePreview(pageNum);
                
                // Logique de validation par immobilité
                const distance = Math.sqrt(
                    Math.pow(currentPoint.x - this.protractorCenterPoint.x, 2) + 
                    Math.pow(currentPoint.y - this.protractorCenterPoint.y, 2)
                );
                
                // Si on a bougé assez loin du centre et qu'on n'a pas encore démarré le timer
                if (distance > 20 && !this.protractorValidationTimer) {
                    this.startProtractorValidationTimer(pageNum);
                } 
                // Si on bouge pendant le timer, le relancer
                else if (distance > 20 && this.protractorValidationTimer) {
                    this.startProtractorValidationTimer(pageNum); // Ceci va nettoyer l'ancien timer
                }
            } else if (this.protractorState === 'drawing_second_line') {
                this.protractorSecondPoint = { ...currentPoint };
                this.drawProtractorAnglePreview(pageNum);
                this.updateProtractorAngle(pageNum);
            }
        } else if (this.currentTool === 'arc') {
            // Pour l'arc de cercle, gérer les différents états
            if (this.arcState === 'drawing_radius') {
                this.arcRadiusPoint = { ...currentPoint };
                this.drawArcRadiusPreview(pageNum);
                this.updateArcRadius(pageNum);
                
                // Logique de validation par immobilité (comme le rapporteur)
                const distance = Math.sqrt(
                    Math.pow(currentPoint.x - this.arcCenterPoint.x, 2) + 
                    Math.pow(currentPoint.y - this.arcCenterPoint.y, 2)
                );
                
                // Si on a bougé assez loin du centre et qu'on n'a pas encore démarré le timer
                if (distance > 20 && !this.arcValidationTimer) {
                    this.startArcValidationTimer(pageNum);
                } 
                // Si on bouge pendant le timer, le relancer
                else if (distance > 20 && this.arcValidationTimer) {
                    this.startArcValidationTimer(pageNum);
                }
            } else if (this.arcState === 'drawing_arc') {
                this.arcEndPoint = { ...currentPoint };
                this.drawArcPreview(pageNum);
                this.updateArcRadius(pageNum);
                this.updateArcAngle(pageNum);
            }
        } else if (this.currentTool === 'arrow') {
            // Pour la flèche, dessiner la flèche en temps réel
            this.arrowEndPoint = { ...currentPoint };
            this.drawArrowPreview(pageNum);
            this.updateArrowLength(pageNum);
        } else if (this.currentTool === 'rectangle') {
            // Pour le rectangle, dessiner le rectangle en temps réel
            this.rectangleEndPoint = { ...currentPoint };
            this.drawRectanglePreview(pageNum);
            this.updateRectangleMeasure(pageNum);
        } else if (this.currentTool === 'circle') {
            // Pour le cercle, dessiner le cercle en temps réel
            this.circleEndPoint = { ...currentPoint };
            this.drawCirclePreview(pageNum);
            this.updateCircleMeasure(pageNum);
        } else {
            // Configuration pour le stylo et autres outils
            ctx.globalCompositeOperation = 'source-over';
            ctx.globalAlpha = 1.0; // Opacité complète
            ctx.strokeStyle = this.currentColor;
            ctx.lineWidth = this.currentLineWidth;
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';
            
            // Pour le stylo, ajouter le point au chemin et vérifier si on bouge
            if (this.currentTool === 'pen') {
                this.drawingPath.push({ ...currentPoint });
                
                // Si on bouge significativement, annuler le timer de ligne droite
                const distance = Math.sqrt(
                    Math.pow(currentPoint.x - this.startPoint.x, 2) + 
                    Math.pow(currentPoint.y - this.startPoint.y, 2)
                );
                
                // Si on bouge de plus de 10 pixels du point de départ, reset le timer
                if (distance > 10 && this.straightLineTimer && !this.isStabilized) {
                    clearTimeout(this.straightLineTimer);
                    this.straightLineTimer = setTimeout(() => {
                        this.convertToStraightLine(pageNum);
                    }, this.straightLineTimeout);
                }
            }
            
            ctx.beginPath();
            ctx.moveTo(this.lastPoint.x, this.lastPoint.y);
            ctx.lineTo(currentPoint.x, currentPoint.y);
            ctx.stroke();
        }
        
        this.lastPoint = currentPoint;
    }
    
    stopDrawing(e, pageNum) {
        if (this.isDrawing) {
            this.log(`Arrêt du dessin sur page ${pageNum}`);
            
            // Nettoyer le timer de ligne droite pour le stylo
            if (this.currentTool === 'pen' && this.straightLineTimer) {
                clearTimeout(this.straightLineTimer);
                this.straightLineTimer = null;
                this.log('Timer ligne droite nettoyé');
            }
            
            const pageElement = this.pageElements.get(pageNum);
            
            // Pour le surligneur, simplement remettre l'opacité normale sans ajouter de point
            if (this.currentTool === 'highlighter' && pageElement?.annotationCtx) {
                const ctx = pageElement.annotationCtx;
                ctx.globalAlpha = 1.0; // Remettre l'opacité normale
            }

            // Pour la règle, finaliser la ligne et nettoyer l'affichage
            if (this.currentTool === 'ruler') {
                this.finalizeRulerLine(pageNum);
                this.cleanupRulerDisplay();
            }

            // Pour le compas, finaliser le cercle et nettoyer l'affichage
            if (this.currentTool === 'compass') {
                this.finalizeCompassCircle(pageNum);
                this.cleanupCompassDisplay();
            }

            // Pour le rapporteur, finaliser l'angle et nettoyer l'affichage
            if (this.currentTool === 'protractor') {
                if (this.protractorState === 'drawing_second_line') {
                    this.finalizeProtractorAngle(pageNum);
                    this.cleanupProtractorDisplay();
                    this.resetProtractorState();
                } else if (this.protractorState === 'drawing_first_line') {
                    // Si on relâche pendant le premier trait, annuler
                    this.resetProtractorState();
                    this.cleanupProtractorDisplay();
                }
            }

            // Pour l'arc de cercle, finaliser l'arc et nettoyer l'affichage
            if (this.currentTool === 'arc') {
                if (this.arcState === 'drawing_arc') {
                    this.finalizeArc(pageNum);
                    this.cleanupArcDisplay();
                    this.resetArcState();
                } else if (this.arcState === 'drawing_radius') {
                    // Si on relâche pendant le premier trait (rayon), annuler
                    this.resetArcState();
                    this.cleanupArcDisplay();
                }
            }

            // Pour la flèche, finaliser la flèche et nettoyer l'affichage
            if (this.currentTool === 'arrow') {
                this.finalizeArrow(pageNum);
                this.cleanupArrowDisplay();
            }

            // Pour le rectangle, finaliser le rectangle et nettoyer l'affichage
            if (this.currentTool === 'rectangle') {
                this.finalizeRectangle(pageNum);
                this.cleanupRectangleDisplay();
            }

            // Pour le cercle, finaliser le cercle et nettoyer l'affichage
            if (this.currentTool === 'circle') {
                this.finalizeCircle(pageNum);
                this.cleanupCircleDisplay();
            }
            
            // Sauvegarder l'état final pour tous les outils dans l'historique undo/redo
            this.saveCanvasState(pageNum);
            
            this.isDrawing = false;
            this.lastPoint = null;
            this.drawingLogged = false; // Reset pour le prochain trait
            
            // Reset des variables ligne droite
            this.drawingPath = [];
            this.startPoint = null;
            this.isStabilized = false;
            this.currentStrokeImageData = null;

            // Reset des variables règle
            this.rulerStartPoint = null;
            this.rulerCurrentPoint = null;

            // Reset des variables compas
            this.compassCenterPoint = null;
            this.compassCurrentPoint = null;
            
            // Nettoyage partiel des variables rapporteur (garder l'état si en cours)
            if (this.currentTool !== 'protractor' || this.protractorState === 'initial') {
                this.resetProtractorState();
            }
            
            if (pageElement?.annotationCanvas) {
                // Ne pas désactiver pointer-events ici car l'outil est toujours sélectionné
                // pageElement.annotationCanvas.style.pointerEvents = 'none';
                this.log(`Dessin terminé sur page ${pageNum}`);
            }
            
            // Sauvegarder automatiquement si activé
            if (this.options.autoSave) {
                this.scheduleAutoSave();
            }
        }
    }

    /**
     * Convertit le trait actuel en ligne droite (fonctionnalité style iPad)
     */
    convertToStraightLine(pageNum) {
        if (!this.isDrawing || this.currentTool !== 'pen' || this.isStabilized) {
            return;
        }

        this.log('🔄 Conversion en ligne droite déclenchée');
        this.isStabilized = true;

        const pageElement = this.pageElements.get(pageNum);
        if (!pageElement?.annotationCtx || this.drawingPath.length < 2) {
            this.log('❌ Impossible de convertir: contexte ou chemin invalide');
            return;
        }

        const ctx = pageElement.annotationCtx;
        const startPoint = this.startPoint;
        const endPoint = this.drawingPath[this.drawingPath.length - 1];

        // Calculer la distance pour vérifier si c'est une vraie ligne
        const distance = Math.sqrt(
            Math.pow(endPoint.x - startPoint.x, 2) + 
            Math.pow(endPoint.y - startPoint.y, 2)
        );

        // Seulement convertir si la ligne fait au moins 20 pixels
        if (distance < 20) {
            this.log('📏 Ligne trop courte pour conversion');
            return;
        }

        this.log(`📐 Conversion ligne droite: ${startPoint.x},${startPoint.y} → ${endPoint.x},${endPoint.y} (distance: ${Math.round(distance)}px)`);

        // Restaurer l'état du canvas avant le trait actuel (efface seulement le trait en cours)
        if (this.currentStrokeImageData) {
            ctx.putImageData(this.currentStrokeImageData, 0, 0);
            this.log('🔄 Canvas restauré à l\'état avant le trait');
        }

        // Dessiner la ligne droite parfaite
        ctx.globalCompositeOperation = 'source-over';
        ctx.globalAlpha = 1.0;
        ctx.strokeStyle = this.currentColor;
        ctx.lineWidth = this.currentLineWidth;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';

        ctx.beginPath();
        ctx.moveTo(startPoint.x, startPoint.y);
        ctx.lineTo(endPoint.x, endPoint.y);
        ctx.stroke();

        this.log('✅ Ligne droite créée avec succès');

        // Mettre à jour le chemin avec juste les deux points
        this.drawingPath = [startPoint, endPoint];

        // Effet visuel de feedback (petit flash)
        this.showStraightLineConfirmation(pageElement.annotationCanvas);
    }

    /**
     * Efface les annotations de la page (pour redessiner proprement)
     */
    clearPageAnnotations(pageNum) {
        const pageElement = this.pageElements.get(pageNum);
        if (pageElement?.annotationCtx) {
            const canvas = pageElement.annotationCanvas;
            pageElement.annotationCtx.clearRect(0, 0, canvas.width, canvas.height);
            this.log(`🧹 Annotations effacées pour page ${pageNum}`);
        }
    }

    /**
     * Affiche une confirmation visuelle de la conversion en ligne droite
     */
    showStraightLineConfirmation(canvas) {
        // Effet flash subtil pour confirmer la conversion
        const originalFilter = canvas.style.filter;
        canvas.style.filter = 'brightness(1.2)';
        
        setTimeout(() => {
            canvas.style.filter = originalFilter;
        }, 150);

        this.log('✨ Effet de confirmation affiché');
    }

    /**
     * Crée l'élément d'affichage de la mesure pour la règle
     */
    createRulerMeasureElement() {
        // Supprimer l'ancien élément s'il existe
        if (this.rulerMeasureElement) {
            this.rulerMeasureElement.remove();
        }

        this.rulerMeasureElement = document.createElement('div');
        this.rulerMeasureElement.id = 'ruler-measure';
        this.rulerMeasureElement.style.cssText = `
            position: fixed;
            background: rgba(0, 0, 0, 0.9);
            color: white;
            padding: 8px 12px;
            border-radius: 8px;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 14px;
            font-weight: 600;
            z-index: 10000;
            pointer-events: none;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            transform: translate(-50%, -120%);
            display: none;
        `;

        document.body.appendChild(this.rulerMeasureElement);
        this.log('📏 Élément de mesure créé');
    }

    /**
     * Dessine la prévisualisation de la règle en temps réel
     */
    drawRulerPreview(pageNum) {
        const pageElement = this.pageElements.get(pageNum);
        if (!pageElement?.annotationCtx || !this.rulerStartPoint || !this.rulerCurrentPoint) {
            return;
        }

        const ctx = pageElement.annotationCtx;
        const canvas = pageElement.annotationCanvas;

        // Sauvegarder l'état propre du canvas la première fois (AVANT toute prévisualisation)
        if (!this.rulerCanvasState) {
            this.rulerCanvasState = ctx.getImageData(0, 0, canvas.width, canvas.height);
            this.log('📸 État propre du canvas sauvegardé AVANT prévisualisation');
        }
        
        // Restaurer l'état propre du canvas (sans aucune prévisualisation)
        ctx.putImageData(this.rulerCanvasState, 0, 0);

        // Dessiner la ligne de prévisualisation
        ctx.save();
        ctx.globalCompositeOperation = 'source-over';
        ctx.strokeStyle = '#FF4444'; // Rouge pour la prévisualisation
        ctx.lineWidth = 2;
        ctx.lineCap = 'round';
        ctx.setLineDash([5, 5]); // Ligne pointillée

        ctx.beginPath();
        ctx.moveTo(this.rulerStartPoint.x, this.rulerStartPoint.y);
        ctx.lineTo(this.rulerCurrentPoint.x, this.rulerCurrentPoint.y);
        ctx.stroke();

        // Dessiner les marqueurs aux extrémités
        this.drawRulerEndpoints(ctx);

        ctx.restore();
    }

    /**
     * Dessine les marqueurs aux extrémités de la règle (prévisualisation)
     */
    drawRulerEndpoints(ctx) {
        const radius = 4;
        
        // Durant la prévisualisation, dessiner seulement le point d'arrivée rouge
        // Le point de départ noir sera ajouté seulement lors de la finalisation
        ctx.fillStyle = '#FF4444';
        ctx.beginPath();
        ctx.arc(this.rulerCurrentPoint.x, this.rulerCurrentPoint.y, radius, 0, 2 * Math.PI);
        ctx.fill();
    }

    /**
     * Met à jour l'affichage de la mesure
     */
    updateRulerMeasure(pageNum) {
        if (!this.rulerMeasureElement || !this.rulerStartPoint || !this.rulerCurrentPoint) {
            return;
        }

        // Calculer la distance en pixels
        const deltaX = this.rulerCurrentPoint.x - this.rulerStartPoint.x;
        const deltaY = this.rulerCurrentPoint.y - this.rulerStartPoint.y;
        const distancePixels = Math.sqrt(deltaX * deltaX + deltaY * deltaY);

        // Convertir en centimètres (en tenant compte du zoom)
        const distanceCm = (distancePixels / (this.a4PixelsPerCm * this.currentScale));

        // Position du curseur pour afficher la mesure
        const midX = (this.rulerStartPoint.x + this.rulerCurrentPoint.x) / 2;
        const midY = (this.rulerStartPoint.y + this.rulerCurrentPoint.y) / 2;

        // Convertir en coordonnées de fenêtre (utiliser la page courante)
        const canvas = this.pageElements.get(pageNum)?.annotationCanvas;
        if (canvas) {
            const rect = canvas.getBoundingClientRect();
            const windowX = rect.left + midX;
            const windowY = rect.top + midY;

            this.rulerMeasureElement.style.left = windowX + 'px';
            this.rulerMeasureElement.style.top = windowY + 'px';
            this.rulerMeasureElement.style.display = 'block';
            this.rulerMeasureElement.textContent = `${distanceCm.toFixed(1)} cm`;
        }
    }

    /**
     * Finalise la ligne de règle (la dessine de façon permanente)
     */
    finalizeRulerLine(pageNum) {
        const pageElement = this.pageElements.get(pageNum);
        if (!pageElement?.annotationCtx || !this.rulerStartPoint || !this.rulerCurrentPoint) {
            return;
        }

        // Restaurer le canvas à l'état avant la prévisualisation
        if (this.rulerCanvasState) {
            const ctx = pageElement.annotationCtx;
            ctx.putImageData(this.rulerCanvasState, 0, 0);
        }

        // Dessiner la ligne finale (solide)
        const ctx = pageElement.annotationCtx;
        ctx.save();
        ctx.globalCompositeOperation = 'source-over';
        ctx.strokeStyle = this.currentColor;
        ctx.lineWidth = this.currentLineWidth;
        ctx.lineCap = 'round';
        ctx.setLineDash([]); // Ligne solide

        ctx.beginPath();
        ctx.moveTo(this.rulerStartPoint.x, this.rulerStartPoint.y);
        ctx.lineTo(this.rulerCurrentPoint.x, this.rulerCurrentPoint.y);
        ctx.stroke();

        // Dessiner les points d'extrémité noirs
        this.drawFinalRulerEndpoints(ctx);
        
        ctx.restore();

        this.rulerCanvasState = null;
        this.log('📏 Ligne de règle finalisée');
    }

    /**
     * Nettoie l'affichage de la règle
     */
    cleanupRulerDisplay() {
        if (this.rulerMeasureElement) {
            this.rulerMeasureElement.style.display = 'none';
        }
        this.rulerCanvasState = null;
        this.log('🧹 Affichage règle nettoyé');
    }

    /**
     * Dessine les points d'extrémité noirs pour la ligne finale
     */
    drawFinalRulerEndpoints(ctx) {
        const radius = 3;
        
        // Point de départ (noir)
        ctx.fillStyle = '#000000';
        ctx.beginPath();
        ctx.arc(this.rulerStartPoint.x, this.rulerStartPoint.y, radius, 0, 2 * Math.PI);
        ctx.fill();

        // Point d'arrivée (noir)
        ctx.fillStyle = '#000000';
        ctx.beginPath();
        ctx.arc(this.rulerCurrentPoint.x, this.rulerCurrentPoint.y, radius, 0, 2 * Math.PI);
        ctx.fill();

        this.log('⚫ Points d\'extrémité noirs ajoutés');
    }

    /**
     * Crée l'élément d'affichage du rayon pour le compas
     */
    createCompassRadiusElement() {
        // Supprimer l'ancien élément s'il existe
        if (this.compassRadiusElement) {
            this.compassRadiusElement.remove();
        }

        this.compassRadiusElement = document.createElement('div');
        this.compassRadiusElement.id = 'compass-radius';
        this.compassRadiusElement.style.cssText = `
            position: fixed;
            background: rgba(0, 0, 0, 0.9);
            color: white;
            padding: 8px 12px;
            border-radius: 8px;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 14px;
            font-weight: 600;
            z-index: 10000;
            pointer-events: none;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 165, 0, 0.4);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            transform: translate(-50%, -120%);
            display: none;
        `;

        document.body.appendChild(this.compassRadiusElement);
        this.log('🧭 Élément de rayon créé');
    }

    /**
     * Dessine la prévisualisation du compas en temps réel
     */
    drawCompassPreview(pageNum) {
        const pageElement = this.pageElements.get(pageNum);
        if (!pageElement?.annotationCtx || !this.compassCenterPoint || !this.compassCurrentPoint) {
            return;
        }

        const ctx = pageElement.annotationCtx;
        const canvas = pageElement.annotationCanvas;

        // Sauvegarder l'état propre du canvas la première fois (AVANT toute prévisualisation)
        if (!this.compassCanvasState) {
            this.compassCanvasState = ctx.getImageData(0, 0, canvas.width, canvas.height);
            this.log('📸 État propre du canvas sauvegardé AVANT prévisualisation compas');
        }
        
        // Restaurer l'état propre du canvas (sans aucune prévisualisation)
        ctx.putImageData(this.compassCanvasState, 0, 0);

        // Calculer le rayon
        const deltaX = this.compassCurrentPoint.x - this.compassCenterPoint.x;
        const deltaY = this.compassCurrentPoint.y - this.compassCenterPoint.y;
        const radius = Math.sqrt(deltaX * deltaX + deltaY * deltaY);

        // Dessiner la prévisualisation du cercle
        ctx.save();
        ctx.globalCompositeOperation = 'source-over';
        ctx.strokeStyle = '#FF4444'; // Rouge pour la prévisualisation
        ctx.lineWidth = 2;
        ctx.lineCap = 'round';
        ctx.setLineDash([5, 5]); // Ligne pointillée

        ctx.beginPath();
        ctx.arc(this.compassCenterPoint.x, this.compassCenterPoint.y, radius, 0, 2 * Math.PI);
        ctx.stroke();

        // Dessiner la ligne du rayon
        ctx.setLineDash([2, 2]); // Ligne pointillée plus fine
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(this.compassCenterPoint.x, this.compassCenterPoint.y);
        ctx.lineTo(this.compassCurrentPoint.x, this.compassCurrentPoint.y);
        ctx.stroke();

        // Dessiner les marqueurs
        this.drawCompassMarkers(ctx);

        ctx.restore();
    }

    /**
     * Dessine les marqueurs du compas (centre et point du rayon)
     */
    drawCompassMarkers(ctx) {
        // Point central (vert)
        ctx.fillStyle = '#22C55E';
        ctx.beginPath();
        ctx.arc(this.compassCenterPoint.x, this.compassCenterPoint.y, 4, 0, 2 * Math.PI);
        ctx.fill();

        // Point du rayon (rouge)
        ctx.fillStyle = '#FF4444';
        ctx.beginPath();
        ctx.arc(this.compassCurrentPoint.x, this.compassCurrentPoint.y, 3, 0, 2 * Math.PI);
        ctx.fill();
    }

    /**
     * Met à jour l'affichage du rayon
     */
    updateCompassRadius(pageNum) {
        if (!this.compassRadiusElement || !this.compassCenterPoint || !this.compassCurrentPoint) {
            return;
        }

        // Calculer le rayon en pixels
        const deltaX = this.compassCurrentPoint.x - this.compassCenterPoint.x;
        const deltaY = this.compassCurrentPoint.y - this.compassCenterPoint.y;
        const radiusPixels = Math.sqrt(deltaX * deltaX + deltaY * deltaY);

        // Convertir en centimètres (en tenant compte du zoom)
        const radiusCm = (radiusPixels / (this.a4PixelsPerCm * this.currentScale));

        // Position du curseur pour afficher la mesure (au milieu du rayon)
        const midX = (this.compassCenterPoint.x + this.compassCurrentPoint.x) / 2;
        const midY = (this.compassCenterPoint.y + this.compassCurrentPoint.y) / 2;

        // Convertir en coordonnées de fenêtre (utiliser la page courante)
        const canvas = this.pageElements.get(pageNum)?.annotationCanvas;
        if (canvas) {
            const rect = canvas.getBoundingClientRect();
            const windowX = rect.left + midX;
            const windowY = rect.top + midY;

            this.compassRadiusElement.style.left = windowX + 'px';
            this.compassRadiusElement.style.top = windowY + 'px';
            this.compassRadiusElement.style.display = 'block';
            this.compassRadiusElement.textContent = `r: ${radiusCm.toFixed(1)} cm`;
        }
    }

    /**
     * Finalise le cercle du compas (le dessine de façon permanente)
     */
    finalizeCompassCircle(pageNum) {
        const pageElement = this.pageElements.get(pageNum);
        if (!pageElement?.annotationCtx || !this.compassCenterPoint || !this.compassCurrentPoint) {
            return;
        }

        // Restaurer le canvas à l'état avant la prévisualisation
        if (this.compassCanvasState) {
            const ctx = pageElement.annotationCtx;
            ctx.putImageData(this.compassCanvasState, 0, 0);
        }

        // Calculer le rayon final
        const deltaX = this.compassCurrentPoint.x - this.compassCenterPoint.x;
        const deltaY = this.compassCurrentPoint.y - this.compassCenterPoint.y;
        const radius = Math.sqrt(deltaX * deltaX + deltaY * deltaY);

        // Dessiner le cercle final (solide)
        const ctx = pageElement.annotationCtx;
        ctx.save();
        ctx.globalCompositeOperation = 'source-over';
        ctx.strokeStyle = this.currentColor;
        ctx.lineWidth = this.currentLineWidth;
        ctx.lineCap = 'round';
        ctx.setLineDash([]); // Ligne solide

        ctx.beginPath();
        ctx.arc(this.compassCenterPoint.x, this.compassCenterPoint.y, radius, 0, 2 * Math.PI);
        ctx.stroke();

        // Dessiner le point central noir
        this.drawFinalCompassCenter(ctx);
        
        ctx.restore();

        this.compassCanvasState = null;
        this.log('🧭 Cercle du compas finalisé');
    }

    /**
     * Dessine le point central noir du compas
     */
    drawFinalCompassCenter(ctx) {
        // Point central (noir)
        ctx.fillStyle = '#000000';
        ctx.beginPath();
        ctx.arc(this.compassCenterPoint.x, this.compassCenterPoint.y, 2, 0, 2 * Math.PI);
        ctx.fill();

        this.log('⚫ Point central noir ajouté');
    }

    /**
     * Nettoie l'affichage du compas
     */
    cleanupCompassDisplay() {
        if (this.compassRadiusElement) {
            this.compassRadiusElement.style.display = 'none';
        }
        this.compassCanvasState = null;
        this.log('🧹 Affichage compas nettoyé');
    }

    /**
     * ==========================================
     * FONCTIONS OUTIL RAPPORTEUR (PROTRACTOR)
     * ==========================================
     */

    /**
     * Crée l'élément d'affichage de l'angle pour le rapporteur
     */
    createProtractorAngleElement() {
        // Supprimer l'ancien élément s'il existe
        if (this.protractorAngleElement) {
            this.protractorAngleElement.remove();
        }

        this.protractorAngleElement = document.createElement('div');
        this.protractorAngleElement.id = 'protractor-angle';
        this.protractorAngleElement.style.cssText = `
            position: fixed;
            background: rgba(0, 0, 0, 0.9);
            color: white;
            padding: 8px 12px;
            border-radius: 8px;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 14px;
            font-weight: 600;
            z-index: 10000;
            pointer-events: none;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 165, 0, 0.4);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            transform: translate(-50%, -120%);
            display: none;
        `;

        document.body.appendChild(this.protractorAngleElement);
        this.log('📐 Élément d\'angle créé');
    }

    /**
     * Dessine la prévisualisation du premier trait du rapporteur
     */
    drawProtractorFirstLinePreview(pageNum) {
        const pageElement = this.pageElements.get(pageNum);
        if (!pageElement?.annotationCtx || !this.protractorCenterPoint || !this.protractorFirstPoint) {
            return;
        }

        const ctx = pageElement.annotationCtx;
        const canvas = pageElement.annotationCanvas;

        // Sauvegarder l'état propre du canvas la première fois
        if (!this.protractorCanvasState) {
            this.protractorCanvasState = ctx.getImageData(0, 0, canvas.width, canvas.height);
            this.log('📸 État propre du canvas sauvegardé AVANT prévisualisation rapporteur');
        }
        
        // Restaurer l'état propre du canvas
        ctx.putImageData(this.protractorCanvasState, 0, 0);

        // Dessiner la ligne de prévisualisation (comme la règle)
        ctx.save();
        ctx.globalCompositeOperation = 'source-over';
        ctx.strokeStyle = '#FF4444'; // Rouge pour la prévisualisation
        ctx.lineWidth = 2;
        ctx.lineCap = 'round';
        ctx.setLineDash([5, 5]); // Ligne pointillée

        ctx.beginPath();
        ctx.moveTo(this.protractorCenterPoint.x, this.protractorCenterPoint.y);
        ctx.lineTo(this.protractorFirstPoint.x, this.protractorFirstPoint.y);
        ctx.stroke();

        // Dessiner le point central
        ctx.fillStyle = '#22C55E'; // Vert pour le centre
        ctx.setLineDash([]);
        ctx.beginPath();
        ctx.arc(this.protractorCenterPoint.x, this.protractorCenterPoint.y, 4, 0, 2 * Math.PI);
        ctx.fill();

        // Dessiner le point d'extrémité
        ctx.fillStyle = '#FF4444'; // Rouge pour l'extrémité
        ctx.beginPath();
        ctx.arc(this.protractorFirstPoint.x, this.protractorFirstPoint.y, 3, 0, 2 * Math.PI);
        ctx.fill();

        ctx.restore();
    }

    /**
     * Démarre le timer de validation pour le premier trait
     */
    startProtractorValidationTimer(pageNum) {
        // Nettoyer le timer précédent
        if (this.protractorValidationTimer) {
            clearTimeout(this.protractorValidationTimer);
        }

        this.protractorValidationTimer = setTimeout(() => {
            this.validateFirstLine(pageNum);
        }, this.protractorValidationTimeout);

        this.log('⏰ Timer de validation rapporteur démarré (1.5s)');
    }

    /**
     * Valide le premier trait et passe au deuxième trait
     */
    validateFirstLine(pageNum) {
        if (this.protractorState !== 'drawing_first_line') {
            return;
        }

        this.log('✅ Premier trait validé - passage au deuxième trait');
        this.protractorState = 'drawing_second_line';
        this.protractorSecondPoint = { ...this.protractorFirstPoint }; // Commencer du même point

        // Dessiner le premier trait de façon permanente
        this.drawPermanentFirstLine(pageNum);

        // Effet visuel de confirmation
        this.showProtractorValidationFeedback(pageNum);
    }

    /**
     * Dessine le premier trait de façon permanente
     */
    drawPermanentFirstLine(pageNum) {
        const pageElement = this.pageElements.get(pageNum);
        if (!pageElement?.annotationCtx) return;

        const ctx = pageElement.annotationCtx;
        
        // Restaurer l'état propre et dessiner le trait permanent
        if (this.protractorCanvasState) {
            ctx.putImageData(this.protractorCanvasState, 0, 0);
        }

        ctx.save();
        ctx.globalCompositeOperation = 'source-over';
        ctx.strokeStyle = this.currentColor;
        ctx.lineWidth = this.currentLineWidth;
        ctx.lineCap = 'round';
        ctx.setLineDash([]);

        ctx.beginPath();
        ctx.moveTo(this.protractorCenterPoint.x, this.protractorCenterPoint.y);
        ctx.lineTo(this.protractorFirstPoint.x, this.protractorFirstPoint.y);
        ctx.stroke();

        ctx.restore();

        // Sauvegarder l'état avec le premier trait
        this.protractorCanvasState = ctx.getImageData(0, 0, pageElement.annotationCanvas.width, pageElement.annotationCanvas.height);
        this.log('📏 Premier trait dessiné de façon permanente');
    }

    /**
     * Affiche un feedback visuel de validation
     */
    showProtractorValidationFeedback(pageNum) {
        const pageElement = this.pageElements.get(pageNum);
        if (!pageElement?.annotationCanvas) return;

        // Effet flash subtil
        const canvas = pageElement.annotationCanvas;
        const originalFilter = canvas.style.filter;
        canvas.style.filter = 'brightness(1.3) saturate(1.2)';
        
        setTimeout(() => {
            canvas.style.filter = originalFilter;
        }, 200);

        this.log('✨ Feedback de validation affiché');
    }

    /**
     * Dessine la prévisualisation de l'angle complet
     */
    drawProtractorAnglePreview(pageNum) {
        const pageElement = this.pageElements.get(pageNum);
        if (!pageElement?.annotationCtx || !this.protractorCenterPoint || !this.protractorFirstPoint || !this.protractorSecondPoint) {
            return;
        }

        const ctx = pageElement.annotationCtx;
        
        // Restaurer l'état avec le premier trait permanent
        if (this.protractorCanvasState) {
            ctx.putImageData(this.protractorCanvasState, 0, 0);
        }

        // Utiliser le point aimanté s'il existe, sinon le point actuel
        const effectiveSecondPoint = this.protractorSnappedPoint || this.protractorSecondPoint;

        // Dessiner le deuxième trait en prévisualisation
        ctx.save();
        ctx.globalCompositeOperation = 'source-over';
        
        // Couleur différente si aimanté
        ctx.strokeStyle = this.protractorSnappedPoint ? '#22C55E' : '#FF4444'; // Vert si aimanté, rouge sinon
        ctx.lineWidth = this.protractorSnappedPoint ? 3 : 2; // Plus épais si aimanté
        ctx.lineCap = 'round';
        ctx.setLineDash([5, 5]);

        ctx.beginPath();
        ctx.moveTo(this.protractorCenterPoint.x, this.protractorCenterPoint.y);
        ctx.lineTo(effectiveSecondPoint.x, effectiveSecondPoint.y);
        ctx.stroke();

        // Dessiner l'arc de l'angle avec le point effectif
        this.drawAngleArc(ctx, effectiveSecondPoint);

        // Dessiner les marqueurs avec le point effectif
        this.drawProtractorMarkers(ctx, effectiveSecondPoint);

        ctx.restore();
    }

    /**
     * Dessine l'arc représentant l'angle
     */
    drawAngleArc(ctx, effectiveSecondPoint = null) {
        const radius = 30; // Rayon de l'arc d'angle
        const secondPoint = effectiveSecondPoint || this.protractorSecondPoint;

        // Calculer les angles
        const angle1 = Math.atan2(
            this.protractorFirstPoint.y - this.protractorCenterPoint.y,
            this.protractorFirstPoint.x - this.protractorCenterPoint.x
        );
        const angle2 = Math.atan2(
            secondPoint.y - this.protractorCenterPoint.y,
            secondPoint.x - this.protractorCenterPoint.x
        );

        // Couleur différente si aimanté
        ctx.strokeStyle = this.protractorSnappedPoint ? '#22C55E' : '#8B5CF6'; // Vert si aimanté, violet sinon
        ctx.lineWidth = this.protractorSnappedPoint ? 3 : 2; // Plus épais si aimanté
        ctx.setLineDash([3, 3]);

        ctx.beginPath();
        // Dessiner l'arc dans le sens trigonométrique (antihoraire)
        // Si angle2 < angle1, on traverse 0°, donc on dessine dans le sens positif
        if (angle2 < angle1) {
            ctx.arc(this.protractorCenterPoint.x, this.protractorCenterPoint.y, radius, angle1, angle2 + 2 * Math.PI);
        } else {
            ctx.arc(this.protractorCenterPoint.x, this.protractorCenterPoint.y, radius, angle1, angle2);
        }
        ctx.stroke();
    }

    /**
     * Dessine les marqueurs du rapporteur
     */
    drawProtractorMarkers(ctx, effectiveSecondPoint = null) {
        const secondPoint = effectiveSecondPoint || this.protractorSecondPoint;

        // Point central (vert)
        ctx.fillStyle = '#22C55E';
        ctx.setLineDash([]);
        ctx.beginPath();
        ctx.arc(this.protractorCenterPoint.x, this.protractorCenterPoint.y, 4, 0, 2 * Math.PI);
        ctx.fill();

        // Point de fin du deuxième trait - couleur selon aimantation
        ctx.fillStyle = this.protractorSnappedPoint ? '#22C55E' : '#FF4444'; // Vert si aimanté, rouge sinon
        const pointRadius = this.protractorSnappedPoint ? 4 : 3; // Plus gros si aimanté
        ctx.beginPath();
        ctx.arc(secondPoint.x, secondPoint.y, pointRadius, 0, 2 * Math.PI);
        ctx.fill();

        // Si aimanté, ajouter un anneau pour indiquer l'aimantation
        if (this.protractorSnappedPoint) {
            ctx.strokeStyle = '#22C55E';
            ctx.lineWidth = 2;
            ctx.setLineDash([2, 2]);
            ctx.beginPath();
            ctx.arc(secondPoint.x, secondPoint.y, 8, 0, 2 * Math.PI);
            ctx.stroke();
        }
    }

    /**
     * Met à jour l'affichage de l'angle en degrés avec aimantation
     */
    updateProtractorAngle(pageNum) {
        if (!this.protractorAngleElement || !this.protractorCenterPoint || !this.protractorFirstPoint || !this.protractorSecondPoint) {
            return;
        }

        // Calculer l'angle entre les deux traits
        const angle1 = Math.atan2(
            this.protractorFirstPoint.y - this.protractorCenterPoint.y,
            this.protractorFirstPoint.x - this.protractorCenterPoint.x
        );
        const angle2 = Math.atan2(
            this.protractorSecondPoint.y - this.protractorCenterPoint.y,
            this.protractorSecondPoint.x - this.protractorCenterPoint.x
        );

        let angleDiff = angle2 - angle1;
        
        // Normaliser l'angle entre 0 et 2π (permettre angles complets 0-360°)
        if (angleDiff < 0) angleDiff += 2 * Math.PI;
        
        // Convertir en degrés (0° à 360°)
        let angleDegrees = (angleDiff * 180) / Math.PI;

        // Calculer l'angle le plus petit pour l'affichage (≤ 180°)
        let displayAngle = angleDegrees;
        if (angleDegrees > 180) {
            displayAngle = 360 - angleDegrees;
        }

        // AIMANTATION AUX ANGLES ENTIERS (sur l'angle d'affichage)
        let snappedAngle = displayAngle;
        let isSnapped = false;

        if (this.protractorSnapToInteger) {
            const nearestInteger = Math.round(displayAngle);
            const difference = Math.abs(displayAngle - nearestInteger);
            
            // Si on est assez proche d'un angle entier, s'y aimanter
            if (difference <= this.protractorSnapTolerance) {
                snappedAngle = nearestInteger;
                isSnapped = true;
                
                // Pour l'aimantation, on doit recalculer l'angle complet correct
                let targetFullAngle = snappedAngle;
                if (angleDegrees > 180 && snappedAngle !== 180) {
                    targetFullAngle = 360 - snappedAngle;
                }
                
                // Calculer le point corrigé pour l'aimantation
                this.protractorSnappedPoint = this.calculateSnappedPoint(targetFullAngle);
                
                this.log(`🧲 Aimantation: ${displayAngle.toFixed(1)}° → ${snappedAngle}° (angle minimal)`);
            } else {
                this.protractorSnappedPoint = null;
            }
        }

        // Position pour afficher la mesure (au centre de l'angle) - utiliser la page courante
        const canvas = this.pageElements.get(pageNum)?.annotationCanvas;
        if (canvas) {
            const rect = canvas.getBoundingClientRect();
            const windowX = rect.left + this.protractorCenterPoint.x;
            const windowY = rect.top + this.protractorCenterPoint.y - 50; // Un peu au-dessus du centre

            this.protractorAngleElement.style.left = windowX + 'px';
            this.protractorAngleElement.style.top = windowY + 'px';
            this.protractorAngleElement.style.display = 'block';
            
            // Afficher l'angle le plus petit avec indicateur d'aimantation
            const displayText = isSnapped ? `${snappedAngle}° 🧲` : `${displayAngle.toFixed(1)}°`;
            this.protractorAngleElement.textContent = displayText;
            
            // Changer la couleur pour indiquer l'aimantation
            this.protractorAngleElement.style.color = isSnapped ? '#22C55E' : 'white';
            this.protractorAngleElement.style.borderColor = isSnapped ? 'rgba(34, 197, 94, 0.4)' : 'rgba(255, 165, 0, 0.4)';
        }
    }

    /**
     * Calcule la position du point corrigé pour l'aimantation
     */
    calculateSnappedPoint(targetAngleDegrees) {
        if (!this.protractorCenterPoint || !this.protractorFirstPoint || !this.protractorSecondPoint) {
            return null;
        }

        // Calculer l'angle du premier trait
        const angle1 = Math.atan2(
            this.protractorFirstPoint.y - this.protractorCenterPoint.y,
            this.protractorFirstPoint.x - this.protractorCenterPoint.x
        );

        // Calculer l'angle cible en radians (relatif au premier trait)
        const targetAngleRad = (targetAngleDegrees * Math.PI) / 180;
        const finalAngle = angle1 + targetAngleRad;

        // Calculer la distance actuelle du deuxième point
        const currentDistance = Math.sqrt(
            Math.pow(this.protractorSecondPoint.x - this.protractorCenterPoint.x, 2) + 
            Math.pow(this.protractorSecondPoint.y - this.protractorCenterPoint.y, 2)
        );

        // Calculer le nouveau point à la bonne position
        const snappedX = this.protractorCenterPoint.x + currentDistance * Math.cos(finalAngle);
        const snappedY = this.protractorCenterPoint.y + currentDistance * Math.sin(finalAngle);

        return {
            x: snappedX,
            y: snappedY
        };
    }

    /**
     * Finalise l'angle (le dessine de façon permanente)
     */
    finalizeProtractorAngle(pageNum) {
        const pageElement = this.pageElements.get(pageNum);
        if (!pageElement?.annotationCtx || !this.protractorCenterPoint || !this.protractorFirstPoint || !this.protractorSecondPoint) {
            return;
        }

        // Restaurer l'état avec le premier trait
        if (this.protractorCanvasState) {
            const ctx = pageElement.annotationCtx;
            ctx.putImageData(this.protractorCanvasState, 0, 0);
        }

        // Utiliser le point aimanté pour la finalisation s'il existe
        const finalSecondPoint = this.protractorSnappedPoint || this.protractorSecondPoint;

        // Dessiner le deuxième trait permanent
        const ctx = pageElement.annotationCtx;
        ctx.save();
        ctx.globalCompositeOperation = 'source-over';
        ctx.strokeStyle = this.currentColor;
        ctx.lineWidth = this.currentLineWidth;
        ctx.lineCap = 'round';
        ctx.setLineDash([]);

        ctx.beginPath();
        ctx.moveTo(this.protractorCenterPoint.x, this.protractorCenterPoint.y);
        ctx.lineTo(finalSecondPoint.x, finalSecondPoint.y);
        ctx.stroke();

        // Dessiner les points finaux noirs
        this.drawFinalProtractorPoints(ctx, finalSecondPoint);
        
        ctx.restore();

        this.protractorCanvasState = null;
        this.log('📐 Angle du rapporteur finalisé');
    }

    /**
     * Dessine les points finaux noirs du rapporteur
     */
    drawFinalProtractorPoints(ctx, finalSecondPoint = null) {
        const radius = 2;
        const secondPoint = finalSecondPoint || this.protractorSecondPoint;
        
        // Point central (noir)
        ctx.fillStyle = '#000000';
        ctx.beginPath();
        ctx.arc(this.protractorCenterPoint.x, this.protractorCenterPoint.y, radius + 1, 0, 2 * Math.PI);
        ctx.fill();

        // Points d'extrémité (noirs)
        ctx.fillStyle = '#000000';
        ctx.beginPath();
        ctx.arc(this.protractorFirstPoint.x, this.protractorFirstPoint.y, radius, 0, 2 * Math.PI);
        ctx.fill();

        ctx.beginPath();
        ctx.arc(secondPoint.x, secondPoint.y, radius, 0, 2 * Math.PI);
        ctx.fill();

        // Log avec information d'aimantation
        const wasSnapped = this.protractorSnappedPoint ? ' (avec aimantation)' : '';
        this.log(`⚫ Points d'extrémité noirs ajoutés${wasSnapped}`);
    }

    /**
     * Nettoie l'affichage du rapporteur
     */
    cleanupProtractorDisplay() {
        if (this.protractorAngleElement) {
            this.protractorAngleElement.style.display = 'none';
        }
        if (this.protractorValidationTimer) {
            clearTimeout(this.protractorValidationTimer);
            this.protractorValidationTimer = null;
        }
        this.protractorCanvasState = null;
        this.log('🧹 Affichage rapporteur nettoyé');
    }

    /**
     * Remet à zéro l'état du rapporteur
     */
    resetProtractorState() {
        this.protractorState = 'initial';
        this.protractorCenterPoint = null;
        this.protractorFirstPoint = null;
        this.protractorSecondPoint = null;
        if (this.protractorValidationTimer) {
            clearTimeout(this.protractorValidationTimer);
            this.protractorValidationTimer = null;
        }
        this.log('🔄 État rapporteur réinitialisé');
    }

    // =====================================================
    // MÉTHODES OUTIL ARC DE CERCLE
    // =====================================================

    createArcRadiusElement() {
        // Créer l'élément d'affichage du rayon flottant
        this.arcRadiusElement = document.createElement('div');
        this.arcRadiusElement.style.position = 'fixed';
        this.arcRadiusElement.style.background = 'rgba(0, 0, 0, 0.9)';
        this.arcRadiusElement.style.color = '#F97316';
        this.arcRadiusElement.style.padding = '8px 12px';
        this.arcRadiusElement.style.borderRadius = '8px';
        this.arcRadiusElement.style.fontSize = '14px';
        this.arcRadiusElement.style.fontFamily = 'Monaco, monospace';
        this.arcRadiusElement.style.fontWeight = '600';
        this.arcRadiusElement.style.pointerEvents = 'none';
        this.arcRadiusElement.style.zIndex = '10000';
        this.arcRadiusElement.style.border = '2px solid rgba(249, 115, 22, 0.4)';
        this.arcRadiusElement.style.backdropFilter = 'blur(10px)';
        this.arcRadiusElement.style.boxShadow = '0 8px 32px rgba(0, 0, 0, 0.3)';
        this.arcRadiusElement.style.transition = 'all 0.2s ease';
        this.arcRadiusElement.style.display = 'none';
        this.arcRadiusElement.textContent = '0.0 cm';
        document.body.appendChild(this.arcRadiusElement);

        // Créer l'élément d'affichage de l'angle flottant
        this.arcAngleElement = document.createElement('div');
        this.arcAngleElement.style.position = 'fixed';
        this.arcAngleElement.style.background = 'rgba(0, 0, 0, 0.9)';
        this.arcAngleElement.style.color = '#3B82F6';
        this.arcAngleElement.style.padding = '8px 12px';
        this.arcAngleElement.style.borderRadius = '8px';
        this.arcAngleElement.style.fontSize = '14px';
        this.arcAngleElement.style.fontFamily = 'Monaco, monospace';
        this.arcAngleElement.style.fontWeight = '600';
        this.arcAngleElement.style.pointerEvents = 'none';
        this.arcAngleElement.style.zIndex = '10000';
        this.arcAngleElement.style.border = '2px solid rgba(59, 130, 246, 0.4)';
        this.arcAngleElement.style.backdropFilter = 'blur(10px)';
        this.arcAngleElement.style.boxShadow = '0 8px 32px rgba(0, 0, 0, 0.3)';
        this.arcAngleElement.style.transition = 'all 0.2s ease';
        this.arcAngleElement.style.display = 'none';
        this.arcAngleElement.textContent = '0°';
        document.body.appendChild(this.arcAngleElement);
        
        this.log('🌙 Éléments rayon et angle arc créés');
    }

    drawArcRadiusPreview(pageNum) {
        // Dessiner la prévisualisation du rayon (trait pointillé)
        const pageElement = this.pageElements.get(pageNum);
        if (!pageElement?.annotationCtx) return;

        const ctx = pageElement.annotationCtx;
        
        // Restaurer l'état propre (sauvegardé à l'initialisation)
        if (this.arcCanvasState) {
            ctx.putImageData(this.arcCanvasState, 0, 0);
        }
        
        // Dessiner le trait de rayon en pointillé rouge
        ctx.save();
        ctx.strokeStyle = '#EF4444';
        ctx.lineWidth = 2;
        ctx.setLineDash([8, 4]);
        ctx.lineCap = 'round';
        
        ctx.beginPath();
        ctx.moveTo(this.arcCenterPoint.x, this.arcCenterPoint.y);
        ctx.lineTo(this.arcRadiusPoint.x, this.arcRadiusPoint.y);
        ctx.stroke();
        ctx.restore();
        
        // Dessiner les points de référence
        this.drawArcRadiusMarkers(ctx);
        
        this.log('🌙 Prévisualisation rayon arc mise à jour');
    }

    drawArcRadiusMarkers(ctx) {
        // Dessiner les marqueurs pour le rayon
        ctx.save();
        
        // Point central (vert)
        ctx.fillStyle = '#22C55E';
        ctx.beginPath();
        ctx.arc(this.arcCenterPoint.x, this.arcCenterPoint.y, 4, 0, 2 * Math.PI);
        ctx.fill();
        
        // Point du rayon (rouge)
        ctx.fillStyle = '#EF4444';
        ctx.beginPath();
        ctx.arc(this.arcRadiusPoint.x, this.arcRadiusPoint.y, 3, 0, 2 * Math.PI);
        ctx.fill();
        
        ctx.restore();
    }

    startArcValidationTimer(pageNum) {
        // Démarrer le timer de validation pour le rayon (1.5s)
        if (this.arcValidationTimer) {
            clearTimeout(this.arcValidationTimer);
        }

        this.arcValidationTimer = setTimeout(() => {
            this.validateArcRadius(pageNum);
        }, this.arcValidationTimeout);
        
        this.log('⏱️ Timer validation rayon arc démarré');
    }

    validateArcRadius(pageNum) {
        // Valider le rayon et passer au tracé de l'arc
        if (this.arcState !== 'drawing_radius') {
            return;
        }

        this.arcState = 'drawing_arc';
        this.arcEndPoint = { ...this.arcRadiusPoint };
        
        // Nettoyer le canvas et sauvegarder l'état propre (le rayon sera masqué)
        this.drawPermanentRadius(pageNum);
        this.showArcValidationFeedback(pageNum);
        
        this.log('✅ Rayon arc validé - passage au tracé arc');
    }

    drawPermanentRadius(pageNum) {
        // Nettoyer complètement et sauvegarder un état propre (sans rayon)
        const pageElement = this.pageElements.get(pageNum);
        if (!pageElement?.annotationCtx) return;

        const ctx = pageElement.annotationCtx;
        
        // Restaurer l'état initial vraiment propre (celui sauvé au tout début)
        if (this.arcCanvasState) {
            ctx.putImageData(this.arcCanvasState, 0, 0);
        }
        
        // NE PAS resauvegarder - on garde l'état initial propre pour la finalisation
        this.log('✏️ Canvas nettoyé, état propre conservé (rayon masqué)');
    }

    showArcValidationFeedback(pageNum) {
        // Afficher un feedback visuel de validation
        const pageElement = this.pageElements.get(pageNum);
        if (!pageElement?.annotationCanvas) return;

        const canvas = pageElement.annotationCanvas;
        canvas.style.filter = 'brightness(1.3) saturate(1.5)';
        
        setTimeout(() => {
            canvas.style.filter = '';
        }, 200);
        
        this.log('✨ Feedback validation rayon arc');
    }

    drawArcPreview(pageNum) {
        // Dessiner la prévisualisation de l'arc complet
        const pageElement = this.pageElements.get(pageNum);
        if (!pageElement?.annotationCtx) return;

        const ctx = pageElement.annotationCtx;
        
        // Restaurer l'état propre (SANS le rayon permanent)
        if (this.arcCanvasState) {
            ctx.putImageData(this.arcCanvasState, 0, 0);
        }
        
        // Calculer le rayon
        const radius = Math.sqrt(
            Math.pow(this.arcRadiusPoint.x - this.arcCenterPoint.x, 2) + 
            Math.pow(this.arcRadiusPoint.y - this.arcCenterPoint.y, 2)
        );
        
        // Calculer les angles
        const startAngle = Math.atan2(
            this.arcRadiusPoint.y - this.arcCenterPoint.y,
            this.arcRadiusPoint.x - this.arcCenterPoint.x
        );
        let endAngle = Math.atan2(
            this.arcEndPoint.y - this.arcCenterPoint.y,
            this.arcEndPoint.x - this.arcCenterPoint.x
        );

        // Vérifier l'aimantation
        const snappedPoint = this.calculateArcSnappedPoint();
        if (snappedPoint) {
            this.arcSnappedEndPoint = snappedPoint;
            endAngle = Math.atan2(
                snappedPoint.y - this.arcCenterPoint.y,
                snappedPoint.x - this.arcCenterPoint.x
            );
        } else {
            this.arcSnappedEndPoint = null;
        }

        // Calculer l'angle et s'assurer qu'on prend toujours le plus petit arc (≤ 180°)
        let angleDiff = ((endAngle - startAngle + 2 * Math.PI) % (2 * Math.PI));
        let clockwise = false;
        
        if (angleDiff > Math.PI) {
            // L'arc direct est > 180°, on prend l'arc dans l'autre sens
            clockwise = true;
            angleDiff = 2 * Math.PI - angleDiff;
        }
        
        // Dessiner l'arc en prévisualisation
        ctx.save();
        if (snappedPoint) {
            ctx.strokeStyle = '#22C55E'; // Vert pour l'aimantation
            ctx.lineWidth = this.currentLineWidth + 1;
        } else {
            ctx.strokeStyle = this.currentColor;
            ctx.lineWidth = this.currentLineWidth;
        }
        ctx.setLineDash([6, 3]);
        ctx.lineCap = 'round';
        
        ctx.beginPath();
        ctx.arc(this.arcCenterPoint.x, this.arcCenterPoint.y, radius, startAngle, endAngle, clockwise);
        ctx.stroke();
        ctx.restore();
        
        // Dessiner les marqueurs
        this.drawArcPreviewMarkers(ctx, radius, snappedPoint);
        
        this.log('🌙 Prévisualisation arc mise à jour');
    }

    drawArcPreviewMarkers(ctx, radius, snappedPoint) {
        // Dessiner les marqueurs pour l'arc
        ctx.save();
        
        // Point central (vert)
        ctx.fillStyle = '#22C55E';
        ctx.beginPath();
        ctx.arc(this.arcCenterPoint.x, this.arcCenterPoint.y, 4, 0, 2 * Math.PI);
        ctx.fill();
        
        // Point de début du rayon (orange)
        ctx.fillStyle = '#F97316';
        ctx.beginPath();
        ctx.arc(this.arcRadiusPoint.x, this.arcRadiusPoint.y, 3, 0, 2 * Math.PI);
        ctx.fill();
        
        // Point de fin de l'arc
        if (snappedPoint) {
            // Point aimanté (vert plus gros)
            ctx.fillStyle = '#22C55E';
            ctx.beginPath();
            ctx.arc(snappedPoint.x, snappedPoint.y, 4, 0, 2 * Math.PI);
            ctx.fill();
            
            // Anneau d'aimantation
            ctx.strokeStyle = '#22C55E';
            ctx.lineWidth = 2;
            ctx.setLineDash([]);
            ctx.beginPath();
            ctx.arc(snappedPoint.x, snappedPoint.y, 8, 0, 2 * Math.PI);
            ctx.stroke();
        } else {
            // Point normal (bleu)
            ctx.fillStyle = '#3B82F6';
            ctx.beginPath();
            ctx.arc(this.arcEndPoint.x, this.arcEndPoint.y, 3, 0, 2 * Math.PI);
            ctx.fill();
        }
        
        ctx.restore();
    }

    updateArcRadius(pageNum) {
        // Mettre à jour l'affichage du rayon
        if (!this.arcRadiusElement || !this.arcCenterPoint || !this.arcRadiusPoint) return;
        
        // Calculer le rayon en pixels puis en cm
        const radiusPixels = Math.sqrt(
            Math.pow(this.arcRadiusPoint.x - this.arcCenterPoint.x, 2) + 
            Math.pow(this.arcRadiusPoint.y - this.arcCenterPoint.y, 2)
        );
        const radiusCm = radiusPixels / this.a4PixelsPerCm;
        
        // Mettre à jour le texte
        this.arcRadiusElement.textContent = `${radiusCm.toFixed(1)} cm`;
        
        // Positionner l'élément (utiliser la page courante)
        const canvas = this.pageElements.get(pageNum)?.annotationCanvas;
        if (canvas) {
            const rect = canvas.getBoundingClientRect();
            const centerX = rect.left + this.arcCenterPoint.x;
            const centerY = rect.top + this.arcCenterPoint.y;
            
            this.arcRadiusElement.style.left = `${centerX - 30}px`;
            this.arcRadiusElement.style.top = `${centerY - 40}px`;
            this.arcRadiusElement.style.display = 'block';
        }
        
        this.log(`📏 Rayon arc: ${radiusCm.toFixed(1)} cm`);
    }

    updateArcAngle(pageNum) {
        // Mettre à jour l'affichage de l'angle de l'arc
        if (!this.arcAngleElement || !this.arcCenterPoint || !this.arcRadiusPoint || !this.arcEndPoint) return;
        
        // Calculer les angles
        const startAngle = Math.atan2(
            this.arcRadiusPoint.y - this.arcCenterPoint.y,
            this.arcRadiusPoint.x - this.arcCenterPoint.x
        );
        const endAngle = Math.atan2(
            this.arcEndPoint.y - this.arcCenterPoint.y,
            this.arcEndPoint.x - this.arcCenterPoint.x
        );

        // Calculer l'angle de l'arc et toujours prendre le plus petit (≤ 180°)
        let arcAngleDeg = ((endAngle - startAngle) * 180 / Math.PI + 360) % 360;
        if (arcAngleDeg > 180) {
            arcAngleDeg = 360 - arcAngleDeg;
        }

        // Vérifier l'aimantation
        const snappedPoint = this.calculateArcSnappedPoint();
        let displayText;
        let color;

        if (snappedPoint) {
            displayText = `${snappedPoint.snappedAngle}° 🧲`;
            color = '#22C55E';
            this.arcAngleElement.style.color = color;
            this.arcAngleElement.style.borderColor = 'rgba(34, 197, 94, 0.4)';
        } else {
            displayText = `${Math.round(arcAngleDeg)}°`;
            color = '#3B82F6';
            this.arcAngleElement.style.color = color;
            this.arcAngleElement.style.borderColor = 'rgba(59, 130, 246, 0.4)';
        }
        
        // Mettre à jour le texte
        this.arcAngleElement.textContent = displayText;
        
        // Positionner l'élément (décalé par rapport au rayon) - utiliser la page courante
        const canvas = this.pageElements.get(pageNum)?.annotationCanvas;
        if (canvas) {
            const rect = canvas.getBoundingClientRect();
            const centerX = rect.left + this.arcCenterPoint.x;
            const centerY = rect.top + this.arcCenterPoint.y;
            
            this.arcAngleElement.style.left = `${centerX + 20}px`;
            this.arcAngleElement.style.top = `${centerY - 40}px`;
            this.arcAngleElement.style.display = 'block';
        }
        
        this.log(`📐 Angle arc: ${displayText} (${snappedPoint ? 'aimanté' : 'libre'})`);
    }

    finalizeArc(pageNum) {
        // Finaliser l'arc de cercle (sans le rayon)
        const pageElement = this.pageElements.get(pageNum);
        if (!pageElement?.annotationCtx) return;

        const ctx = pageElement.annotationCtx;
        
        // Restaurer l'état propre (SANS le rayon permanent)
        if (this.arcCanvasState) {
            ctx.putImageData(this.arcCanvasState, 0, 0);
        }
        
        // Calculer le rayon
        const radius = Math.sqrt(
            Math.pow(this.arcRadiusPoint.x - this.arcCenterPoint.x, 2) + 
            Math.pow(this.arcRadiusPoint.y - this.arcCenterPoint.y, 2)
        );
        
        // Calculer les angles
        const startAngle = Math.atan2(
            this.arcRadiusPoint.y - this.arcCenterPoint.y,
            this.arcRadiusPoint.x - this.arcCenterPoint.x
        );
        let endAngle = Math.atan2(
            this.arcEndPoint.y - this.arcCenterPoint.y,
            this.arcEndPoint.x - this.arcCenterPoint.x
        );

        // Utiliser le point aimanté si disponible
        const snappedPoint = this.arcSnappedEndPoint;
        if (snappedPoint) {
            endAngle = Math.atan2(
                snappedPoint.y - this.arcCenterPoint.y,
                snappedPoint.x - this.arcCenterPoint.x
            );
        }

        // Calculer l'angle et s'assurer qu'on prend toujours le plus petit arc (≤ 180°)
        let angleDiff = ((endAngle - startAngle + 2 * Math.PI) % (2 * Math.PI));
        let clockwise = false;
        
        if (angleDiff > Math.PI) {
            // L'arc direct est > 180°, on prend l'arc dans l'autre sens
            clockwise = true;
            angleDiff = 2 * Math.PI - angleDiff;
        }

        const angleDeg = angleDiff * 180 / Math.PI;
        
        // Dessiner l'arc final (SANS le rayon)
        ctx.save();
        ctx.strokeStyle = this.currentColor;
        ctx.lineWidth = this.currentLineWidth;
        ctx.setLineDash([]);
        ctx.lineCap = 'round';
        
        ctx.beginPath();
        ctx.arc(this.arcCenterPoint.x, this.arcCenterPoint.y, radius, startAngle, endAngle, clockwise);
        ctx.stroke();
        ctx.restore();
        
        // Dessiner seulement le point central final
        this.drawFinalArcPoints(ctx);
        
        const radiusCm = radius / this.a4PixelsPerCm;
        const snapInfo = snappedPoint ? ` (aimanté à ${snappedPoint.snappedAngle}°)` : '';
        
        this.log(`✅ Arc finalisé - Rayon: ${radiusCm.toFixed(1)}cm, Angle: ${angleDeg.toFixed(1)}°${snapInfo}`);
    }

    drawFinalArcPoints(ctx) {
        // Dessiner les points finaux de l'arc (seulement le centre)
        ctx.save();
        ctx.fillStyle = '#000000'; // Points noirs pour la finalisation
        
        // Point central uniquement
        ctx.beginPath();
        ctx.arc(this.arcCenterPoint.x, this.arcCenterPoint.y, 2, 0, 2 * Math.PI);
        ctx.fill();
        
        ctx.restore();
    }

    cleanupArcDisplay() {
        // Nettoyer l'affichage de l'arc
        if (this.arcRadiusElement) {
            this.arcRadiusElement.style.display = 'none';
        }
        
        if (this.arcAngleElement) {
            this.arcAngleElement.style.display = 'none';
        }
        
        if (this.arcValidationTimer) {
            clearTimeout(this.arcValidationTimer);
            this.arcValidationTimer = null;
        }
        
        this.arcCanvasState = null;
        
        this.log('🧹 Affichage arc nettoyé');
    }

    resetArcState() {
        // Réinitialiser l'état de l'outil arc
        this.arcState = 'initial';
        this.arcCenterPoint = null;
        this.arcRadiusPoint = null;
        this.arcEndPoint = null;
        this.arcSnappedEndPoint = null;
        this.arcCanvasState = null; // Réinitialiser l'état canvas
        if (this.arcValidationTimer) {
            clearTimeout(this.arcValidationTimer);
            this.arcValidationTimer = null;
        }
        this.log('🔄 État arc réinitialisé');
    }

    calculateArcSnappedPoint() {
        // Calculer le point corrigé par l'aimantation pour l'arc
        if (!this.arcCenterPoint || !this.arcRadiusPoint || !this.arcEndPoint) {
            return null;
        }

        // Calculer le rayon
        const radius = Math.sqrt(
            Math.pow(this.arcRadiusPoint.x - this.arcCenterPoint.x, 2) + 
            Math.pow(this.arcRadiusPoint.y - this.arcCenterPoint.y, 2)
        );

        // Calculer les angles
        const startAngle = Math.atan2(
            this.arcRadiusPoint.y - this.arcCenterPoint.y,
            this.arcRadiusPoint.x - this.arcCenterPoint.x
        );
        const endAngle = Math.atan2(
            this.arcEndPoint.y - this.arcCenterPoint.y,
            this.arcEndPoint.x - this.arcCenterPoint.x
        );

        // Calculer l'angle de l'arc en degrés
        let arcAngle = ((endAngle - startAngle) * 180 / Math.PI + 360) % 360;
        
        // Toujours prendre l'angle le plus petit (≤ 180°)
        if (arcAngle > 180) {
            arcAngle = 360 - arcAngle;
        }

        // Vérifier si on doit appliquer l'aimantation
        if (!this.arcSnapToInteger) {
            return null;
        }

        const nearestInteger = Math.round(arcAngle);
        const difference = Math.abs(arcAngle - nearestInteger);

        if (difference <= this.arcSnapTolerance) {
            // Calculer le nouvel angle final aimanté
            let snappedAngle = nearestInteger * Math.PI / 180;
            
            // Déterminer le sens (horaire ou antihoraire) pour le plus petit arc
            let finalEndAngle;
            if (((endAngle - startAngle + 2 * Math.PI) % (2 * Math.PI)) <= Math.PI) {
                // Sens antihoraire (arc actuel <= 180°)
                finalEndAngle = startAngle + snappedAngle;
            } else {
                // Sens horaire (arc actuel > 180°, on veut le plus petit)
                finalEndAngle = startAngle - snappedAngle;
            }

            // Calculer la nouvelle position du point final
            const snappedX = this.arcCenterPoint.x + radius * Math.cos(finalEndAngle);
            const snappedY = this.arcCenterPoint.y + radius * Math.sin(finalEndAngle);

            return {
                x: snappedX,
                y: snappedY,
                snappedAngle: nearestInteger
            };
        }

        return null;
    }
    
    // =====================================================
    // MÉTHODES OUTIL TEXTE
    // =====================================================
    
    /**
     * Crée une zone de saisie de texte à la position cliquée
     */
    createTextInput(pageNum, position) {
        const pageElement = this.pageElements.get(pageNum);
        if (!pageElement) {
            this.log('❌ Page element non trouvé pour page:', pageNum);
            return;
        }
        
        // Supprimer toute zone de texte existante
        this.removeActiveTextInput();
        
        // Créer l'input de texte
        const textInput = document.createElement('textarea');
        textInput.className = 'pdf-text-input';
        
        // Configuration de base
        textInput.placeholder = 'Tapez votre texte ici...';
        textInput.style.position = 'fixed';
        textInput.style.width = '200px';
        textInput.style.height = '60px';
        textInput.style.fontSize = '16px';
        textInput.style.fontFamily = 'Arial, sans-serif';
        textInput.style.padding = '8px';
        textInput.style.borderRadius = '4px';
        textInput.style.backgroundColor = 'rgba(255, 255, 255, 0.95)';
        textInput.style.zIndex = '10000';
        textInput.style.resize = 'both';
        textInput.style.minWidth = '150px';
        textInput.style.minHeight = '40px';
        textInput.style.outline = 'none';
        
        // Appliquer la couleur sélectionnée au texte et à la bordure
        textInput.style.color = this.currentColor;
        textInput.style.border = `2px solid ${this.currentColor}`;
        textInput.style.boxShadow = `0 2px 8px ${this.currentColor}33`; // 33 = 20% d'opacité
        
        this.log('🎨 Couleur appliquée à la zone de texte (texte et bordure):', this.currentColor);
        
        // Stocker les infos pour la finalisation
        textInput.dataset.pageNum = pageNum;
        textInput.dataset.x = position.x;
        textInput.dataset.y = position.y;
        
        // Calculer la position sur l'écran
        const canvas = pageElement.annotationCanvas;
        const canvasRect = canvas.getBoundingClientRect();
        const screenX = canvasRect.left + position.x;
        const screenY = canvasRect.top + position.y;
        
        textInput.style.left = `${screenX}px`;
        textInput.style.top = `${screenY}px`;
        
        // Pour l'outil texte, on ne sauvegarde PAS ici
        // La sauvegarde se fera après que le texte soit effectivement ajouté au canvas
        
        // Ajouter au body
        document.body.appendChild(textInput);
        
        // Stocker la référence IMMÉDIATEMENT
        this.activeTextInput = textInput;
        
        this.log('📝 TextInput créé et ajouté au DOM');
        
        // Focus avec délai pour s'assurer que l'élément est bien rendu
        setTimeout(() => {
            if (textInput.parentNode) {
                textInput.focus();
                textInput.select();
                this.log('🎯 Focus donné au textarea');
            }
        }, 10);
        
        // Événements clavier seulement
        textInput.addEventListener('keydown', (e) => {
            e.stopPropagation();
            
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                this.finalizeText(textInput);
            } else if (e.key === 'Escape') {
                e.preventDefault();
                this.removeActiveTextInput();
            }
        });
        
        // Clic extérieur avec priorité haute pour intercepter avant les autres événements
        const setupClickHandler = () => {
            this.textClickHandler = (e) => {
                if (this.activeTextInput && 
                    !this.activeTextInput.contains(e.target) && 
                    this.activeTextInput.parentNode) {
                    
                    this.log('👆 Clic extérieur détecté - finalisation du texte');
                    
                    // Empêcher la propagation pour éviter d'autres clics
                    e.preventDefault();
                    e.stopPropagation();
                    e.stopImmediatePropagation();
                    
                    // Nettoyer immédiatement le gestionnaire
                    document.removeEventListener('click', this.textClickHandler, true);
                    this.textClickHandler = null;
                    
                    // Finaliser le texte
                    this.finalizeText(this.activeTextInput);
                    
                    return false;
                }
            };
            // Utiliser capture: true pour intercepter l'événement en premier
            document.addEventListener('click', this.textClickHandler, true);
            this.log('👂 Gestionnaire clic extérieur installé (capture mode)');
        };
        
        // Délai de 200ms pour s'assurer que l'événement initial est terminé
        setTimeout(setupClickHandler, 200);
        
        this.log('✅ Zone de texte créée avec gestionnaires d\'événements');
    }
    
    /**
     * Finalise le texte et le dessine sur le canvas
     */
    finalizeText(textInput) {
        // Vérifier que l'input existe encore et n'a pas déjà été supprimé
        if (!textInput || !textInput.parentNode) {
            this.log('📝 Zone de texte déjà supprimée, abandon de la finalisation');
            return;
        }
        
        const text = textInput.value.trim();
        if (!text) {
            // Si pas de texte, juste supprimer l'input
            this.log('📝 Pas de texte saisi, suppression de la zone');
            this.removeActiveTextInput();
            return;
        }
        
        const pageNum = parseInt(textInput.dataset.pageNum);
        const x = parseFloat(textInput.dataset.x);
        const y = parseFloat(textInput.dataset.y);
        
        const pageElement = this.pageElements.get(pageNum);
        if (!pageElement?.annotationCtx) {
            this.log('❌ Impossible de finaliser le texte - contexte non trouvé');
            this.removeActiveTextInput();
            return;
        }
        
        const ctx = pageElement.annotationCtx;
        
        // Configurer le style de texte
        ctx.save();
        ctx.font = '16px Arial';
        ctx.fillStyle = this.currentColor;
        ctx.textBaseline = 'top';
        
        // Gérer le texte multiligne
        const lines = text.split('\n');
        const lineHeight = 20;
        
        lines.forEach((line, index) => {
            if (line.trim()) { // Éviter de dessiner des lignes vides
                ctx.fillText(line, x, y + (index * lineHeight));
            }
        });
        
        ctx.restore();
        
        // Sauvegarder l'état APRÈS avoir ajouté le texte (comme les autres outils)
        this.saveCanvasState(pageNum);
        this.log('💾 État canvas sauvé après ajout du texte');
        
        // Supprimer l'input
        this.removeActiveTextInput();
        
        this.log('✅ Texte finalisé:', text);
        
        // Programmer la sauvegarde automatique
        if (this.options.autoSave) {
            this.scheduleAutoSave();
        }
    }
    
    /**
     * Supprime la zone de texte active
     */
    removeActiveTextInput() {
        if (this.activeTextInput) {
            this.activeTextInput.remove();
            this.activeTextInput = null;
            this.log('📝 Zone de texte supprimée (pas de sauvegarde d\'état car pas de texte ajouté)');
        }
        
        // Nettoyer le gestionnaire de clic extérieur
        if (this.textClickHandler) {
            document.removeEventListener('click', this.textClickHandler, true);
            this.textClickHandler = null;
            this.log('🧹 Gestionnaire clic extérieur nettoyé');
        }
    }
    
    renderPageAnnotations(pageNum) {
        const pageElement = this.pageElements.get(pageNum);
        if (!pageElement?.annotationCtx) return;

        // Effacer le canvas d'annotation
        const ctx = pageElement.annotationCtx;
        ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);

        // Rendre les annotations existantes pour cette page
        const annotations = this.annotations.get(pageNum);
        if (annotations) {
            // Logique de rendu des annotations sauvegardées
            console.log(`Rendu des annotations pour la page ${pageNum}:`, annotations);
        }

        // Redessiner la grille si elle était visible
        const isGridVisible = this.gridVisible.get(pageNum) || false;
        if (isGridVisible) {
            this.drawGrid(pageNum);
        }
    }
    
    async loadAnnotations() {
        // Charger les annotations depuis l'API
        try {
            const response = await fetch(`${this.options.apiEndpoints.loadAnnotations}/${this.fileId}`);
            if (response.ok) {
                const data = await response.json();
                this.annotations = new Map(Object.entries(data.annotations || {}));
                this.log('Annotations chargées');
            }
        } catch (error) {
            this.log('Erreur chargement annotations:', error);
        }
    }
    
    async saveAnnotations() {
        // Sauvegarder les annotations via l'API
        try {
            const annotationsData = Object.fromEntries(this.annotations);
            const response = await fetch(this.options.apiEndpoints.saveAnnotations, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    file_id: this.fileId,
                    annotations: annotationsData
                })
            });
            
            if (response.ok) {
                this.log('Annotations sauvegardées');
                this.emit('annotations-saved');
            }
        } catch (error) {
            this.log('Erreur sauvegarde annotations:', error);
        }
    }
    
    scheduleAutoSave() {
        if (this.saveTimeout) {
            clearTimeout(this.saveTimeout);
        }
        this.saveTimeout = setTimeout(() => {
            this.saveAnnotations();
        }, this.options.saveDelay);
    }
    
    // =====================================================
    // MÉTHODES GESTION HISTORIQUE (UNDO/REDO)
    // =====================================================

    /**
     * Initialise l'historique undo avec un état vide pour chaque page
     */
    initializeUndoHistory() {
        this.pageElements.forEach((pageElement, pageNum) => {
            if (pageElement?.annotationCtx) {
                const ctx = pageElement.annotationCtx;
                const emptyState = ctx.getImageData(0, 0, ctx.canvas.width, ctx.canvas.height);
                
                // Initialiser les stacks pour cette page
                if (!this.undoStack.has(pageNum)) {
                    this.undoStack.set(pageNum, []);
                }
                if (!this.redoStack.has(pageNum)) {
                    this.redoStack.set(pageNum, []);
                }
                
                // Ajouter l'état vide initial
                this.undoStack.get(pageNum).push(emptyState);
                this.log(`📄 Historique initialisé pour page ${pageNum}`);
            }
        });
        this.updateUndoRedoButtons();
    }

    /**
     * Initialise l'historique undo pour une page spécifique
     */
    initializeUndoHistoryForPage(pageNum) {
        const pageElement = this.pageElements.get(pageNum);
        if (pageElement?.annotationCtx) {
            const ctx = pageElement.annotationCtx;
            const emptyState = ctx.getImageData(0, 0, ctx.canvas.width, ctx.canvas.height);
            
            // Initialiser les stacks pour cette page
            if (!this.undoStack.has(pageNum)) {
                this.undoStack.set(pageNum, []);
            }
            if (!this.redoStack.has(pageNum)) {
                this.redoStack.set(pageNum, []);
            }
            
            // Ajouter l'état vide initial
            this.undoStack.get(pageNum).push(emptyState);
            this.log(`📄 Historique initialisé pour page ${pageNum}`);
            
            this.updateUndoRedoButtons();
        }
    }

    /**
     * Sauvegarde l'état actuel du canvas dans l'historique
     */
    saveCanvasState(pageNum) {
        const pageElement = this.pageElements.get(pageNum);
        if (!pageElement?.annotationCtx) return;

        const ctx = pageElement.annotationCtx;
        const imageData = ctx.getImageData(0, 0, ctx.canvas.width, ctx.canvas.height);
        
        // Initialiser les stacks pour cette page si nécessaire
        if (!this.undoStack.has(pageNum)) {
            this.undoStack.set(pageNum, []);
        }
        if (!this.redoStack.has(pageNum)) {
            this.redoStack.set(pageNum, []);
        }
        
        // Ajouter l'état actuel à la stack d'undo
        const undoHistory = this.undoStack.get(pageNum);
        undoHistory.push(imageData);
        
        // Limiter la taille de l'historique (par exemple 20 états)
        if (undoHistory.length > 20) {
            undoHistory.shift(); // Supprimer le plus ancien
        }
        
        // Vider la stack de redo quand on fait une nouvelle action
        this.redoStack.set(pageNum, []);
        
        this.log(`💾 État canvas sauvé pour page ${pageNum} (${undoHistory.length} états)`);
        this.updateUndoRedoButtons();
    }

    /**
     * Annule la dernière action sur la page courante
     */
    undo() {
        const pageNum = this.currentPage;
        const undoHistory = this.undoStack.get(pageNum);
        
        // Vérifier qu'il y a au moins 2 états (pour pouvoir revenir à un état précédent)
        if (!undoHistory || undoHistory.length < 2) {
            this.log('⚠️ Aucune action à annuler sur cette page');
            return;
        }
        
        const pageElement = this.pageElements.get(pageNum);
        if (!pageElement?.annotationCtx) return;
        
        // Retirer le dernier état (l'état actuel avec la dernière action)
        const currentState = undoHistory.pop();
        
        // Sauvegarder cet état dans la stack de redo
        if (!this.redoStack.has(pageNum)) {
            this.redoStack.set(pageNum, []);
        }
        this.redoStack.get(pageNum).push(currentState);
        
        // Restaurer l'état précédent (avant la dernière action)
        const previousState = undoHistory[undoHistory.length - 1];
        const ctx = pageElement.annotationCtx;
        ctx.putImageData(previousState, 0, 0);
        
        this.log(`↶ Annulation effectuée sur page ${pageNum} (${undoHistory.length} états restants)`);
        this.updateUndoRedoButtons();
        
        // Nettoyer les états des outils actifs
        this.resetToolStates();
    }

    /**
     * Refait la dernière action annulée sur la page courante
     */
    redo() {
        const pageNum = this.currentPage;
        const redoHistory = this.redoStack.get(pageNum);
        
        if (!redoHistory || redoHistory.length === 0) {
            this.log('⚠️ Aucune action à refaire sur cette page');
            return;
        }
        
        const pageElement = this.pageElements.get(pageNum);
        if (!pageElement?.annotationCtx) return;
        
        // Sauvegarder l'état actuel dans la stack d'undo
        const ctx = pageElement.annotationCtx;
        const currentState = ctx.getImageData(0, 0, ctx.canvas.width, ctx.canvas.height);
        
        if (!this.undoStack.has(pageNum)) {
            this.undoStack.set(pageNum, []);
        }
        this.undoStack.get(pageNum).push(currentState);
        
        // Restaurer l'état suivant
        const nextState = redoHistory.pop();
        ctx.putImageData(nextState, 0, 0);
        
        this.log(`↷ Refaire effectué sur page ${pageNum} (${redoHistory.length} états restants)`);
        this.updateUndoRedoButtons();
        
        // Nettoyer les états des outils actifs
        this.resetToolStates();
    }

    /**
     * Vide la page courante
     */
    clearCurrentPage() {
        const pageNum = this.currentPage;
        const pageElement = this.pageElements.get(pageNum);
        if (!pageElement?.annotationCtx) return;
        
        // Effacer le canvas
        const ctx = pageElement.annotationCtx;
        ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
        
        // Sauvegarder l'état après effacement
        this.saveCanvasState(pageNum);
        
        this.log(`🗑️ Page ${pageNum} effacée`);
        
        // Nettoyer les états des outils actifs
        this.resetToolStates();
        
        // Programmer la sauvegarde automatique
        if (this.options.autoSave) {
            this.scheduleAutoSave();
        }
    }

    /**
     * Met à jour l'état des boutons undo/redo
     */
    updateUndoRedoButtons() {
        const pageNum = this.currentPage;
        const undoHistory = this.undoStack.get(pageNum) || [];
        const redoHistory = this.redoStack.get(pageNum) || [];
        
        const undoBtn = document.getElementById('btn-undo');
        const redoBtn = document.getElementById('btn-redo');
        
        // Pour undo, on peut annuler s'il y a au moins 2 états (un état précédent + l'état actuel)
        const canUndo = undoHistory.length >= 2;
        const undoCount = Math.max(0, undoHistory.length - 1); // -1 car le dernier est l'état actuel
        
        if (undoBtn) {
            undoBtn.disabled = !canUndo;
            undoBtn.style.opacity = canUndo ? '1' : '0.5';
            undoBtn.title = canUndo ? `Annuler (${undoCount} action${undoCount > 1 ? 's' : ''})` : 'Aucune action à annuler';
        }
        
        if (redoBtn) {
            redoBtn.disabled = redoHistory.length === 0;
            redoBtn.style.opacity = redoHistory.length === 0 ? '0.5' : '1';
            redoBtn.title = redoHistory.length === 0 ? 'Aucune action à refaire' : `Refaire (${redoHistory.length} action${redoHistory.length > 1 ? 's' : ''})`;
        }
    }

    /**
     * Remet à zéro les états des outils actifs
     */
    resetToolStates() {
        // Réinitialiser les états des outils qui ont des méthodes reset
        if (typeof this.resetProtractorState === 'function') {
            this.resetProtractorState();
        }
        if (typeof this.resetArcState === 'function') {
            this.resetArcState();
        }
        
        // Nettoyer les éléments d'affichage
        this.cleanupRulerDisplay();
        this.cleanupCompassDisplay();
        this.cleanupProtractorDisplay();
        this.cleanupArcDisplay();
        
        this.log('🔄 États des outils réinitialisés');
    }

    /**
     * Méthodes d'interface publique
     */
    openFileDialog() {
        console.log('Ouverture dialogue fichier');
    }
    
    showExportDialog() {
        console.log('Affichage dialogue export');
    }
    
    rotateLeft() {
        this.rotation = (this.rotation - 90) % 360;
        this.refreshCurrentView();
    }
    
    rotateRight() {
        this.rotation = (this.rotation + 90) % 360;
        this.refreshCurrentView();
    }
    
    toggleFullscreen() {
        if (!document.fullscreenElement) {
            this.container.requestFullscreen?.();
        } else {
            document.exitFullscreen?.();
        }
    }
    
    async refreshCurrentView() {
        if (this.options.viewMode === 'continuous') {
            await this.renderAllPages();
        } else {
            await this.renderPage(this.currentPage);
        }
    }
    
    async generateThumbnails() {
        if (!this.pdfDoc || !this.currentMode.features.includes('thumbnails')) return;

        this.log('Génération des miniatures...');
        const container = this.elements.thumbnailsContainer;
        if (!container) {
            this.log('Conteneur de miniatures non trouvé');
            return;
        }

        container.innerHTML = '';

        for (let pageNum = 1; pageNum <= this.totalPages; pageNum++) {
            try {
                const page = await this.pdfDoc.getPage(pageNum);
                const viewport = page.getViewport({ scale: 0.15 }); // Échelle réduite pour de meilleures miniatures

                // Créer le conteneur de la miniature
                const thumbnailItem = document.createElement('div');
                thumbnailItem.className = 'thumbnail-item';
                thumbnailItem.dataset.pageNumber = pageNum;

                // Créer le canvas pour la miniature
                const canvas = document.createElement('canvas');
                canvas.width = Math.max(viewport.width, 50); // Taille minimum
                canvas.height = Math.max(viewport.height, 70); // Taille minimum
                canvas.className = 'thumbnail-canvas';
                
                // Style inline pour forcer la visibilité
                canvas.style.maxWidth = '100%';
                canvas.style.border = '1px solid #ccc';
                canvas.style.backgroundColor = '#f0f0f0';

                // Créer l'indicateur de numéro
                const thumbnailNumber = document.createElement('div');
                thumbnailNumber.className = 'thumbnail-number';
                thumbnailNumber.textContent = pageNum;

                // Assembler les éléments
                thumbnailItem.appendChild(canvas);
                thumbnailItem.appendChild(thumbnailNumber);

                // Marquer la première page comme active
                if (pageNum === 1) {
                    thumbnailItem.classList.add('active');
                }

                // Ajouter l'événement de clic
                thumbnailItem.addEventListener('click', () => {
                    if (this.options.viewMode === 'continuous') {
                        this.scrollToPage(pageNum);
                    } else {
                        this.goToPage(pageNum);
                    }
                });

                // Ajouter le menu contextuel (clic droit)
                thumbnailItem.addEventListener('contextmenu', (e) => {
                    e.preventDefault();
                    this.showThumbnailContextMenu(e, pageNum);
                });

                // Appui long pour desktop et mobile
                let pressTimer;
                let isLongPress = false;

                // Gérer l'appui long avec mousedown/mouseup (desktop)
                thumbnailItem.addEventListener('mousedown', (e) => {
                    // Ignorer le clic droit (bouton 2)
                    if (e.button === 2) return;
                    
                    isLongPress = false;
                    pressTimer = setTimeout(() => {
                        isLongPress = true;
                        this.showThumbnailContextMenu(e, pageNum);
                        this.log(`👆 Appui long détecté sur miniature ${pageNum}`);
                    }, 500); // 500ms pour l'appui long
                });

                thumbnailItem.addEventListener('mouseup', (e) => {
                    clearTimeout(pressTimer);
                    
                    // Empêcher le clic normal si c'était un appui long
                    if (isLongPress) {
                        e.preventDefault();
                        e.stopPropagation();
                    }
                });

                thumbnailItem.addEventListener('mouseleave', () => {
                    clearTimeout(pressTimer);
                });

                // Appui long tactile pour mobile
                let touchTimer;
                let isTouchLongPress = false;

                thumbnailItem.addEventListener('touchstart', (e) => {
                    isTouchLongPress = false;
                    touchTimer = setTimeout(() => {
                        isTouchLongPress = true;
                        this.showThumbnailContextMenu(e, pageNum);
                        this.log(`📱 Appui long tactile détecté sur miniature ${pageNum}`);
                    }, 500); // 500ms pour l'appui long
                });

                thumbnailItem.addEventListener('touchend', (e) => {
                    clearTimeout(touchTimer);
                    
                    // Empêcher le clic normal si c'était un appui long tactile
                    if (isTouchLongPress) {
                        e.preventDefault();
                        e.stopPropagation();
                    }
                });

                thumbnailItem.addEventListener('touchmove', () => {
                    clearTimeout(touchTimer);
                    isTouchLongPress = false;
                });

                // Ajouter au conteneur
                container.appendChild(thumbnailItem);

                // Rendre la page sur le canvas APRÈS l'avoir ajouté au DOM
                const ctx = canvas.getContext('2d');
                this.log(`Rendu miniature ${pageNum} - Canvas: ${canvas.width}x${canvas.height}`);
                
                // Dessiner un rectangle de test d'abord
                ctx.fillStyle = '#e0e0e0';
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                ctx.fillStyle = '#333';
                ctx.font = '12px Arial';
                ctx.fillText(`Page ${pageNum}`, 5, 15);
                
                try {
                    await page.render({ canvasContext: ctx, viewport }).promise;
                    this.log(`Miniature ${pageNum} rendue avec succès`);
                } catch (renderError) {
                    this.log(`Erreur rendu miniature ${pageNum}:`, renderError);
                    // En cas d'erreur, laisser le rectangle de test
                }

                this.log(`Miniature ${pageNum} générée et rendue`);
            } catch (error) {
                this.log('Erreur génération miniature page', pageNum, error);
            }
        }

        this.log('Toutes les miniatures générées');
    }
    
    searchPrevious() {
        // Navigation recherche précédente
        console.log('Recherche précédente');
    }
    
    searchNext() {
        // Navigation recherche suivante
        console.log('Recherche suivante');
    }
    
    initTouchGestures() {
        // Initialisation des gestes tactiles
        console.log('Gestes tactiles initialisés');
    }

    // =====================================================
    // MÉTHODES OUTIL FLÈCHE
    // =====================================================

    /**
     * Crée l'élément d'affichage de la longueur de la flèche
     */
    createArrowLengthElement() {
        this.arrowLengthElement = document.createElement('div');
        this.arrowLengthElement.className = 'measurement-display arrow-length';
        this.arrowLengthElement.style.position = 'absolute';
        this.arrowLengthElement.style.background = 'rgba(0, 0, 0, 0.8)';
        this.arrowLengthElement.style.color = 'white';
        this.arrowLengthElement.style.padding = '4px 8px';
        this.arrowLengthElement.style.borderRadius = '4px';
        this.arrowLengthElement.style.fontSize = '12px';
        this.arrowLengthElement.style.fontFamily = 'monospace';
        this.arrowLengthElement.style.pointerEvents = 'none';
        this.arrowLengthElement.style.zIndex = '1000';
        this.arrowLengthElement.style.whiteSpace = 'nowrap';
        this.arrowLengthElement.textContent = '0.0 cm';
        
        this.container.appendChild(this.arrowLengthElement);
        this.log('📏 Élément de longueur de flèche créé');
    }

    /**
     * Dessine la prévisualisation de la flèche
     */
    drawArrowPreview(pageNum) {
        const pageElement = this.pageElements.get(pageNum);
        if (!pageElement?.annotationCtx || !this.arrowCanvasState) return;

        const ctx = pageElement.annotationCtx;
        
        // Restaurer l'état du canvas
        ctx.putImageData(this.arrowCanvasState, 0, 0);
        
        // Dessiner la flèche en prévisualisation
        this.drawArrow(ctx, this.arrowStartPoint, this.arrowEndPoint, true);
    }

    /**
     * Dessine une flèche entre deux points
     */
    drawArrow(ctx, start, end, isPreview = false) {
        if (!start || !end) return;

        ctx.save();
        
        // Style de la flèche
        ctx.strokeStyle = this.currentColor;
        ctx.fillStyle = this.currentColor;
        ctx.lineWidth = this.currentLineWidth;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        
        if (isPreview) {
            // Style pointillé pour la prévisualisation
            ctx.setLineDash([5, 5]);
            ctx.globalAlpha = 0.7;
        }

        // Calculer l'angle de la flèche
        const dx = end.x - start.x;
        const dy = end.y - start.y;
        const angle = Math.atan2(dy, dx);
        
        // Longueur de la pointe de flèche
        const arrowHeadLength = Math.min(20, Math.sqrt(dx * dx + dy * dy) * 0.3);
        const arrowHeadAngle = Math.PI / 6; // 30 degrés

        // Dessiner la ligne principale
        ctx.beginPath();
        ctx.moveTo(start.x, start.y);
        ctx.lineTo(end.x, end.y);
        ctx.stroke();

        // Dessiner la pointe de flèche
        if (arrowHeadLength > 0) {
            ctx.beginPath();
            
            // Pointe gauche
            const leftX = end.x - arrowHeadLength * Math.cos(angle - arrowHeadAngle);
            const leftY = end.y - arrowHeadLength * Math.sin(angle - arrowHeadAngle);
            
            // Pointe droite
            const rightX = end.x - arrowHeadLength * Math.cos(angle + arrowHeadAngle);
            const rightY = end.y - arrowHeadLength * Math.sin(angle + arrowHeadAngle);
            
            // Dessiner le triangle de la pointe
            ctx.moveTo(end.x, end.y);
            ctx.lineTo(leftX, leftY);
            ctx.lineTo(rightX, rightY);
            ctx.closePath();
            ctx.fill();
        }

        ctx.restore();
    }

    /**
     * Met à jour l'affichage de la longueur de la flèche
     */
    updateArrowLength(pageNum) {
        if (!this.arrowLengthElement || !this.arrowStartPoint || !this.arrowEndPoint) return;

        const pageElement = this.pageElements.get(pageNum);
        if (!pageElement?.annotationCanvas) return;

        // Calculer la longueur en pixels
        const dx = this.arrowEndPoint.x - this.arrowStartPoint.x;
        const dy = this.arrowEndPoint.y - this.arrowStartPoint.y;
        const lengthPixels = Math.sqrt(dx * dx + dy * dy);
        
        // Convertir en centimètres (approximation : 96 DPI = 37.8 pixels par cm)
        const lengthCm = lengthPixels / 37.8;
        
        // Mettre à jour le texte
        this.arrowLengthElement.textContent = `${lengthCm.toFixed(1)} cm`;
        
        // Positionner l'élément au milieu de la flèche
        const canvas = pageElement.annotationCanvas;
        const canvasRect = canvas.getBoundingClientRect();
        const containerRect = this.container.getBoundingClientRect();
        
        const midX = (this.arrowStartPoint.x + this.arrowEndPoint.x) / 2;
        const midY = (this.arrowStartPoint.y + this.arrowEndPoint.y) / 2;
        
        const screenX = canvasRect.left - containerRect.left + midX;
        const screenY = canvasRect.top - containerRect.top + midY - 25; // Décalage vers le haut
        
        this.arrowLengthElement.style.left = `${screenX}px`;
        this.arrowLengthElement.style.top = `${screenY}px`;
        this.arrowLengthElement.style.display = 'block';
    }

    /**
     * Finalise la flèche et la dessine définitivement
     */
    finalizeArrow(pageNum) {
        const pageElement = this.pageElements.get(pageNum);
        if (!pageElement?.annotationCtx || !this.arrowStartPoint || !this.arrowEndPoint) return;

        const ctx = pageElement.annotationCtx;
        
        // Dessiner la flèche finale (sans prévisualisation)
        this.drawArrow(ctx, this.arrowStartPoint, this.arrowEndPoint, false);
        
        this.log('➡️ Flèche finalisée');
    }

    /**
     * Nettoie l'affichage de la flèche
     */
    cleanupArrowDisplay() {
        if (this.arrowLengthElement) {
            this.arrowLengthElement.remove();
            this.arrowLengthElement = null;
        }
        
        // Reset des points et de l'état
        this.arrowStartPoint = null;
        this.arrowEndPoint = null;
        this.arrowCanvasState = null;
        
        this.log('🧹 Affichage flèche nettoyé');
    }

    // =====================================================
    // MÉTHODES OUTIL RECTANGLE
    // =====================================================

    /**
     * Crée l'élément d'affichage des dimensions du rectangle
     */
    createRectangleMeasureElement() {
        this.rectangleMeasureElement = document.createElement('div');
        this.rectangleMeasureElement.className = 'measurement-display rectangle-dimensions';
        this.rectangleMeasureElement.style.position = 'absolute';
        this.rectangleMeasureElement.style.background = 'rgba(0, 0, 0, 0.8)';
        this.rectangleMeasureElement.style.color = 'white';
        this.rectangleMeasureElement.style.padding = '4px 8px';
        this.rectangleMeasureElement.style.borderRadius = '4px';
        this.rectangleMeasureElement.style.fontSize = '12px';
        this.rectangleMeasureElement.style.fontFamily = 'monospace';
        this.rectangleMeasureElement.style.pointerEvents = 'none';
        this.rectangleMeasureElement.style.zIndex = '1000';
        this.rectangleMeasureElement.style.whiteSpace = 'nowrap';
        this.rectangleMeasureElement.textContent = '0.0 × 0.0 cm';
        
        this.container.appendChild(this.rectangleMeasureElement);
        this.log('📐 Élément de dimensions du rectangle créé');
    }

    /**
     * Dessine la prévisualisation du rectangle
     */
    drawRectanglePreview(pageNum) {
        const pageElement = this.pageElements.get(pageNum);
        if (!pageElement?.annotationCtx || !this.rectangleCanvasState) return;

        const ctx = pageElement.annotationCtx;
        
        // Restaurer l'état du canvas
        ctx.putImageData(this.rectangleCanvasState, 0, 0);
        
        // Dessiner le rectangle en prévisualisation
        this.drawRectangle(ctx, this.rectangleStartPoint, this.rectangleEndPoint, true);
    }

    /**
     * Dessine un rectangle entre deux points
     */
    drawRectangle(ctx, start, end, isPreview = false) {
        if (!start || !end) return;

        ctx.save();
        
        // Style du rectangle
        ctx.fillStyle = this.currentColor;
        ctx.strokeStyle = this.currentColor;
        ctx.lineWidth = this.currentLineWidth;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        
        if (isPreview) {
            // Style pointillé pour la prévisualisation avec transparence
            ctx.setLineDash([5, 5]);
            ctx.globalAlpha = 0.5;
        }

        // Calculer les dimensions
        const width = end.x - start.x;
        const height = end.y - start.y;

        // Dessiner le rectangle plein
        ctx.beginPath();
        ctx.rect(start.x, start.y, width, height);
        
        if (isPreview) {
            // En prévisualisation, juste le contour pointillé
            ctx.stroke();
        } else {
            // En final, rectangle plein
            ctx.fill();
        }

        ctx.restore();
    }

    /**
     * Met à jour l'affichage des dimensions du rectangle
     */
    updateRectangleMeasure(pageNum) {
        if (!this.rectangleMeasureElement || !this.rectangleStartPoint || !this.rectangleEndPoint) return;

        const pageElement = this.pageElements.get(pageNum);
        if (!pageElement?.annotationCanvas) return;

        // Calculer les dimensions en pixels
        const widthPixels = Math.abs(this.rectangleEndPoint.x - this.rectangleStartPoint.x);
        const heightPixels = Math.abs(this.rectangleEndPoint.y - this.rectangleStartPoint.y);
        
        // Convertir en centimètres (approximation : 96 DPI = 37.8 pixels par cm)
        const widthCm = widthPixels / 37.8;
        const heightCm = heightPixels / 37.8;
        
        // Mettre à jour le texte
        this.rectangleMeasureElement.textContent = `${widthCm.toFixed(1)} × ${heightCm.toFixed(1)} cm`;
        
        // Positionner l'élément au centre du rectangle
        const canvas = pageElement.annotationCanvas;
        const canvasRect = canvas.getBoundingClientRect();
        const containerRect = this.container.getBoundingClientRect();
        
        const centerX = (this.rectangleStartPoint.x + this.rectangleEndPoint.x) / 2;
        const centerY = (this.rectangleStartPoint.y + this.rectangleEndPoint.y) / 2;
        
        const screenX = canvasRect.left - containerRect.left + centerX;
        const screenY = canvasRect.top - containerRect.top + centerY - 25; // Décalage vers le haut
        
        this.rectangleMeasureElement.style.left = `${screenX}px`;
        this.rectangleMeasureElement.style.top = `${screenY}px`;
        this.rectangleMeasureElement.style.display = 'block';
    }

    /**
     * Finalise le rectangle et le dessine définitivement
     */
    finalizeRectangle(pageNum) {
        const pageElement = this.pageElements.get(pageNum);
        if (!pageElement?.annotationCtx || !this.rectangleStartPoint || !this.rectangleEndPoint) return;

        const ctx = pageElement.annotationCtx;
        
        // Restaurer l'état propre du canvas (sans prévisualisation)
        if (this.rectangleCanvasState) {
            ctx.putImageData(this.rectangleCanvasState, 0, 0);
        }
        
        // Dessiner le rectangle final (sans prévisualisation)
        this.drawRectangle(ctx, this.rectangleStartPoint, this.rectangleEndPoint, false);
        
        this.log('⬜ Rectangle finalisé');
    }

    /**
     * Nettoie l'affichage du rectangle
     */
    cleanupRectangleDisplay() {
        if (this.rectangleMeasureElement) {
            this.rectangleMeasureElement.remove();
            this.rectangleMeasureElement = null;
        }
        
        // Reset des points et de l'état
        this.rectangleStartPoint = null;
        this.rectangleEndPoint = null;
        this.rectangleCanvasState = null;
        
        this.log('🧹 Affichage rectangle nettoyé');
    }

    // =====================================================
    // MÉTHODES OUTIL CERCLE
    // =====================================================

    /**
     * Crée l'élément d'affichage du rayon du cercle
     */
    createCircleMeasureElement() {
        this.circleMeasureElement = document.createElement('div');
        this.circleMeasureElement.className = 'measurement-display circle-radius';
        this.circleMeasureElement.style.position = 'absolute';
        this.circleMeasureElement.style.background = 'rgba(0, 0, 0, 0.8)';
        this.circleMeasureElement.style.color = 'white';
        this.circleMeasureElement.style.padding = '4px 8px';
        this.circleMeasureElement.style.borderRadius = '4px';
        this.circleMeasureElement.style.fontSize = '12px';
        this.circleMeasureElement.style.fontFamily = 'monospace';
        this.circleMeasureElement.style.pointerEvents = 'none';
        this.circleMeasureElement.style.zIndex = '1000';
        this.circleMeasureElement.style.whiteSpace = 'nowrap';
        this.circleMeasureElement.textContent = 'r: 0.0 cm';
        
        this.container.appendChild(this.circleMeasureElement);
        this.log('🔵 Élément de rayon du cercle créé');
    }

    /**
     * Dessine la prévisualisation du cercle
     */
    drawCirclePreview(pageNum) {
        const pageElement = this.pageElements.get(pageNum);
        if (!pageElement?.annotationCtx || !this.circleCanvasState) return;

        const ctx = pageElement.annotationCtx;
        
        // Restaurer l'état du canvas
        ctx.putImageData(this.circleCanvasState, 0, 0);
        
        // Dessiner le cercle en prévisualisation
        this.drawCircle(ctx, this.circleStartPoint, this.circleEndPoint, true);
    }

    /**
     * Dessine un cercle entre deux points (centre et point sur la circonférence)
     */
    drawCircle(ctx, center, edge, isPreview = false) {
        if (!center || !edge) return;

        ctx.save();
        
        // Style du cercle
        ctx.fillStyle = this.currentColor;
        ctx.strokeStyle = this.currentColor;
        ctx.lineWidth = this.currentLineWidth;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        
        if (isPreview) {
            // Style pointillé pour la prévisualisation avec transparence
            ctx.setLineDash([5, 5]);
            ctx.globalAlpha = 0.5;
        }

        // Calculer le rayon
        const dx = edge.x - center.x;
        const dy = edge.y - center.y;
        const radius = Math.sqrt(dx * dx + dy * dy);

        // Dessiner le cercle
        ctx.beginPath();
        ctx.arc(center.x, center.y, radius, 0, 2 * Math.PI);
        
        if (isPreview) {
            // En prévisualisation, juste le contour pointillé
            ctx.stroke();
        } else {
            // En final, cercle plein
            ctx.fill();
        }

        // Dessiner le rayon en pointillé si c'est une prévisualisation
        if (isPreview && radius > 0) {
            ctx.save();
            ctx.setLineDash([2, 2]);
            ctx.globalAlpha = 0.3;
            ctx.beginPath();
            ctx.moveTo(center.x, center.y);
            ctx.lineTo(edge.x, edge.y);
            ctx.stroke();
            ctx.restore();
        }

        ctx.restore();
    }

    /**
     * Met à jour l'affichage du rayon du cercle
     */
    updateCircleMeasure(pageNum) {
        if (!this.circleMeasureElement || !this.circleStartPoint || !this.circleEndPoint) return;

        const pageElement = this.pageElements.get(pageNum);
        if (!pageElement?.annotationCanvas) return;

        // Calculer le rayon en pixels
        const dx = this.circleEndPoint.x - this.circleStartPoint.x;
        const dy = this.circleEndPoint.y - this.circleStartPoint.y;
        const radiusPixels = Math.sqrt(dx * dx + dy * dy);
        
        // Convertir en centimètres (approximation : 96 DPI = 37.8 pixels par cm)
        const radiusCm = radiusPixels / 37.8;
        
        // Mettre à jour le texte
        this.circleMeasureElement.textContent = `r: ${radiusCm.toFixed(1)} cm`;
        
        // Positionner l'élément au milieu du rayon
        const canvas = pageElement.annotationCanvas;
        const canvasRect = canvas.getBoundingClientRect();
        const containerRect = this.container.getBoundingClientRect();
        
        const midX = (this.circleStartPoint.x + this.circleEndPoint.x) / 2;
        const midY = (this.circleStartPoint.y + this.circleEndPoint.y) / 2;
        
        const screenX = canvasRect.left - containerRect.left + midX;
        const screenY = canvasRect.top - containerRect.top + midY - 25; // Décalage vers le haut
        
        this.circleMeasureElement.style.left = `${screenX}px`;
        this.circleMeasureElement.style.top = `${screenY}px`;
        this.circleMeasureElement.style.display = 'block';
    }

    /**
     * Finalise le cercle et le dessine définitivement
     */
    finalizeCircle(pageNum) {
        const pageElement = this.pageElements.get(pageNum);
        if (!pageElement?.annotationCtx || !this.circleStartPoint || !this.circleEndPoint) return;

        const ctx = pageElement.annotationCtx;
        
        // Restaurer l'état propre du canvas (sans prévisualisation)
        if (this.circleCanvasState) {
            ctx.putImageData(this.circleCanvasState, 0, 0);
        }
        
        // Dessiner le cercle final (sans prévisualisation)
        this.drawCircle(ctx, this.circleStartPoint, this.circleEndPoint, false);
        
        this.log('⭕ Cercle finalisé');
    }

    /**
     * Nettoie l'affichage du cercle
     */
    cleanupCircleDisplay() {
        if (this.circleMeasureElement) {
            this.circleMeasureElement.remove();
            this.circleMeasureElement = null;
        }
        
        // Reset des points et de l'état
        this.circleStartPoint = null;
        this.circleEndPoint = null;
        this.circleCanvasState = null;
        
        this.log('🧹 Affichage cercle nettoyé');
    }

    /**
     * Bascule l'affichage de la grille pour une page
     */
    toggleGridDisplay(pageNum) {
        const pageElement = this.pageElements.get(pageNum);
        if (!pageElement) return;

        const isVisible = this.gridVisible.get(pageNum) || false;
        
        if (isVisible) {
            this.drawGrid(pageNum);
        } else {
            this.clearGrid(pageNum);
        }
    }

    /**
     * Dessine la grille sur une page
     */
    drawGrid(pageNum) {
        const pageElement = this.pageElements.get(pageNum);
        if (!pageElement?.annotationCtx) return;

        const ctx = pageElement.annotationCtx;
        const canvas = pageElement.annotationCanvas;
        
        // Configurer le style de la grille
        ctx.save();
        ctx.strokeStyle = this.gridColor;
        ctx.globalAlpha = this.gridOpacity;
        ctx.lineWidth = 1;
        ctx.setLineDash([]);

        // Dessiner les lignes verticales
        for (let x = 0; x <= canvas.width; x += this.gridSize) {
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, canvas.height);
            ctx.stroke();
        }

        // Dessiner les lignes horizontales
        for (let y = 0; y <= canvas.height; y += this.gridSize) {
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(canvas.width, y);
            ctx.stroke();
        }

        ctx.restore();
        this.log(`🔲 Grille dessinée sur page ${pageNum} (taille: ${this.gridSize}px)`);
    }

    /**
     * Efface uniquement la grille d'une page (sans toucher aux autres annotations)
     */
    clearGrid(pageNum) {
        const pageElement = this.pageElements.get(pageNum);
        if (!pageElement?.annotationCtx) return;

        // Re-rendre les annotations sans la grille
        this.renderPageAnnotations(pageNum);
        this.log(`🧹 Grille effacée de la page ${pageNum}`);
    }

    /**
     * Affiche le menu contextuel pour les miniatures
     */
    showThumbnailContextMenu(event, pageNumber) {
        // Debug: vérifier le mapping
        const thumbnailElement = event.target.closest('.thumbnail-item');
        const displayPageNumber = thumbnailElement?.dataset.pageNumber;
        const originalPageNumber = thumbnailElement?.dataset.originalPageNumber;
        
        this.log(`🔍 DEBUG Menu contextuel - pageNumber reçu: ${pageNumber}, displayPageNumber: ${displayPageNumber}, originalPageNumber: ${originalPageNumber}`);
        
        // Utiliser le numéro d'affichage plutôt que le pageNumber passé en paramètre
        const correctPageNumber = displayPageNumber ? parseInt(displayPageNumber) : pageNumber;
        
        // Supprimer tout menu existant
        this.hideThumbnailContextMenu();

        // Créer le menu contextuel
        const contextMenu = document.createElement('div');
        contextMenu.className = 'thumbnail-context-menu';
        contextMenu.innerHTML = `
            <div class="context-menu-item delete-page" data-action="delete">
                <i class="fas fa-trash"></i>
                <span>Supprimer la page</span>
            </div>
            <div class="context-menu-item add-page" data-action="add">
                <i class="fas fa-plus"></i>
                <span>Ajouter page blanche après</span>
            </div>
        `;

        // Positionner le menu
        const x = event.clientX || event.touches?.[0]?.clientX || 0;
        const y = event.clientY || event.touches?.[0]?.clientY || 0;
        
        contextMenu.style.position = 'fixed';
        contextMenu.style.left = `${x}px`;
        contextMenu.style.top = `${y}px`;
        contextMenu.style.zIndex = '10000';

        // Ajouter au DOM
        document.body.appendChild(contextMenu);
        this.currentContextMenu = contextMenu;
        this.contextMenuPageNumber = correctPageNumber;

        // Ajouter les événements pour les options du menu
        contextMenu.addEventListener('click', (e) => {
            const action = e.target.closest('.context-menu-item')?.dataset.action;
            if (action === 'delete') {
                this.deletePage(correctPageNumber);
            } else if (action === 'add') {
                this.addBlankPageAfter(correctPageNumber);
            }
            this.hideThumbnailContextMenu();
        });

        // Fermer le menu si on clique ailleurs
        setTimeout(() => {
            document.addEventListener('click', this.hideContextMenuHandler);
        }, 100);

        this.log(`📋 Menu contextuel affiché pour page ${correctPageNumber}`);
    }

    /**
     * Cache le menu contextuel
     */
    hideThumbnailContextMenu() {
        if (this.currentContextMenu) {
            this.currentContextMenu.remove();
            this.currentContextMenu = null;
            this.contextMenuPageNumber = null;
            document.removeEventListener('click', this.hideContextMenuHandler);
        }
    }

    /**
     * Gestionnaire pour fermer le menu contextuel
     */
    hideContextMenuHandler = () => {
        this.hideThumbnailContextMenu();
    }

    /**
     * Supprime une page du PDF
     */
    async deletePage(pageNumber) {
        if (this.totalPages <= 1) {
            alert('Impossible de supprimer la dernière page du document.');
            return;
        }

        // Identifier le type de page (originale ou blanche)
        const pageIdentifier = this.getPageIdentifier(pageNumber);
        
        this.log(`🔍 DEBUG suppression - pageNumber: ${pageNumber}, type: ${pageIdentifier.type}, identifier: ${JSON.stringify(pageIdentifier)}`);

        if (confirm(`Êtes-vous sûr de vouloir supprimer la page ${pageNumber} ?`)) {
            try {
                if (pageIdentifier.type === 'blank') {
                    // Supprimer une page blanche
                    this.log(`🗑️ Début suppression page blanche ${pageNumber} (ID: ${pageIdentifier.id})`);
                    await this.removeBlankPage(pageIdentifier.id);
                    await this.updateUIAfterBlankPageDeletion();
                    this.log(`✅ Page blanche ${pageNumber} supprimée avec succès`);
                } else {
                    // Supprimer une page originale
                    this.log(`🗑️ Début suppression page originale ${pageNumber} (page ${pageIdentifier.pageNumber})`);
                    await this.removePageFromDocument(pageIdentifier.pageNumber);
                    await this.updateUIAfterPageDeletion(pageIdentifier.pageNumber);
                    this.log(`✅ Page originale ${pageNumber} supprimée avec succès`);
                }
                
            } catch (error) {
                console.error('❌ Erreur lors de la suppression:', error);
                alert('Erreur lors de la suppression de la page. Veuillez réessayer.');
            }
        }
    }

    /**
     * Supprime une page blanche
     */
    async removeBlankPage(blankPageId) {
        this.log(`🗑️ Suppression page blanche ID: ${blankPageId}`);
        
        // Supprimer de la Map des pages ajoutées
        if (this.addedPages.has(blankPageId)) {
            this.addedPages.delete(blankPageId);
            this.log(`✅ Page blanche ${blankPageId} supprimée de addedPages`);
        }
        
        // Mettre à jour le nombre total de pages
        this.totalPages--;
        
        this.log(`📊 Nouveau nombre de pages après suppression page blanche: ${this.totalPages}`);
    }

    /**
     * Met à jour l'interface après suppression d'une page blanche
     */
    async updateUIAfterBlankPageDeletion() {
        this.log(`🖥️ Mise à jour UI après suppression page blanche`);
        
        // Régénérer toutes les miniatures
        await this.regenerateThumbnailsWithAddedPages();
        
        // Mettre à jour la navigation
        this.updateNavigationState();
        
        // Mettre à jour l'affichage
        if (this.options.viewMode === 'continuous') {
            await this.renderAllPagesWithAddedPages();
        } else {
            this.renderPage(this.currentPage);
        }
        
        // Mettre à jour la sélection des miniatures
        this.updateThumbnailSelection();
        
        this.log(`✅ Interface mise à jour après suppression page blanche`);
    }

    /**
     * Convertit un numéro de page d'affichage vers le numéro de page original ou ID de page blanche
     */
    getPageIdentifier(displayPageNumber) {
        this.deletedPages = this.deletedPages || new Set();
        this.addedPages = this.addedPages || new Map();
        
        // Créer la séquence de pages pour trouver la correspondance
        const pageSequence = this.createPageSequence();
        
        if (displayPageNumber > 0 && displayPageNumber <= pageSequence.length) {
            const pageInfo = pageSequence[displayPageNumber - 1];
            
            if (pageInfo.isBlank) {
                this.log(`🔢 Mapping: page affichage ${displayPageNumber} → page blanche ${pageInfo.id}`);
                return { type: 'blank', id: pageInfo.id };
            } else {
                this.log(`🔢 Mapping: page affichage ${displayPageNumber} → page originale ${pageInfo.originalPageNumber}`);
                return { type: 'original', pageNumber: pageInfo.originalPageNumber };
            }
        }
        
        // Fallback vers la première page
        this.log(`🔢 Mapping fallback: page affichage ${displayPageNumber} → page originale 1`);
        return { type: 'original', pageNumber: 1 };
    }

    /**
     * Convertit un numéro de page d'affichage vers le numéro de page original (pour compatibilité)
     */
    getOriginalPageNumber(displayPageNumber) {
        const identifier = this.getPageIdentifier(displayPageNumber);
        if (identifier.type === 'original') {
            return identifier.pageNumber;
        }
        // Si c'est une page blanche, retourner la page originale suivante ou la dernière
        const pageSequence = this.createPageSequence();
        for (let i = displayPageNumber; i < pageSequence.length; i++) {
            if (!pageSequence[i].isBlank) {
                return pageSequence[i].originalPageNumber;
            }
        }
        // Si pas de page originale suivante, retourner la dernière page originale
        return this.pdfDoc.numPages;
    }

    /**
     * Supprime une page du document PDF en interne
     */
    async removePageFromDocument(pageNumber) {
        this.log(`🔄 Suppression page ${pageNumber} du document...`);
        
        // Créer une liste des pages à conserver (toutes sauf celle supprimée)
        this.deletedPages = this.deletedPages || new Set();
        this.deletedPages.add(pageNumber);
        
        // Supprimer l'élément DOM de la page
        const pageElement = this.pageElements.get(pageNumber);
        if (pageElement?.element) {
            pageElement.element.remove();
        }
        
        // Supprimer les annotations de cette page
        this.annotations.delete(pageNumber);
        
        // Supprimer l'historique undo/redo de cette page
        this.undoStack.delete(pageNumber);
        this.redoStack.delete(pageNumber);
        
        // Renumberier les pages qui restent
        await this.renumberPagesAfterDeletion(pageNumber);
        
        // Mettre à jour le nombre total de pages
        this.totalPages--;
        
        this.log(`📊 Nouveau nombre de pages: ${this.totalPages}`);
    }

    /**
     * Renumérote les pages après suppression
     */
    async renumberPagesAfterDeletion(deletedPageNumber) {
        this.log(`🔢 Renumerotation après suppression page ${deletedPageNumber}`);
        
        // Maps temporaires pour stocker les données renumerotées
        const newPages = new Map();
        const newPageElements = new Map();
        const newAnnotations = new Map();
        const newUndoStack = new Map();
        const newRedoStack = new Map();
        
        // Renumeroter toutes les pages suivantes
        for (let oldPageNum = 1; oldPageNum <= this.totalPages + 1; oldPageNum++) {
            let newPageNum = oldPageNum;
            
            // Si c'est une page après celle supprimée, décrémenter le numéro
            if (oldPageNum > deletedPageNumber) {
                newPageNum = oldPageNum - 1;
            }
            // Si c'est la page supprimée, l'ignorer
            else if (oldPageNum === deletedPageNumber) {
                continue;
            }
            
            // Transférer les données avec le nouveau numéro
            if (this.pages.has(oldPageNum)) {
                newPages.set(newPageNum, this.pages.get(oldPageNum));
            }
            
            if (this.pageElements.has(oldPageNum)) {
                const pageElement = this.pageElements.get(oldPageNum);
                // Mettre à jour l'attribut data-page-number
                if (pageElement.element) {
                    pageElement.element.dataset.pageNumber = newPageNum;
                }
                newPageElements.set(newPageNum, pageElement);
            }
            
            if (this.annotations.has(oldPageNum)) {
                newAnnotations.set(newPageNum, this.annotations.get(oldPageNum));
            }
            
            if (this.undoStack.has(oldPageNum)) {
                newUndoStack.set(newPageNum, this.undoStack.get(oldPageNum));
            }
            
            if (this.redoStack.has(oldPageNum)) {
                newRedoStack.set(newPageNum, this.redoStack.get(oldPageNum));
            }
        }
        
        // Remplacer les Maps par les versions renumerotées
        this.pages = newPages;
        this.pageElements = newPageElements;
        this.annotations = newAnnotations;
        this.undoStack = newUndoStack;
        this.redoStack = newRedoStack;
        
        this.log(`✅ Renumerotation terminée`);
    }

    /**
     * Met à jour l'interface utilisateur après suppression
     */
    async updateUIAfterPageDeletion(deletedPageNumber) {
        this.log(`🖥️ Mise à jour UI après suppression page ${deletedPageNumber}`);
        
        // Ajuster la page courante si nécessaire
        if (this.currentPage === deletedPageNumber) {
            // Si on a supprimé la dernière page, aller à la page précédente
            if (deletedPageNumber > this.totalPages) {
                this.currentPage = this.totalPages;
            }
            // Sinon rester sur le même numéro (qui affichera la page suivante)
        } else if (this.currentPage > deletedPageNumber) {
            // Si la page courante était après celle supprimée, la décrémenter
            this.currentPage--;
        }
        
        // Régénérer toutes les miniatures
        await this.regenerateThumbnails();
        
        // Mettre à jour la navigation
        this.updateNavigationState();
        
        // Mettre à jour l'affichage de la page courante
        if (this.options.viewMode === 'continuous') {
            // Utiliser la méthode qui gère toutes les modifications (suppressions ET ajouts)
            if (this.addedPages && this.addedPages.size > 0) {
                await this.renderAllPagesWithAddedPages();
            } else {
                await this.renderRemainingPagesInMainView();
            }
        } else {
            this.renderPage(this.currentPage);
        }
        
        // Mettre à jour la sélection des miniatures
        this.updateThumbnailSelection();
        
        this.log(`✅ Interface mise à jour`);
    }

    /**
     * Régénère toutes les miniatures après modification
     */
    async regenerateThumbnails() {
        this.log('🔄 Régénération des miniatures...');
        
        const container = document.getElementById('thumbnails-container');
        if (!container) return;
        
        // Vider le conteneur
        container.innerHTML = '';
        
        // Si des pages ont été modifiées (supprimées ou ajoutées), utiliser la méthode complète
        if ((this.deletedPages && this.deletedPages.size > 0) || (this.addedPages && this.addedPages.size > 0)) {
            await this.generateThumbnailsWithAllPages();
        } else {
            // Sinon utiliser la méthode standard
            await this.generateThumbnails();
        }
        
        this.log('✅ Miniatures régénérées');
    }

    /**
     * Génère les miniatures uniquement pour les pages qui n'ont pas été supprimées
     */
    async generateThumbnailsForRemainingPages() {
        this.log('📄 Génération des miniatures pour pages restantes...');
        
        const container = document.getElementById('thumbnails-container');
        if (!container || !this.pdfDoc) return;

        this.deletedPages = this.deletedPages || new Set();
        let displayPageNumber = 1;

        // Générer miniatures pour chaque page originale non supprimée
        for (let originalPageNum = 1; originalPageNum <= this.pdfDoc.numPages; originalPageNum++) {
            // Ignorer les pages supprimées
            if (this.deletedPages.has(originalPageNum)) {
                continue;
            }

            // Créer l'élément miniature
            const thumbnailItem = document.createElement('div');
            thumbnailItem.className = 'thumbnail-item';
            thumbnailItem.dataset.pageNumber = displayPageNumber;
            thumbnailItem.dataset.originalPageNumber = originalPageNum;

            const canvas = document.createElement('canvas');
            canvas.className = 'thumbnail-canvas';
            canvas.width = 91;
            canvas.height = 118;

            const thumbnailNumber = document.createElement('div');
            thumbnailNumber.className = 'thumbnail-number';
            thumbnailNumber.textContent = displayPageNumber;

            thumbnailItem.appendChild(canvas);
            thumbnailItem.appendChild(thumbnailNumber);

            // Événement de clic
            thumbnailItem.addEventListener('click', () => {
                if (this.options.viewMode === 'continuous') {
                    this.scrollToPage(displayPageNumber);
                } else {
                    this.goToPage(displayPageNumber);
                }
            });

            // Menu contextuel (clic droit)
            thumbnailItem.addEventListener('contextmenu', (e) => {
                e.preventDefault();
                this.showThumbnailContextMenu(e, displayPageNumber);
            });

            // Appui long pour desktop et mobile
            let pressTimer;
            let isLongPress = false;

            thumbnailItem.addEventListener('mousedown', (e) => {
                if (e.button === 2) return;
                
                isLongPress = false;
                pressTimer = setTimeout(() => {
                    isLongPress = true;
                    this.showThumbnailContextMenu(e, displayPageNumber);
                    this.log(`👆 Appui long détecté sur miniature ${displayPageNumber}`);
                }, 500);
            });

            thumbnailItem.addEventListener('mouseup', (e) => {
                clearTimeout(pressTimer);
                if (isLongPress) {
                    e.preventDefault();
                    e.stopPropagation();
                }
            });

            thumbnailItem.addEventListener('mouseleave', () => {
                clearTimeout(pressTimer);
            });

            // Appui long tactile pour mobile
            let touchTimer;
            let isTouchLongPress = false;

            thumbnailItem.addEventListener('touchstart', (e) => {
                isTouchLongPress = false;
                touchTimer = setTimeout(() => {
                    isTouchLongPress = true;
                    this.showThumbnailContextMenu(e, displayPageNumber);
                    this.log(`📱 Appui long tactile détecté sur miniature ${displayPageNumber}`);
                }, 500);
            });

            thumbnailItem.addEventListener('touchend', (e) => {
                clearTimeout(touchTimer);
                if (isTouchLongPress) {
                    e.preventDefault();
                    e.stopPropagation();
                }
            });

            thumbnailItem.addEventListener('touchmove', () => {
                clearTimeout(touchTimer);
                isTouchLongPress = false;
            });

            // Marquer comme active si c'est la page courante
            if (displayPageNumber === this.currentPage) {
                thumbnailItem.classList.add('active');
            }

            // Ajouter au conteneur
            container.appendChild(thumbnailItem);

            // Rendre la page originale sur le canvas
            try {
                const page = await this.pdfDoc.getPage(originalPageNum);
                const ctx = canvas.getContext('2d');
                const viewport = page.getViewport({ scale: 0.15 });
                
                await page.render({
                    canvasContext: ctx,
                    viewport: viewport
                }).promise;

                this.log(`Miniature ${displayPageNumber} (page originale ${originalPageNum}) générée`);
            } catch (error) {
                console.error(`Erreur rendu miniature ${displayPageNumber}:`, error);
            }

            displayPageNumber++;
        }

        this.log(`✅ ${displayPageNumber - 1} miniatures générées pour pages restantes`);
    }

    /**
     * Rendre les pages restantes dans la vue principale après suppression
     */
    async renderRemainingPagesInMainView() {
        if (!this.pdfDoc) return;

        this.log('🔄 Rendu des pages restantes dans la vue principale...');
        
        // Vider le conteneur principal
        this.elements.pagesContainer.innerHTML = '';
        this.pageElements.clear();

        this.deletedPages = this.deletedPages || new Set();
        let displayPageNumber = 1;

        // Créer et rendre chaque page non supprimée
        for (let originalPageNum = 1; originalPageNum <= this.pdfDoc.numPages; originalPageNum++) {
            // Ignorer les pages supprimées
            if (this.deletedPages.has(originalPageNum)) {
                continue;
            }

            await this.createPageElementForOriginalPage(originalPageNum, displayPageNumber);
            displayPageNumber++;
        }

        // Reconfigurer la détection de page visible
        this.setupPageVisibilityObserver();
        
        // Reconfigurer les outils d'annotation pour toutes les pages
        this.reconfigureAnnotationTools();
        
        this.log(`✅ ${displayPageNumber - 1} pages restantes rendues dans la vue principale`);
    }

    /**
     * Créer un élément de page pour une page originale avec un nouveau numéro d'affichage
     */
    async createPageElementForOriginalPage(originalPageNum, displayPageNum) {
        try {
            const page = await this.pdfDoc.getPage(originalPageNum);
            
            // Calculer les dimensions
            const baseViewport = page.getViewport({ scale: 1.0 });
            const scaledViewport = page.getViewport({ scale: this.currentScale });
            
            // Créer le conteneur de la page
            const pageContainer = document.createElement('div');
            pageContainer.className = 'pdf-page-container';
            pageContainer.dataset.pageNumber = displayPageNum;
            pageContainer.dataset.originalPageNumber = originalPageNum;
            
            // Canvas principal
            const canvas = document.createElement('canvas');
            canvas.className = 'pdf-canvas';
            canvas.width = scaledViewport.width;
            canvas.height = scaledViewport.height;
            
            // Canvas pour annotations
            const annotationCanvas = document.createElement('canvas');
            annotationCanvas.className = 'pdf-annotation-layer';
            annotationCanvas.width = scaledViewport.width;
            annotationCanvas.height = scaledViewport.height;
            
            // Assembler la structure
            pageContainer.appendChild(canvas);
            pageContainer.appendChild(annotationCanvas);
            this.elements.pagesContainer.appendChild(pageContainer);
            
            // Obtenir les contextes
            const ctx = canvas.getContext('2d');
            const annotationCtx = annotationCanvas.getContext('2d');
            
            // Stocker les éléments de page
            const pageElement = {
                element: pageContainer,
                container: pageContainer,
                canvas: canvas,
                annotationCanvas: annotationCanvas,
                ctx: ctx,
                annotationCtx: annotationCtx,
                viewport: scaledViewport,
                originalPageNumber: originalPageNum
            };
            
            this.pageElements.set(displayPageNum, pageElement);
            
            // Rendre la page originale
            await page.render({
                canvasContext: ctx,
                viewport: scaledViewport
            }).promise;
            
            // Initialiser l'historique pour cette page
            this.initializeUndoHistoryForPage(displayPageNum);
            
            this.log(`Page ${displayPageNum} (originale ${originalPageNum}) créée et rendue`);
            
        } catch (error) {
            console.error(`Erreur création page ${displayPageNum}:`, error);
        }
    }

    /**
     * Initialise l'historique undo/redo pour une page spécifique
     */
    initializeUndoHistoryForPage(pageNum) {
        const pageElement = this.pageElements.get(pageNum);
        if (pageElement?.annotationCtx) {
            const ctx = pageElement.annotationCtx;
            const emptyState = ctx.getImageData(0, 0, ctx.canvas.width, ctx.canvas.height);
            
            // Initialiser les stacks pour cette page
            if (!this.undoStack.has(pageNum)) {
                this.undoStack.set(pageNum, []);
            }
            if (!this.redoStack.has(pageNum)) {
                this.redoStack.set(pageNum, []);
            }
            
            // Ajouter l'état vide initial
            this.undoStack.get(pageNum).push(emptyState);
            this.log(`📄 Historique initialisé pour page ${pageNum}`);
            
            this.updateUndoRedoButtons();
        }
    }

    /**
     * Ajoute une page blanche après la page spécifiée
     */
    async addBlankPageAfter(pageNumber) {
        this.log(`📄 Début ajout page blanche après la page ${pageNumber}`);
        
        // Convertir le numéro de page d'affichage vers le numéro original
        const originalPageNumber = this.getOriginalPageNumber(pageNumber);
        
        this.log(`🔍 DEBUG ajout - pageNumber: ${pageNumber}, originalPageNumber: ${originalPageNumber}`);

        if (confirm(`Ajouter une page blanche après la page ${pageNumber} ?`)) {
            try {
                // Créer et insérer la page blanche
                await this.insertBlankPageAfter(originalPageNumber);
                
                // Mettre à jour l'interface utilisateur
                await this.updateUIAfterPageInsertion(originalPageNumber);
                
                this.log(`✅ Page blanche ajoutée après la page ${pageNumber}`);
                
            } catch (error) {
                console.error('❌ Erreur lors de l\'ajout de page blanche:', error);
                alert('Erreur lors de l\'ajout de la page blanche. Veuillez réessayer.');
            }
        }
    }

    /**
     * Insère une page blanche après la page originale spécifiée
     */
    async insertBlankPageAfter(originalPageNumber) {
        this.log(`📄 Insertion page blanche après page originale ${originalPageNumber}`);
        
        // Initialiser le système de pages ajoutées si nécessaire
        this.addedPages = this.addedPages || new Map();
        
        // Générer un identifiant unique pour la page blanche
        const blankPageId = `blank_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        
        // Créer les données de la page blanche
        const blankPageData = {
            id: blankPageId,
            isBlank: true,
            insertAfter: originalPageNumber,
            width: 595, // Taille A4 standard en points
            height: 842,
            createdAt: new Date().toISOString()
        };
        
        // Stocker la page blanche
        this.addedPages.set(blankPageId, blankPageData);
        
        // Mettre à jour le nombre total de pages
        this.totalPages++;
        
        this.log(`📊 Page blanche créée avec ID: ${blankPageId}, nouveau total: ${this.totalPages} pages`);
    }

    /**
     * Met à jour l'interface utilisateur après insertion de page
     */
    async updateUIAfterPageInsertion(originalPageNumber) {
        this.log(`🖥️ Mise à jour UI après insertion page blanche après ${originalPageNumber}`);
        
        // Régénérer toutes les miniatures avec les pages ajoutées
        await this.regenerateThumbnailsWithAddedPages();
        
        // Mettre à jour la navigation
        this.updateNavigationState();
        
        // Mettre à jour l'affichage de la page courante
        if (this.options.viewMode === 'continuous') {
            await this.renderAllPagesWithAddedPages();
        } else {
            this.renderPage(this.currentPage);
        }
        
        // Mettre à jour la sélection des miniatures
        this.updateThumbnailSelection();
        
        this.log(`✅ Interface mise à jour après insertion`);
    }

    /**
     * Régénère les miniatures en incluant les pages ajoutées
     */
    async regenerateThumbnailsWithAddedPages() {
        this.log('🔄 Régénération miniatures avec pages ajoutées...');
        
        const container = document.getElementById('thumbnails-container');
        if (!container) return;
        
        // Vider le conteneur
        container.innerHTML = '';
        
        // Générer les miniatures dans l'ordre correct
        await this.generateThumbnailsWithAllPages();
        
        this.log('✅ Miniatures avec pages ajoutées régénérées');
    }

    /**
     * Génère les miniatures pour toutes les pages (originales, supprimées, ajoutées)
     */
    async generateThumbnailsWithAllPages() {
        this.log('📄 Génération miniatures avec toutes les pages...');
        
        const container = document.getElementById('thumbnails-container');
        if (!container || !this.pdfDoc) return;

        this.deletedPages = this.deletedPages || new Set();
        this.addedPages = this.addedPages || new Map();
        
        let displayPageNumber = 1;
        
        // Créer une liste ordonnée de toutes les pages
        const pageSequence = this.createPageSequence();
        
        // Générer miniatures pour chaque page dans la séquence
        for (const pageInfo of pageSequence) {
            if (pageInfo.isBlank) {
                // Créer miniature pour page blanche
                await this.createBlankThumbnail(displayPageNumber, pageInfo.id);
            } else {
                // Créer miniature pour page originale
                await this.createOriginalThumbnail(displayPageNumber, pageInfo.originalPageNumber);
            }
            displayPageNumber++;
        }
        
        this.log(`✅ ${displayPageNumber - 1} miniatures générées avec toutes les pages`);
    }

    /**
     * Crée la séquence ordonnée de toutes les pages
     */
    createPageSequence() {
        const sequence = [];
        
        this.log('🔄 Création séquence de pages...');
        this.log(`📊 Pages supprimées: ${this.deletedPages ? Array.from(this.deletedPages).join(', ') : 'aucune'}`);
        this.log(`📊 Pages ajoutées: ${this.addedPages ? this.addedPages.size : 0}`);
        
        // Parcourir toutes les pages originales
        for (let originalPageNum = 1; originalPageNum <= this.pdfDoc.numPages; originalPageNum++) {
            // Ajouter la page originale si elle n'est pas supprimée
            if (!this.deletedPages.has(originalPageNum)) {
                sequence.push({
                    isBlank: false,
                    originalPageNumber: originalPageNum
                });
                this.log(`📄 Ajouté page originale ${originalPageNum} en position ${sequence.length}`);
            } else {
                this.log(`❌ Page originale ${originalPageNum} ignorée (supprimée)`);
            }
            
            // Ajouter les pages blanches insérées après cette page
            for (const [blankId, blankData] of this.addedPages) {
                if (blankData.insertAfter === originalPageNum) {
                    sequence.push({
                        isBlank: true,
                        id: blankId,
                        blankData: blankData
                    });
                    this.log(`📄 Ajouté page blanche ${blankId} en position ${sequence.length} (après page ${originalPageNum})`);
                }
            }
        }
        
        this.log(`✅ Séquence créée avec ${sequence.length} pages`);
        return sequence;
    }

    /**
     * Crée une miniature pour une page blanche
     */
    async createBlankThumbnail(displayPageNum, blankPageId) {
        const container = document.getElementById('thumbnails-container');
        
        // Créer l'élément miniature
        const thumbnailItem = document.createElement('div');
        thumbnailItem.className = 'thumbnail-item blank-page';
        thumbnailItem.dataset.pageNumber = displayPageNum;
        thumbnailItem.dataset.blankPageId = blankPageId;

        const canvas = document.createElement('canvas');
        canvas.className = 'thumbnail-canvas';
        canvas.width = 91;
        canvas.height = 118;

        const thumbnailNumber = document.createElement('div');
        thumbnailNumber.className = 'thumbnail-number';
        thumbnailNumber.textContent = displayPageNum;

        thumbnailItem.appendChild(canvas);
        thumbnailItem.appendChild(thumbnailNumber);

        // Dessiner une page blanche
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = 'white';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.strokeStyle = '#ddd';
        ctx.lineWidth = 1;
        ctx.strokeRect(0, 0, canvas.width, canvas.height);
        
        // Ajouter une indication visuelle que c'est une page blanche
        ctx.fillStyle = '#999';
        ctx.font = '12px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('Page', canvas.width / 2, canvas.height / 2 - 5);
        ctx.fillText('blanche', canvas.width / 2, canvas.height / 2 + 10);

        // Ajouter les événements
        this.addThumbnailEvents(thumbnailItem, displayPageNum);

        // Marquer comme active si c'est la page courante
        if (displayPageNum === this.currentPage) {
            thumbnailItem.classList.add('active');
        }

        // Ajouter au conteneur
        container.appendChild(thumbnailItem);

        this.log(`Miniature page blanche ${displayPageNum} (ID: ${blankPageId}) créée`);
    }

    /**
     * Crée une miniature pour une page originale
     */
    async createOriginalThumbnail(displayPageNum, originalPageNum) {
        const container = document.getElementById('thumbnails-container');
        
        // Créer l'élément miniature
        const thumbnailItem = document.createElement('div');
        thumbnailItem.className = 'thumbnail-item';
        thumbnailItem.dataset.pageNumber = displayPageNum;
        thumbnailItem.dataset.originalPageNumber = originalPageNum;

        const canvas = document.createElement('canvas');
        canvas.className = 'thumbnail-canvas';
        canvas.width = 91;
        canvas.height = 118;

        const thumbnailNumber = document.createElement('div');
        thumbnailNumber.className = 'thumbnail-number';
        thumbnailNumber.textContent = displayPageNum;

        thumbnailItem.appendChild(canvas);
        thumbnailItem.appendChild(thumbnailNumber);

        // Ajouter les événements
        this.addThumbnailEvents(thumbnailItem, displayPageNum);

        // Marquer comme active si c'est la page courante
        if (displayPageNum === this.currentPage) {
            thumbnailItem.classList.add('active');
        }

        // Ajouter au conteneur
        container.appendChild(thumbnailItem);

        // Rendre la page originale sur le canvas
        try {
            const page = await this.pdfDoc.getPage(originalPageNum);
            const ctx = canvas.getContext('2d');
            const viewport = page.getViewport({ scale: 0.15 });
            
            await page.render({
                canvasContext: ctx,
                viewport: viewport
            }).promise;

            this.log(`Miniature ${displayPageNum} (page originale ${originalPageNum}) générée`);
        } catch (error) {
            console.error(`Erreur rendu miniature ${displayPageNum}:`, error);
        }
    }

    /**
     * Ajoute les événements aux miniatures
     */
    addThumbnailEvents(thumbnailItem, displayPageNum) {
        // Événement de clic
        thumbnailItem.addEventListener('click', () => {
            if (this.options.viewMode === 'continuous') {
                this.scrollToPage(displayPageNum);
            } else {
                this.goToPage(displayPageNum);
            }
        });

        // Menu contextuel (clic droit)
        thumbnailItem.addEventListener('contextmenu', (e) => {
            e.preventDefault();
            this.showThumbnailContextMenu(e, displayPageNum);
        });

        // Appui long pour desktop et mobile
        let pressTimer;
        let isLongPress = false;

        thumbnailItem.addEventListener('mousedown', (e) => {
            if (e.button === 2) return;
            
            isLongPress = false;
            pressTimer = setTimeout(() => {
                isLongPress = true;
                this.showThumbnailContextMenu(e, displayPageNum);
                this.log(`👆 Appui long détecté sur miniature ${displayPageNum}`);
            }, 500);
        });

        thumbnailItem.addEventListener('mouseup', (e) => {
            clearTimeout(pressTimer);
            if (isLongPress) {
                e.preventDefault();
                e.stopPropagation();
            }
        });

        thumbnailItem.addEventListener('mouseleave', () => {
            clearTimeout(pressTimer);
        });

        // Appui long tactile pour mobile
        let touchTimer;
        let isTouchLongPress = false;

        thumbnailItem.addEventListener('touchstart', (e) => {
            isTouchLongPress = false;
            touchTimer = setTimeout(() => {
                isTouchLongPress = true;
                this.showThumbnailContextMenu(e, displayPageNum);
                this.log(`📱 Appui long tactile détecté sur miniature ${displayPageNum}`);
            }, 500);
        });

        thumbnailItem.addEventListener('touchend', (e) => {
            clearTimeout(touchTimer);
            if (isTouchLongPress) {
                e.preventDefault();
                e.stopPropagation();
            }
        });

        thumbnailItem.addEventListener('touchmove', () => {
            clearTimeout(touchTimer);
            isTouchLongPress = false;
        });
    }

    /**
     * Rendre toutes les pages avec les pages ajoutées
     */
    async renderAllPagesWithAddedPages() {
        if (!this.pdfDoc) return;

        this.log('🔄 Rendu de toutes les pages avec pages ajoutées...');
        
        // Vider le conteneur principal
        this.elements.pagesContainer.innerHTML = '';
        this.pageElements.clear();

        const pageSequence = this.createPageSequence();
        let displayPageNumber = 1;

        // Créer et rendre chaque page dans la séquence
        for (const pageInfo of pageSequence) {
            if (pageInfo.isBlank) {
                await this.createBlankPageElement(displayPageNumber, pageInfo.id);
            } else {
                await this.createPageElementForOriginalPage(pageInfo.originalPageNumber, displayPageNumber);
            }
            displayPageNumber++;
        }

        // Reconfigurer la détection de page visible
        this.setupPageVisibilityObserver();
        
        // Reconfigurer les outils d'annotation pour toutes les pages
        this.reconfigureAnnotationTools();
        
        this.log(`✅ ${displayPageNumber - 1} pages rendues avec pages ajoutées`);
    }

    /**
     * Crée un élément de page pour une page blanche
     */
    async createBlankPageElement(displayPageNum, blankPageId) {
        try {
            const blankData = this.addedPages.get(blankPageId);
            
            // Calculer les dimensions
            const scaledWidth = blankData.width * this.currentScale;
            const scaledHeight = blankData.height * this.currentScale;
            
            // Créer le conteneur de la page
            const pageContainer = document.createElement('div');
            pageContainer.className = 'pdf-page-container blank-page';
            pageContainer.dataset.pageNumber = displayPageNum;
            pageContainer.dataset.blankPageId = blankPageId;
            
            // Canvas principal
            const canvas = document.createElement('canvas');
            canvas.className = 'pdf-canvas';
            canvas.width = scaledWidth;
            canvas.height = scaledHeight;
            
            // Canvas pour annotations
            const annotationCanvas = document.createElement('canvas');
            annotationCanvas.className = 'pdf-annotation-layer';
            annotationCanvas.width = scaledWidth;
            annotationCanvas.height = scaledHeight;
            
            // Assembler la structure
            pageContainer.appendChild(canvas);
            pageContainer.appendChild(annotationCanvas);
            this.elements.pagesContainer.appendChild(pageContainer);
            
            // Obtenir les contextes
            const ctx = canvas.getContext('2d');
            const annotationCtx = annotationCanvas.getContext('2d');
            
            // Dessiner une page blanche
            ctx.fillStyle = 'white';
            ctx.fillRect(0, 0, scaledWidth, scaledHeight);
            ctx.strokeStyle = '#ddd';
            ctx.lineWidth = 1;
            ctx.strokeRect(0, 0, scaledWidth, scaledHeight);
            
            // Stocker les éléments de page
            const pageElement = {
                element: pageContainer,
                container: pageContainer,
                canvas: canvas,
                annotationCanvas: annotationCanvas,
                ctx: ctx,
                annotationCtx: annotationCtx,
                viewport: { width: scaledWidth, height: scaledHeight },
                isBlank: true,
                blankPageId: blankPageId
            };
            
            this.pageElements.set(displayPageNum, pageElement);
            
            // Initialiser l'historique pour cette page
            this.initializeUndoHistoryForPage(displayPageNum);
            
            this.log(`Page blanche ${displayPageNum} (ID: ${blankPageId}) créée et rendue`);
            
        } catch (error) {
            console.error(`Erreur création page blanche ${displayPageNum}:`, error);
        }
    }

    /**
     * Reconfigure les outils d'annotation après régénération des pages
     */
    reconfigureAnnotationTools() {
        this.log('🔧 Reconfiguration des outils d\'annotation...');
        
        // Réactiver l'outil courant pour toutes les pages
        this.setCurrentTool(this.currentTool);
        
        this.log(`✅ Outils d'annotation reconfigurés pour l'outil: ${this.currentTool}`);
    }
}

// Export pour utilisation ES6 modules (optionnel)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = UnifiedPDFViewer;
}

// Rendre la classe disponible globalement pour utilisation dans le navigateur
if (typeof window !== 'undefined') {
    window.UnifiedPDFViewer = UnifiedPDFViewer;
}