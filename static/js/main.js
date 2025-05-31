// Gestion des messages flash
document.addEventListener('DOMContentLoaded', function() {
    // Auto-fermeture des messages flash après 5 secondes
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(message => {
        setTimeout(() => {
            message.style.opacity = '0';
            setTimeout(() => message.remove(), 300);
        }, 5000);
    });

    // Gestion du dropdown utilisateur
    const userDropdown = document.querySelector('.user-dropdown');
    if (userDropdown) {
        const userBtn = userDropdown.querySelector('.user-btn');
        const dropdownMenu = userDropdown.querySelector('.dropdown-menu');

        userBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            dropdownMenu.style.display = dropdownMenu.style.display === 'block' ? 'none' : 'block';
        });

        // Fermer le dropdown en cliquant ailleurs
        document.addEventListener('click', () => {
            if (dropdownMenu) {
                dropdownMenu.style.display = 'none';
            }
        });
    }
});

// Fonction utilitaire pour les requêtes AJAX
async function fetchJSON(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
    };

    try {
        const response = await fetch(url, { ...defaultOptions, ...options });
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.message || 'Une erreur est survenue');
        }

        return data;
    } catch (error) {
        console.error('Erreur:', error);
        showNotification('error', error.message);
        throw error;
    }
}

// Système de notifications
function showNotification(type, message) {
    const container = document.querySelector('.flash-container') || createFlashContainer();

    const notification = document.createElement('div');
    notification.className = `flash-message flash-${type}`;

    const icon = document.createElement('i');
    icon.className = `fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}`;

    const text = document.createElement('span');
    text.textContent = message;

    const closeBtn = document.createElement('button');
    closeBtn.className = 'flash-close';
    closeBtn.innerHTML = '<i class="fas fa-times"></i>';
    closeBtn.onclick = () => notification.remove();

    notification.appendChild(icon);
    notification.appendChild(text);
    notification.appendChild(closeBtn);

    container.appendChild(notification);

    // Auto-fermeture après 5 secondes
    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}

function createFlashContainer() {
    const container = document.createElement('div');
    container.className = 'flash-container';
    document.querySelector('.main-content').prepend(container);
    return container;
}

// Formattage des dates
function formatDate(dateString) {
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    return new Date(dateString).toLocaleDateString('fr-FR', options);
}

function formatTime(timeString) {
    return timeString.substring(0, 5); // Format HH:MM
}

// Gestion des couleurs
function initColorPickers() {
    const colorInputs = document.querySelectorAll('input[type="color"]');
    colorInputs.forEach(input => {
        // Afficher la valeur hex à côté du sélecteur
        const wrapper = input.closest('.color-picker-wrapper');
        if (wrapper) {
            const valueDisplay = document.createElement('span');
            valueDisplay.className = 'color-value';
            valueDisplay.textContent = input.value;
            wrapper.appendChild(valueDisplay);

            input.addEventListener('input', (e) => {
                valueDisplay.textContent = e.target.value;
            });
        }
    });
}

// Initialisation au chargement
document.addEventListener('DOMContentLoaded', initColorPickers);
