// Fonctions utilitaires pour les calendriers

// Formater une date au format YYYY-MM-DD
function formatDateISO(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

// Obtenir le nom du jour en français
function getDayName(dayIndex) {
    const days = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi'];
    return days[dayIndex];
}

// Obtenir le nom du mois en français
function getMonthName(monthIndex) {
    const months = [
        'janvier', 'février', 'mars', 'avril', 'mai', 'juin',
        'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'
    ];
    return months[monthIndex];
}

// Calculer le numéro de semaine
function getWeekNumber(date) {
    const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
    const dayNum = d.getUTCDay() || 7;
    d.setUTCDate(d.getUTCDate() + 4 - dayNum);
    const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
    return Math.ceil((((d - yearStart) / 86400000) + 1) / 7);
}

// Obtenir les dates de la semaine
function getWeekDates(date) {
    const week = [];
    const startDate = new Date(date);
    const dayOfWeek = startDate.getDay();
    const diff = dayOfWeek === 0 ? -6 : 1 - dayOfWeek; // Ajuster pour commencer le lundi

    startDate.setDate(startDate.getDate() + diff);

    for (let i = 0; i < 5; i++) { // Lundi à Vendredi
        const day = new Date(startDate);
        day.setDate(startDate.getDate() + i);
        week.push(day);
    }

    return week;
}

// Vérifier si deux dates sont le même jour
function isSameDay(date1, date2) {
    return date1.getFullYear() === date2.getFullYear() &&
           date1.getMonth() === date2.getMonth() &&
           date1.getDate() === date2.getDate();
}

// Créer un élément de classe pour l'affichage
function createClassElement(classroom, title = null) {
    const div = document.createElement('div');
    div.className = 'class-block';
    div.style.backgroundColor = classroom.color;

    const nameDiv = document.createElement('div');
    nameDiv.className = 'class-name';
    nameDiv.textContent = classroom.name;
    div.appendChild(nameDiv);

    if (classroom.subject) {
        const subjectDiv = document.createElement('div');
        subjectDiv.className = 'class-subject';
        subjectDiv.textContent = classroom.subject;
        div.appendChild(subjectDiv);
    }

    if (title) {
        const titleDiv = document.createElement('div');
        titleDiv.className = 'planning-title';
        titleDiv.textContent = title;
        div.appendChild(titleDiv);
    }

    return div;
}

// Gestion des tooltips
function initTooltips() {
    const tooltipElements = document.querySelectorAll('[title]');
    tooltipElements.forEach(element => {
        const title = element.getAttribute('title');
        element.removeAttribute('title');

        element.addEventListener('mouseenter', (e) => {
            showTooltip(e.target, title);
        });

        element.addEventListener('mouseleave', () => {
            hideTooltip();
        });
    });
}

function showTooltip(element, text) {
    hideTooltip(); // Cacher tout tooltip existant

    const tooltip = document.createElement('div');
    tooltip.className = 'calendar-tooltip';
    tooltip.textContent = text;
    document.body.appendChild(tooltip);

    const rect = element.getBoundingClientRect();
    tooltip.style.left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';
    tooltip.style.top = rect.top - tooltip.offsetHeight - 5 + 'px';

    // Ajuster si le tooltip sort de l'écran
    if (tooltip.offsetLeft < 0) {
        tooltip.style.left = '5px';
    } else if (tooltip.offsetLeft + tooltip.offsetWidth > window.innerWidth) {
        tooltip.style.left = window.innerWidth - tooltip.offsetWidth - 5 + 'px';
    }

    if (tooltip.offsetTop < 0) {
        tooltip.style.top = rect.bottom + 5 + 'px';
    }
}

function hideTooltip() {
    const tooltip = document.querySelector('.calendar-tooltip');
    if (tooltip) {
        tooltip.remove();
    }
}

// Gestion du scroll synchronisé pour les vues multiples
function initSynchronizedScroll() {
    const scrollContainers = document.querySelectorAll('.sync-scroll');

    scrollContainers.forEach(container => {
        container.addEventListener('scroll', () => {
            const scrollTop = container.scrollTop;
            const scrollLeft = container.scrollLeft;

            scrollContainers.forEach(otherContainer => {
                if (otherContainer !== container) {
                    if (container.classList.contains('sync-vertical')) {
                        otherContainer.scrollTop = scrollTop;
                    }
                    if (container.classList.contains('sync-horizontal')) {
                        otherContainer.scrollLeft = scrollLeft;
                    }
                }
            });
        });
    });
}

// Raccourcis clavier
function initKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Ctrl/Cmd + flèches pour naviguer entre les semaines
        if (e.ctrlKey || e.metaKey) {
            switch(e.key) {
                case 'ArrowLeft':
                    e.preventDefault();
                    if (typeof navigateWeek === 'function') {
                        navigateWeek('prev');
                    }
                    break;
                case 'ArrowRight':
                    e.preventDefault();
                    if (typeof navigateWeek === 'function') {
                        navigateWeek('next');
                    }
                    break;
                case 'ArrowUp':
                    e.preventDefault();
                    if (typeof navigateToToday === 'function') {
                        navigateToToday();
                    }
                    break;
            }
        }
    });
}

// Impression du calendrier
function printCalendar() {
    window.print();
}

// Initialisation au chargement de la page
document.addEventListener('DOMContentLoaded', function() {
    initTooltips();
    initSynchronizedScroll();
    initKeyboardShortcuts();
});

// Export des fonctions pour utilisation dans d'autres scripts
window.calendarUtils = {
    formatDateISO,
    getDayName,
    getMonthName,
    getWeekNumber,
    getWeekDates,
    isSameDay,
    createClassElement,
    printCalendar
};
