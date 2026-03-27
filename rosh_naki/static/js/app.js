/**
 * ראש נקי - Landing Page JavaScript
 * Rosh Naki - Cannabis Sobriety App by Niv Ifergan
 */

// ---- Screen Navigation ----
function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    const screen = document.getElementById(screenId);
    if (screen) screen.classList.add('active');
}

// ---- Toast Notifications ----
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3500);
}

// ---- API Helper ----
async function api(endpoint, options = {}) {
    try {
        const res = await fetch(endpoint, {
            headers: { 'Content-Type': 'application/json', ...options.headers },
            ...options,
        });
        const data = await res.json();
        if (!res.ok) {
            throw new Error(data.detail || 'שגיאה בשרת');
        }
        return data;
    } catch (err) {
        showToast(err.message, 'error');
        throw err;
    }
}

// ---- Registration ----
async function handleRegister(e) {
    e.preventDefault();

    const body = {
        username: document.getElementById('reg-username').value.trim(),
        email: document.getElementById('reg-email').value.trim(),
        password: document.getElementById('reg-password').value,
        display_name: document.getElementById('reg-name').value.trim(),
        motivation: document.getElementById('reg-motivation').value.trim(),
        sobriety_date: document.getElementById('reg-sobriety-date').value,
        daily_cost: parseFloat(document.getElementById('reg-cost').value) || 50,
        daily_hours: parseFloat(document.getElementById('reg-hours').value) || 2,
    };

    if (!body.username || !body.email || !body.password) {
        showToast('אנא מלא את כל השדות', 'error');
        return;
    }

    try {
        const data = await api('/api/auth/register', {
            method: 'POST',
            body: JSON.stringify(body),
        });

        localStorage.setItem('userId', data.user_id);
        localStorage.setItem('displayName', body.display_name || body.username);
        showToast(data.message, 'success');

        setTimeout(() => {
            window.location.href = '/app';
        }, 1000);
    } catch (err) {
        // Error already shown by api()
    }
}

// ---- Login ----
async function handleLogin(e) {
    e.preventDefault();

    const body = {
        username: document.getElementById('login-username').value.trim(),
        password: document.getElementById('login-password').value,
    };

    if (!body.username || !body.password) {
        showToast('אנא מלא שם משתמש וסיסמה', 'error');
        return;
    }

    try {
        const data = await api('/api/auth/login', {
            method: 'POST',
            body: JSON.stringify(body),
        });

        localStorage.setItem('userId', data.user_id);
        localStorage.setItem('displayName', data.display_name);
        showToast('!ברוכים השבים', 'success');

        setTimeout(() => {
            window.location.href = '/app';
        }, 1000);
    } catch (err) {
        // Error already shown
    }
}

// ---- Init ----
document.addEventListener('DOMContentLoaded', () => {
    // Check if already logged in
    const userId = localStorage.getItem('userId');
    if (userId) {
        window.location.href = '/app';
        return;
    }

    // Set default sobriety date to today
    const dateInput = document.getElementById('reg-sobriety-date');
    if (dateInput) {
        dateInput.value = new Date().toISOString().split('T')[0];
    }
});
