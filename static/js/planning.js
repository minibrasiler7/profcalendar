// Gestion de la planification des cours
let currentPlanningData = {};

// Ouvrir le modal de planification
function openPlanningModal(cell, fromAnnualView = false) {
    currentPlanningCell = cell;
    const date = cell.dataset.date;
    const period = cell.dataset.period;

    // Si c'est depuis la vue annuelle, ouvrir le modal de planification journalière
    if (fromAnnualView) {
        openDayPlanningModal(date);
        return;
    }

    // Vérifier si la période est passée de plus de 24h
    const isPastPeriod = isPeriodPast(date, period);

    // Récupérer les données existantes
    getPlanningData(date, period).then(data => {
        if (data.success && data.planning) {
            document.getElementById('modalClassroom').value = data.planning.classroom_id || '';
            document.getElementById('modalPlanningTitle').value = data.planning.title || '';

            // Si la période est passée, afficher la description avec les indicateurs
            if (isPastPeriod && data.planning.description) {
                displayPastPeriodDescription(data.planning.description, data.planning.checklist_states);
            } else {
                document.getElementById('modalDescription').value = data.planning.description || '';
            }
        } else {
            // Réinitialiser le formulaire
            document.getElementById('modalClassroom').value = '';
            document.getElementById('modalPlanningTitle').value = '';
            document.getElementById('modalDescription').value = '';
        }

        // Adapter l'interface selon si la période est passée ou non
        const descriptionContainer = document.querySelector('.modal-body .form-group:last-child');
        const saveButton = document.querySelector('.modal-footer .btn-primary');

        if (isPastPeriod) {
            // Mode lecture seule pour les périodes passées
            document.getElementById('modalClassroom').disabled = true;
            document.getElementById('modalPlanningTitle').disabled = true;
            descriptionContainer.innerHTML = `
                <label class="form-label">Description</label>
                <div id="pastPeriodDescription" class="past-period-description"></div>
            `;
            saveButton.style.display = 'none';
        } else {
            // Mode édition normal
            document.getElementById('modalClassroom').disabled = false;
            document.getElementById('modalPlanningTitle').disabled = false;
            if (!descriptionContainer.querySelector('textarea')) {
                descriptionContainer.innerHTML = `
                    <label class="form-label">Description</label>
                    <textarea id="modalDescription" class="form-control" rows="3"
                              placeholder="Détails du cours, exercices prévus..."></textarea>
                    <div class="checklist-help" style="font-size: 0.75rem; color: var(--gray-color); margin-top: 0.5rem; font-style: italic;">
                        Astuce : Commencez une ligne par "-" pour créer une case à cocher
                    </div>
                `;
                // Réattacher l'événement de conversion des tirets
                attachDashConversion();
            }
            saveButton.style.display = '';
        }

        // Mettre à jour le titre du modal
        const dateObj = new Date(date);
        const dateStr = dateObj.toLocaleDateString('fr-FR', {
            weekday: 'long',
            day: 'numeric',
            month: 'long'
        });
        document.getElementById('modalTitle').textContent = `Planifier - ${dateStr} - Période ${period}`;

        // Afficher le modal
        document.getElementById('planningModal').classList.add('show');
    });
}

// Vérifier si une période est passée de plus de 24h
function isPeriodPast(date, periodNumber) {
    const now = new Date();
    const periodDate = new Date(date);

    // Obtenir l'heure de fin de la période depuis les données
    const period = periodsData.find(p => p.number === parseInt(periodNumber));
    if (period) {
        const [hours, minutes] = period.end.split(':');
        periodDate.setHours(parseInt(hours), parseInt(minutes), 0, 0);
    }

    // Vérifier si c'est passé de plus de 24h
    const diffHours = (now - periodDate) / (1000 * 60 * 60);
    return diffHours > 24;
}

// Afficher la description pour une période passée avec indicateurs visuels
function displayPastPeriodDescription(description, checklistStates = {}) {
    const container = document.getElementById('pastPeriodDescription');
    if (!container) return;

    const lines = description.split('\n');
    let html = '';
    let checkboxIndex = 0;

    for (const line of lines) {
        const checkboxMatch = line.match(/^(\s*)\[([ x])\]\s*(.*)$/i);

        if (checkboxMatch) {
            const indent = checkboxMatch[1];
            const content = checkboxMatch[3];
            const isChecked = checklistStates[checkboxIndex.toString()] || false;

            if (isChecked) {
                html += `<div class="checklist-item completed" style="margin-left: ${indent.length * 20}px; color: #10B981;">
                    <i class="fas fa-check-circle" style="margin-right: 0.5rem;"></i>
                    <span style="text-decoration: line-through;">${escapeHtml(content)}</span>
                </div>`;
            } else {
                html += `<div class="checklist-item not-completed" style="margin-left: ${indent.length * 20}px; color: #EF4444;">
                    <i class="fas fa-times-circle" style="margin-right: 0.5rem;"></i>
                    <span>${escapeHtml(content)}</span>
                </div>`;
            }
            checkboxIndex++;
        } else {
            html += `<div style="margin: 0.5rem 0;">${escapeHtml(line)}</div>`;
        }
    }

    container.innerHTML = html || '<p style="color: var(--gray-color);">Aucune description</p>';
}

// Fonction pour échapper le HTML
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

// Attacher l'événement de conversion des tirets en checkboxes
function attachDashConversion() {
    const textarea = document.getElementById('modalDescription');
    if (!textarea) return;

    textarea.addEventListener('input', function(e) {
        const cursorPos = textarea.selectionStart;
        const value = textarea.value;

        // Vérifier si on vient de taper un tiret en début de ligne
        if (e.inputType === 'insertText' && e.data === '-') {
            const lines = value.substring(0, cursorPos).split('\n');
            const currentLine = lines[lines.length - 1];

            // Si le tiret est au début de la ligne (avec éventuellement des espaces avant)
            if (currentLine.trim() === '-') {
                e.preventDefault();

                // Remplacer le tiret par [ ]
                const beforeCursor = value.substring(0, cursorPos - 1);
                const afterCursor = value.substring(cursorPos);
                const spaces = currentLine.match(/^\s*/)[0]; // Préserver l'indentation

                textarea.value = beforeCursor + spaces + '[ ] ' + afterCursor;

                // Placer le curseur après [ ]
                const newCursorPos = cursorPos - 1 + spaces.length + 4;
                textarea.setSelectionRange(newCursorPos, newCursorPos);
            }
        }
    });
}

// Ouvrir le modal de planification journalière
function openDayPlanningModal(date, classroomId = null) {
    // Créer un modal pour planifier toute la journée
    const modal = document.createElement('div');
    modal.className = 'planning-modal show';
    modal.style.zIndex = '1001';
    modal.innerHTML = `
        <div class="modal-content" style="max-width: 600px; max-height: 90vh; overflow-y: auto;">
            <div class="modal-header">
                <h3>Planifier pour le ${new Date(date).toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' })}</h3>
                <button class="modal-close" onclick="closeDayPlanningModal(this)">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="modal-body">
                <div id="dayPlanningContainer" style="display: flex; flex-direction: column; gap: 1.5rem;">
                    <div class="loading-spinner" style="text-align: center; padding: 2rem;">
                        <i class="fas fa-spinner fa-spin fa-2x"></i>
                        <p>Chargement des périodes...</p>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-outline" onclick="closeDayPlanningModal(this)">Annuler</button>
                <button class="btn btn-primary" onclick="saveDayPlanning('${date}', this)">
                    <i class="fas fa-save"></i> Enregistrer tout
                </button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    // Charger les périodes et les plannings existants
    loadDayPeriods(date, classroomId);
}

// Charger les périodes de la journée
async function loadDayPeriods(date, filterByClassroomId = null) {
    try {
        const response = await fetch(`/planning/get_available_periods/${date}`);
        const data = await response.json();

        const container = document.getElementById('dayPlanningContainer');
        container.innerHTML = '';

        if (data.success && data.periods) {
            const weekday = new Date(date).getDay();
            const adjustedWeekday = weekday === 0 ? 6 : weekday - 1; // Convertir dimanche=0 en 6, lundi=1 en 0, etc.

            // Si on filtre par classe, on récupère le nom de la classe
            let classroomName = '';
            if (filterByClassroomId) {
                const classroom = classrooms.find(c => c.id === parseInt(filterByClassroomId));
                if (classroom) {
                    classroomName = classroom.name;

                    // Ajouter un titre indiquant la classe
                    const titleDiv = document.createElement('div');
                    titleDiv.style.cssText = 'padding: 1rem; background-color: #EFF6FF; border-radius: 0.5rem; margin-bottom: 1rem;';
                    titleDiv.innerHTML = `
                        <p style="margin: 0; color: #1E40AF; font-weight: 500;">
                            <i class="fas fa-info-circle"></i>
                            Planification pour la classe <strong>${classroom.name} - ${classroom.subject}</strong>
                        </p>
                    `;
                    container.appendChild(titleDiv);
                }
            }

            // Debug: afficher les informations reçues
            console.log('FilterByClassroomId:', filterByClassroomId);
            console.log('Periods data:', data.periods);

            let hasRelevantPeriods = false;

            for (const period of data.periods) {
                // Debug: afficher les informations de chaque période
                console.log(`Period ${period.number}:`, {
                    hasSchedule: period.hasSchedule,
                    defaultClassroom: period.defaultClassroom,
                    filterByClassroomId: filterByClassroomId
                });

                // Si on filtre par classe, vérifier si cette période a cette classe dans l'horaire type
                if (filterByClassroomId) {
                    // Comparer en s'assurant que les deux valeurs sont du même type
                    const periodClassroomId = period.defaultClassroom ? parseInt(period.defaultClassroom) : null;
                    const filterClassroomId = parseInt(filterByClassroomId);

                    if (!period.hasSchedule || periodClassroomId !== filterClassroomId) {
                        console.log(`Skipping period ${period.number} - no match`);
                        continue; // Passer cette période si ce n'est pas la bonne classe
                    }
                }

                hasRelevantPeriods = true;

                // Vérifier si cette période est passée
                const isPast = isPeriodPast(date, period.number);

                // Charger les données existantes pour chaque période
                const planningResponse = await fetch(`/planning/get_planning/${date}/${period.number}`);
                const planningData = await planningResponse.json();

                let existingClassroomId = '';
                let existingTitle = '';
                let existingDescription = '';
                let existingChecklistStates = {};

                if (planningData.success && planningData.planning) {
                    existingClassroomId = planningData.planning.classroom_id || '';
                    existingTitle = planningData.planning.title || '';
                    existingDescription = planningData.planning.description || '';
                    existingChecklistStates = planningData.planning.checklist_states || {};
                } else if (period.hasSchedule && period.defaultClassroom) {
                    // Utiliser l'horaire type par défaut
                    existingClassroomId = period.defaultClassroom;
                }

                // Si on filtre par classe, pré-sélectionner cette classe
                if (filterByClassroomId && !existingClassroomId) {
                    existingClassroomId = filterByClassroomId;
                }

                const periodDiv = document.createElement('div');
                periodDiv.className = 'period-planning-section';
                periodDiv.style.cssText = 'border: 1px solid #e5e7eb; border-radius: 0.5rem; padding: 1rem; background-color: #f9fafb;';

                if (isPast) {
                    // Affichage pour période passée
                    periodDiv.innerHTML = `
                        <h4 style="margin-bottom: 1rem; color: #4b5563; display: flex; align-items: center; gap: 0.5rem;">
                            <i class="fas fa-clock"></i>
                            Période ${period.number} (${period.start} - ${period.end})
                            <span style="font-size: 0.75rem; color: #6B7280; margin-left: auto;">Période terminée</span>
                        </h4>

                        <div class="form-group">
                            <label class="form-label">Classe</label>
                            <input type="text" class="form-control" value="${classrooms.find(c => c.id == existingClassroomId)?.name || 'Aucune classe'}" disabled>
                        </div>

                        <div class="form-group">
                            <label class="form-label">Titre du cours</label>
                            <input type="text" class="form-control" value="${existingTitle}" disabled>
                        </div>

                        <div class="form-group">
                            <label class="form-label">Description</label>
                            <div class="past-period-description" id="past-desc-${period.number}"></div>
                        </div>
                    `;

                    container.appendChild(periodDiv);

                    // Afficher la description formatée pour période passée
                    if (existingDescription) {
                        setTimeout(() => {
                            displayPastPeriodDescriptionInContainer(existingDescription, existingChecklistStates, `past-desc-${period.number}`);
                        }, 0);
                    }
                } else {
                    // Affichage normal pour période future
                    periodDiv.innerHTML = `
                        <h4 style="margin-bottom: 1rem; color: #4b5563; display: flex; align-items: center; gap: 0.5rem;">
                            <i class="fas fa-clock"></i>
                            Période ${period.number} (${period.start} - ${period.end})
                        </h4>

                        <div class="form-group">
                            <label class="form-label">Classe</label>
                            <select class="form-control" data-period="${period.number}" data-field="classroom">
                                <option value="">-- Pas de cours --</option>
                                ${classrooms.map(c => `
                                    <option value="${c.id}" ${existingClassroomId == c.id ? 'selected' : ''}>
                                        ${c.name} - ${c.subject}
                                    </option>
                                `).join('')}
                            </select>
                        </div>

                        <div class="form-group">
                            <label class="form-label">Titre du cours</label>
                            <input type="text" class="form-control"
                                   data-period="${period.number}"
                                   data-field="title"
                                   value="${existingTitle}"
                                   placeholder="Ex: Introduction aux fractions">
                        </div>

                        <div class="form-group">
                            <label class="form-label">Description</label>
                            <textarea class="form-control day-planning-description" rows="2"
                                      data-period="${period.number}"
                                      data-field="description"
                                      placeholder="Détails du cours, exercices prévus...">${existingDescription}</textarea>
                            <div class="checklist-help" style="font-size: 0.75rem; color: var(--gray-color); margin-top: 0.5rem; font-style: italic;">
                                Astuce : Commencez une ligne par "-" pour créer une case à cocher
                            </div>
                        </div>
                    `;

                    container.appendChild(periodDiv);
                }
            }

            // Attacher les événements de conversion des tirets pour toutes les textareas
            attachDashConversionToAll();

            if (!hasRelevantPeriods && filterByClassroomId) {
                container.innerHTML = `
                    <div style="text-align: center; padding: 2rem; color: #6B7280;">
                        <i class="fas fa-calendar-times" style="font-size: 3rem; margin-bottom: 1rem; opacity: 0.5;"></i>
                        <p>Aucune période avec ${classroomName || 'cette classe'} ce jour-là selon votre horaire type.</p>
                        <p style="font-size: 0.875rem; margin-top: 0.5rem;">Vérifiez que vous avez bien configuré cette classe dans votre horaire type pour ce jour de la semaine.</p>
                    </div>
                `;
            } else if (!hasRelevantPeriods) {
                container.innerHTML = '<p>Aucune période disponible pour cette date.</p>';
            }
        } else {
            container.innerHTML = '<p>Aucune période disponible pour cette date.</p>';
        }
    } catch (error) {
        console.error('Erreur lors du chargement des périodes:', error);
        document.getElementById('dayPlanningContainer').innerHTML = '<p>Erreur lors du chargement des périodes.</p>';
    }
}

// Afficher la description formatée dans un container spécifique
function displayPastPeriodDescriptionInContainer(description, checklistStates, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const lines = description.split('\n');
    let html = '';
    let checkboxIndex = 0;

    for (const line of lines) {
        const checkboxMatch = line.match(/^(\s*)\[([ x])\]\s*(.*)$/i);

        if (checkboxMatch) {
            const indent = checkboxMatch[1];
            const content = checkboxMatch[3];
            const isChecked = checklistStates[checkboxIndex.toString()] || false;

            if (isChecked) {
                html += `<div class="checklist-item completed" style="margin-left: ${indent.length * 20}px; color: #10B981;">
                    <i class="fas fa-check-circle" style="margin-right: 0.5rem;"></i>
                    <span style="text-decoration: line-through;">${escapeHtml(content)}</span>
                </div>`;
            } else {
                html += `<div class="checklist-item not-completed" style="margin-left: ${indent.length * 20}px; color: #EF4444;">
                    <i class="fas fa-times-circle" style="margin-right: 0.5rem;"></i>
                    <span>${escapeHtml(content)}</span>
                </div>`;
            }
            checkboxIndex++;
        } else {
            html += `<div style="margin: 0.5rem 0;">${escapeHtml(line)}</div>`;
        }
    }

    container.innerHTML = html || '<p style="color: var(--gray-color);">Aucune description</p>';
}

// Attacher la conversion des tirets à toutes les textareas de planification journalière
function attachDashConversionToAll() {
    const textareas = document.querySelectorAll('.day-planning-description');
    textareas.forEach(textarea => {
        textarea.addEventListener('input', function(e) {
            const cursorPos = textarea.selectionStart;
            const value = textarea.value;

            // Vérifier si on vient de taper un tiret en début de ligne
            if (e.inputType === 'insertText' && e.data === '-') {
                const lines = value.substring(0, cursorPos).split('\n');
                const currentLine = lines[lines.length - 1];

                // Si le tiret est au début de la ligne (avec éventuellement des espaces avant)
                if (currentLine.trim() === '-') {
                    e.preventDefault();

                    // Remplacer le tiret par [ ]
                    const beforeCursor = value.substring(0, cursorPos - 1);
                    const afterCursor = value.substring(cursorPos);
                    const spaces = currentLine.match(/^\s*/)[0]; // Préserver l'indentation

                    textarea.value = beforeCursor + spaces + '[ ] ' + afterCursor;

                    // Placer le curseur après [ ]
                    const newCursorPos = cursorPos - 1 + spaces.length + 4;
                    textarea.setSelectionRange(newCursorPos, newCursorPos);
                }
            }
        });
    });
}

// Fermer le modal de planification journalière
function closeDayPlanningModal(element) {
    element.closest('.planning-modal').remove();
}

// Sauvegarder toutes les planifications de la journée
async function saveDayPlanning(date, buttonElement) {
    const modal = buttonElement.closest('.planning-modal');
    const container = modal.querySelector('#dayPlanningContainer');

    // Désactiver le bouton pendant la sauvegarde
    buttonElement.disabled = true;
    buttonElement.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Enregistrement...';

    let hasErrors = false;

    // Parcourir toutes les périodes
    const periodSections = container.querySelectorAll('.period-planning-section');

    for (const section of periodSections) {
        const classroomSelect = section.querySelector('select[data-field="classroom"]');
        const titleInput = section.querySelector('input[data-field="title"]');
        const descriptionTextarea = section.querySelector('textarea[data-field="description"]');

        // Ignorer les sections en lecture seule (périodes passées)
        if (!classroomSelect || !titleInput || !descriptionTextarea) {
            continue;
        }

        const period = classroomSelect.dataset.period;
        const classroomId = classroomSelect.value;
        const title = titleInput.value;
        const description = descriptionTextarea.value;

        // Calculer les états des checkboxes
        const checklistStates = calculateChecklistStates(description);

        // Sauvegarder uniquement si une classe est sélectionnée
        if (classroomId || title || description) {
            try {
                const response = await fetch('/planning/save_planning', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: JSON.stringify({
                        date: date,
                        period_number: parseInt(period),
                        classroom_id: classroomId ? parseInt(classroomId) : null,
                        title: title,
                        description: description,
                        checklist_states: checklistStates
                    })
                });

                const result = await response.json();

                if (!result.success) {
                    hasErrors = true;
                    console.error(`Erreur pour la période ${period}:`, result.message);
                }
            } catch (error) {
                hasErrors = true;
                console.error(`Erreur lors de la sauvegarde de la période ${period}:`, error);
            }
        }
    }

    if (hasErrors) {
        showNotification('error', 'Certaines planifications n\'ont pas pu être sauvegardées');
        buttonElement.disabled = false;
        buttonElement.innerHTML = '<i class="fas fa-save"></i> Enregistrer tout';
    } else {
        showNotification('success', 'Toutes les planifications ont été enregistrées');
        modal.remove();
        // Recharger la page pour afficher les changements
        location.reload();
    }
}

// Calculer les états initiaux des checkboxes (tous non cochés par défaut)
function calculateChecklistStates(description) {
    const states = {};
    if (!description) return states;

    const lines = description.split('\n');
    let checkboxIndex = 0;

    for (const line of lines) {
        if (line.match(/^(\s*)\[([ x])\]\s*(.*)$/i)) {
            // Par défaut, les nouvelles checkboxes sont non cochées
            states[checkboxIndex.toString()] = false;
            checkboxIndex++;
        }
    }

    return states;
}

// Fermer le modal
function closePlanningModal() {
    document.getElementById('planningModal').classList.remove('show');
    currentPlanningCell = null;
}

// Sauvegarder la planification
async function savePlanning() {
    if (!currentPlanningCell) return;

    const date = currentPlanningCell.dataset.date;
    const period = currentPlanningCell.dataset.period;
    const classroomId = document.getElementById('modalClassroom').value;
    const title = document.getElementById('modalPlanningTitle').value;
    const description = document.getElementById('modalDescription').value;

    // Calculer les états des checkboxes
    const checklistStates = calculateChecklistStates(description);

    try {
        const response = await fetch('/planning/save_planning', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
                date: date,
                period_number: parseInt(period),
                classroom_id: classroomId ? parseInt(classroomId) : null,
                title: title,
                description: description,
                checklist_states: checklistStates
            })
        });

        const result = await response.json();

        if (result.success) {
            // Recharger la page pour afficher les changements
            location.reload();
        } else {
            showNotification('error', result.message || 'Erreur lors de la sauvegarde');
        }
    } catch (error) {
        console.error('Erreur:', error);
        showNotification('error', 'Erreur lors de la sauvegarde');
    }
}

// Récupérer les données de planification
async function getPlanningData(date, period) {
    try {
        const response = await fetch(`/planning/get_planning/${date}/${period}`, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });

        return await response.json();
    } catch (error) {
        console.error('Erreur:', error);
        return { success: false };
    }
}

// Charger les planifications de la semaine
function loadWeeklyPlannings() {
    // Cette fonction peut être étendue pour charger dynamiquement
    // les planifications via AJAX si nécessaire
}

// Gérer le clic en dehors du modal
document.addEventListener('click', (e) => {
    const modal = document.getElementById('planningModal');
    if (e.target === modal) {
        closePlanningModal();
    }
});

// Gérer la touche Escape
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closePlanningModal();
    }
});

// Mettre à jour la couleur de fond du select en fonction de la classe sélectionnée
document.addEventListener('DOMContentLoaded', function() {
    const classroomSelect = document.getElementById('modalClassroom');
    if (classroomSelect) {
        classroomSelect.addEventListener('change', function() {
            const selectedOption = this.options[this.selectedIndex];
            if (selectedOption && selectedOption.dataset.color) {
                this.style.backgroundColor = selectedOption.dataset.color + '20'; // Ajouter transparence
            } else {
                this.style.backgroundColor = '';
            }
        });
    }

    // Attacher la conversion des tirets au modal principal
    attachDashConversion();
});

// Fonction pour synchroniser les vues
function syncViews(date, period, classroomId) {
    // Cette fonction peut être étendue pour synchroniser
    // la vue hebdomadaire et annuelle en temps réel

    // Pour l'instant, on recharge la page
    // Dans une version plus avancée, on pourrait utiliser WebSockets
    // ou des requêtes AJAX pour une mise à jour en temps réel
}

// Gestion du drag & drop (pour une future amélioration)
function initDragAndDrop() {
    // Permettre de glisser-déposer des planifications
    // entre différentes cellules
}

// Export des planifications (pour une future amélioration)
function exportPlannings(format) {
    // Exporter en PDF, Excel ou iCal
}

// Import des planifications (pour une future amélioration)
function importPlannings() {
    // Importer depuis un fichier
}
