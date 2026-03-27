/**
 * ראש נקי - Dashboard JavaScript
 * Rosh Naki - Cannabis Sobriety App by Niv Ifergan
 */

let userId = null;
let userStats = null;
let selectedMoods = { morning: null, evening: null, journal: null };
let selectedTrigger = null;
let breathingInterval = null;

// ---- Init ----
document.addEventListener('DOMContentLoaded', () => {
    userId = localStorage.getItem('userId');
    if (!userId) {
        window.location.href = '/';
        return;
    }

    const displayName = localStorage.getItem('displayName');
    document.getElementById('greeting-text').textContent = `שלום, ${displayName || 'חבר/ה'}! 🧠`;

    loadDashboard();
});

async function loadDashboard() {
    await Promise.all([
        loadStats(),
        loadMilestones(),
        loadWithdrawalTimeline(),
        loadDailyQuote(),
        loadUrgeStats(),
        loadJournal(),
        loadCommunityFeed(),
    ]);

    // Start real-time counter
    startCounter();
}

// ---- API Helper ----
async function api(endpoint, options = {}) {
    try {
        const res = await fetch(endpoint, {
            headers: { 'Content-Type': 'application/json', ...options.headers },
            ...options,
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'שגיאה');
        return data;
    } catch (err) {
        showToast(err.message, 'error');
        throw err;
    }
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3500);
}

// ---- Tab Navigation ----
function showTab(tabName) {
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

    const panel = document.getElementById(`tab-${tabName}`);
    if (panel) panel.classList.add('active');

    const navBtn = document.querySelector(`[data-tab="${tabName}"]`);
    if (navBtn) navBtn.classList.add('active');

    // Refresh data when switching tabs
    if (tabName === 'community') loadCommunityFeed();
    if (tabName === 'journal') loadJournal();
    if (tabName === 'urge') loadUrgeStats();
    if (tabName === 'settings') loadSettings();
}

// ---- Stats & Counter ----
async function loadStats() {
    try {
        userStats = await api(`/api/tracker/stats/${userId}`);
        updateCounterDisplay();

        // Check for newly achieved milestones
        if (userStats.newly_achieved_milestones && userStats.newly_achieved_milestones.length > 0) {
            const m = userStats.newly_achieved_milestones[0];
            showMilestoneModal(m.name);
        }
    } catch (err) { /* handled */ }
}

function updateCounterDisplay() {
    if (!userStats || !userStats.sobriety_start_date) return;

    const start = new Date(userStats.sobriety_start_date);
    const now = new Date();
    const diff = now - start;

    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    const seconds = Math.floor((diff % (1000 * 60)) / 1000);

    document.getElementById('sober-days').textContent = days.toLocaleString('he-IL');
    document.getElementById('sober-hours-num').textContent = hours.toString().padStart(2, '0');
    document.getElementById('sober-minutes-num').textContent = minutes.toString().padStart(2, '0');
    document.getElementById('sober-seconds-num').textContent = seconds.toString().padStart(2, '0');

    // Money & time saved
    const moneySaved = Math.round(days * (userStats.money_saved / Math.max(userStats.sober_days, 1)));
    document.getElementById('money-saved').textContent = `₪${userStats.money_saved.toLocaleString('he-IL')}`;
    document.getElementById('hours-saved').textContent = userStats.hours_saved.toLocaleString('he-IL');

    // Start date
    const startDateStr = start.toLocaleDateString('he-IL', {
        year: 'numeric', month: 'long', day: 'numeric'
    });
    document.getElementById('counter-start-date').textContent = `נקי/ה מאז ${startDateStr}`;
}

function startCounter() {
    setInterval(() => {
        if (userStats && userStats.sobriety_start_date) {
            updateCounterDisplay();
        }
    }, 1000);
}

// ---- Milestones ----
async function loadMilestones() {
    try {
        const data = await api(`/api/tracker/milestones/${userId}`);
        const container = document.getElementById('milestones-container');
        container.innerHTML = '';

        data.milestones.forEach(m => {
            const isAchieved = m.achieved;
            const isCurrent = !isAchieved && m.progress > 0 && m.progress < 100;
            const nextMilestone = !isAchieved && m.progress === 0;

            let className = 'milestone-item';
            if (isAchieved) className += ' achieved';
            if (isCurrent) className += ' current';

            const icon = isAchieved ? '✅' : (isCurrent ? '🔥' : '⭕');

            container.innerHTML += `
                <div class="${className}">
                    <span class="milestone-icon">${icon}</span>
                    <div class="milestone-info">
                        <div class="milestone-name">${m.name}</div>
                        <div class="milestone-days">${m.days_required} ימים ${isAchieved ? '- הושג! 🎉' : ''}</div>
                        ${!isAchieved ? `
                        <div class="milestone-progress">
                            <div class="milestone-progress-fill" style="width: ${m.progress}%"></div>
                        </div>` : ''}
                    </div>
                </div>
            `;
        });
    } catch (err) { /* handled */ }
}

function showMilestoneModal(name) {
    document.getElementById('milestone-title').textContent = name;
    document.getElementById('milestone-message').textContent = 'כל הכבוד! המשך כך! 💜';
    document.getElementById('milestone-modal').style.display = 'flex';
}

function closeMilestoneModal() {
    document.getElementById('milestone-modal').style.display = 'none';
}

// ---- Withdrawal Timeline ----
async function loadWithdrawalTimeline() {
    try {
        const data = await api('/api/tracker/withdrawal-timeline');
        const container = document.getElementById('withdrawal-timeline');
        container.innerHTML = '';

        const currentDays = userStats ? userStats.sober_days : 0;

        data.timeline.forEach(item => {
            const isActive = currentDays >= 0; // Determine if this is the current phase
            let activeClass = '';

            // Simple check for which phase user is in
            const rangeText = item.day_range;

            container.innerHTML += `
                <div class="timeline-item ${activeClass}">
                    <div class="timeline-range">${item.day_range}</div>
                    <div class="timeline-title">${item.title}</div>
                    <div class="timeline-desc">${item.description}</div>
                    <div class="timeline-symptoms">
                        ${item.symptoms.map(s => `<span class="symptom-tag">${s}</span>`).join('')}
                    </div>
                    <div class="timeline-tips">
                        ${item.tips.map(t => `<span>💡 ${t}</span>`).join('')}
                    </div>
                </div>
            `;
        });
    } catch (err) { /* handled */ }
}

// ---- Daily Quote ----
async function loadDailyQuote() {
    try {
        const data = await api('/api/community/quote');
        document.getElementById('daily-quote-text').textContent = `"${data.text}"`;
        document.getElementById('daily-quote-author').textContent = `— ${data.author}`;
    } catch (err) { /* handled */ }
}

// ---- Mood Selector ----
function selectMood(btn, type) {
    const parent = btn.closest('.mood-options');
    parent.querySelectorAll('.mood-btn').forEach(b => b.classList.remove('selected'));
    btn.classList.add('selected');
    selectedMoods[type] = parseInt(btn.dataset.mood);
}

// ---- Morning Pledge ----
async function submitMorningPledge() {
    try {
        const data = await api(`/api/pledges/morning/${userId}`, {
            method: 'POST',
            body: JSON.stringify({
                morning_note: document.getElementById('pledge-note').value,
                mood: selectedMoods.morning,
            }),
        });
        showToast(data.message, 'success');

        if (!data.already_pledged) {
            document.getElementById('pledge-content').style.display = 'none';
            document.getElementById('pledge-done').style.display = 'block';
        }
    } catch (err) { /* handled */ }
}

// ---- Evening Review ----
function showEveningReview() {
    document.getElementById('evening-modal').style.display = 'flex';
}

async function submitEveningReview(stayedSober) {
    try {
        const data = await api(`/api/pledges/evening/${userId}`, {
            method: 'POST',
            body: JSON.stringify({
                evening_note: document.getElementById('evening-note').value,
                mood: selectedMoods.evening,
                difficulty_level: parseInt(document.getElementById('evening-difficulty').value),
                stayed_sober: stayedSober,
            }),
        });
        showToast(data.message, stayedSober ? 'success' : 'info');
        document.getElementById('evening-modal').style.display = 'none';

        if (!stayedSober) {
            // Offer to reset counter
            if (confirm('רוצה לאפס את המונה? זה בסדר, כל יום הוא התחלה חדשה.')) {
                await resetSobriety();
            }
        }
    } catch (err) { /* handled */ }
}

// ---- Urge Tools ----
function updateIntensityLabel(val) {
    document.getElementById('intensity-label').textContent = val;
}

function selectTrigger(btn) {
    document.querySelectorAll('.trigger-btn').forEach(b => b.classList.remove('selected'));
    btn.classList.add('selected');
    selectedTrigger = btn.dataset.trigger;
}

async function logUrge(resisted) {
    try {
        const data = await api(`/api/pledges/urge/${userId}`, {
            method: 'POST',
            body: JSON.stringify({
                intensity: parseInt(document.getElementById('urge-intensity').value),
                trigger_category: selectedTrigger,
                coping_method: document.getElementById('urge-coping').value,
                resisted: resisted,
            }),
        });
        showToast(data.message, resisted ? 'success' : 'info');

        // Reset form
        document.getElementById('urge-intensity').value = 5;
        document.getElementById('intensity-label').textContent = '5';
        document.getElementById('urge-coping').value = '';
        document.querySelectorAll('.trigger-btn').forEach(b => b.classList.remove('selected'));
        selectedTrigger = null;

        loadUrgeStats();
    } catch (err) { /* handled */ }
}

async function loadUrgeStats() {
    try {
        const data = await api(`/api/pledges/urge-stats/${userId}`);
        document.getElementById('urge-total').textContent = data.total_urges;
        document.getElementById('urge-resisted').textContent = data.resisted;
        document.getElementById('urge-rate').textContent = `${data.resistance_rate}%`;
        document.getElementById('urge-avg').textContent = data.avg_intensity;
    } catch (err) { /* handled */ }
}

// ---- Breathing Exercise ----
function startBreathing() {
    if (breathingInterval) {
        clearInterval(breathingInterval);
        breathingInterval = null;
        document.getElementById('breath-text').textContent = 'לחץ להתחלה';
        document.getElementById('breath-circle').className = 'breath-circle';
        return;
    }

    const circle = document.getElementById('breath-circle');
    const text = document.getElementById('breath-text');
    let phase = 0; // 0=inhale, 1=hold, 2=exhale
    const phases = [
        { text: 'שאפ... 🌬️', class: 'inhale', duration: 4000 },
        { text: 'החזק... ⏸️', class: 'inhale', duration: 4000 },
        { text: 'נשוף... 💨', class: 'exhale', duration: 4000 },
    ];

    let cycleCount = 0;
    const maxCycles = 4;

    function nextPhase() {
        const p = phases[phase];
        text.textContent = p.text;
        circle.className = `breath-circle ${p.class}`;

        phase = (phase + 1) % 3;
        if (phase === 0) cycleCount++;

        if (cycleCount >= maxCycles) {
            clearInterval(breathingInterval);
            breathingInterval = null;
            text.textContent = 'מעולה! 🙏';
            circle.className = 'breath-circle';
            setTimeout(() => {
                text.textContent = 'לחץ להתחלה';
            }, 3000);
        }
    }

    nextPhase();
    breathingInterval = setInterval(nextPhase, 4000);
}

// ---- Journal ----
function toggleNewEntry() {
    const form = document.getElementById('new-entry-form');
    form.style.display = form.style.display === 'none' ? 'flex' : 'none';
}

async function saveJournalEntry() {
    const content = document.getElementById('journal-content').value.trim();
    if (!content) {
        showToast('אנא כתוב משהו ביומן', 'error');
        return;
    }

    try {
        const data = await api(`/api/pledges/journal/${userId}`, {
            method: 'POST',
            body: JSON.stringify({
                title: document.getElementById('journal-title').value.trim(),
                content: content,
                mood: selectedMoods.journal,
            }),
        });
        showToast(data.message, 'success');

        // Reset form
        document.getElementById('journal-title').value = '';
        document.getElementById('journal-content').value = '';
        selectedMoods.journal = null;
        document.querySelectorAll('#new-entry-form .mood-btn').forEach(b => b.classList.remove('selected'));
        toggleNewEntry();

        loadJournal();
    } catch (err) { /* handled */ }
}

async function loadJournal() {
    try {
        const data = await api(`/api/pledges/journal/${userId}`);
        const container = document.getElementById('journal-entries');
        container.innerHTML = '';

        if (data.entries.length === 0) {
            container.innerHTML = '<p style="text-align:center;color:var(--text-light);padding:40px 0;">עדיין אין רשומות. התחל לכתוב את הסיפור שלך 📝</p>';
            return;
        }

        const moods = ['', '😢', '😕', '😐', '🙂', '😄'];

        data.entries.forEach(e => {
            const date = new Date(e.created_at).toLocaleDateString('he-IL', {
                year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
            });
            container.innerHTML += `
                <div class="journal-card">
                    <div class="journal-card-header">
                        <span class="journal-card-title">${e.title || 'רשומה'}</span>
                        <span class="journal-card-date">${date}</span>
                    </div>
                    <div class="journal-card-content">${e.content}</div>
                    ${e.mood ? `<div class="journal-card-mood">${moods[e.mood]}</div>` : ''}
                </div>
            `;
        });
    } catch (err) { /* handled */ }
}

// ---- Community ----
function toggleNewPost() {
    const form = document.getElementById('new-post-form');
    form.style.display = form.style.display === 'none' ? 'flex' : 'none';
}

async function submitPost() {
    const content = document.getElementById('post-content').value.trim();
    if (!content) {
        showToast('אנא כתוב משהו', 'error');
        return;
    }

    try {
        const data = await api(`/api/community/post/${userId}`, {
            method: 'POST',
            body: JSON.stringify({
                content: content,
                post_type: document.getElementById('post-type').value,
                is_anonymous: document.getElementById('post-anonymous').checked,
            }),
        });
        showToast(data.message, 'success');
        document.getElementById('post-content').value = '';
        toggleNewPost();
        loadCommunityFeed();
    } catch (err) { /* handled */ }
}

async function loadCommunityFeed() {
    try {
        const data = await api('/api/community/feed');
        const container = document.getElementById('community-feed');
        container.innerHTML = '';

        if (data.posts.length === 0) {
            container.innerHTML = '<p style="text-align:center;color:var(--text-light);padding:40px 0;">הקהילה מחכה לך! היה/י הראשון/ה לשתף 💜</p>';
            return;
        }

        const typeLabels = {
            share: '💬 שיתוף',
            question: '❓ שאלה',
            milestone: '🏆 אבן דרך',
            support: '🤗 תמיכה',
        };

        data.posts.forEach(post => {
            const date = new Date(post.created_at).toLocaleDateString('he-IL', {
                month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
            });

            const initials = post.display_name.charAt(0);

            let commentsHtml = '';
            if (post.comments && post.comments.length > 0) {
                commentsHtml = `
                    <div class="post-comments">
                        ${post.comments.map(c => `
                            <div class="comment-item">
                                <span class="comment-author">${c.display_name}:</span>
                                ${c.content}
                            </div>
                        `).join('')}
                    </div>
                `;
            }

            container.innerHTML += `
                <div class="feed-post">
                    <div class="post-header">
                        <div class="post-author">
                            <div class="post-avatar">${initials}</div>
                            <div>
                                <div class="post-author-name">${post.display_name}</div>
                                <div class="post-author-days">${post.sober_days} ימים נקי/ה • ${date}</div>
                            </div>
                        </div>
                        <span class="post-type-badge">${typeLabels[post.post_type] || post.post_type}</span>
                    </div>
                    <div class="post-content">${post.content}</div>
                    <div class="post-actions">
                        <button class="post-action-btn" onclick="likePost(${post.id})">
                            ❤️ ${post.likes_count}
                        </button>
                        <button class="post-action-btn" onclick="toggleCommentForm(${post.id})">
                            💬 ${post.comments_count}
                        </button>
                        <button class="post-action-btn" onclick="sharePost('${post.content.substring(0, 50)}')">
                            📤 שיתוף
                        </button>
                    </div>
                    ${commentsHtml}
                    <div id="comment-form-${post.id}" style="display:none; margin-top:10px;">
                        <div style="display:flex;gap:8px;">
                            <input type="text" id="comment-input-${post.id}" placeholder="כתוב תגובה..." class="input-field" style="flex:1;">
                            <button class="btn btn-primary btn-sm" onclick="submitComment(${post.id})">שלח</button>
                        </div>
                    </div>
                </div>
            `;
        });
    } catch (err) { /* handled */ }
}

async function likePost(postId) {
    try {
        await api(`/api/community/like/${postId}`, { method: 'POST' });
        loadCommunityFeed();
    } catch (err) { /* handled */ }
}

function toggleCommentForm(postId) {
    const form = document.getElementById(`comment-form-${postId}`);
    form.style.display = form.style.display === 'none' ? 'block' : 'none';
}

async function submitComment(postId) {
    const input = document.getElementById(`comment-input-${postId}`);
    const content = input.value.trim();
    if (!content) return;

    try {
        await api(`/api/community/comment/${postId}/${userId}`, {
            method: 'POST',
            body: JSON.stringify({ content }),
        });
        input.value = '';
        loadCommunityFeed();
    } catch (err) { /* handled */ }
}

function sharePost(text) {
    const shareText = `💜 מתוך קהילת ראש נקי: "${text}..."`;
    if (navigator.share) {
        navigator.share({ title: 'ראש נקי', text: shareText });
    } else {
        // Fallback: copy to clipboard
        navigator.clipboard.writeText(shareText).then(() => {
            showToast('הטקסט הועתק! שתף בוואטסאפ 📱', 'success');
        });
    }
}

// ---- Settings ----
async function loadSettings() {
    try {
        const data = await api(`/api/auth/me/${userId}`);
        document.getElementById('settings-name').value = data.display_name || '';
        document.getElementById('settings-motivation').value = data.motivation || '';
        document.getElementById('settings-cost').value = data.daily_cost_saved || 50;
        document.getElementById('settings-hours').value = data.daily_hours_saved || 2;
        if (data.sobriety_start_date) {
            document.getElementById('settings-sobriety-date').value = data.sobriety_start_date.split('T')[0];
        }
    } catch (err) { /* handled */ }
}

async function saveSettings() {
    try {
        await api(`/api/auth/me/${userId}`, {
            method: 'PUT',
            body: JSON.stringify({
                username: '', // Not changing
                email: '', // Not changing
                password: '', // Not changing
                display_name: document.getElementById('settings-name').value,
                motivation: document.getElementById('settings-motivation').value,
                sobriety_date: document.getElementById('settings-sobriety-date').value,
                daily_cost: parseFloat(document.getElementById('settings-cost').value),
                daily_hours: parseFloat(document.getElementById('settings-hours').value),
            }),
        });
        showToast('ההגדרות נשמרו! 💾', 'success');
        localStorage.setItem('displayName', document.getElementById('settings-name').value);
        document.getElementById('greeting-text').textContent = `שלום, ${document.getElementById('settings-name').value}! 🧠`;
        loadStats();
    } catch (err) { /* handled */ }
}

async function confirmReset() {
    if (!confirm('בטוח/ה? המונה יאופס. אבל זכור/י - כל יום הוא התחלה חדשה! 💜')) {
        return;
    }

    await resetSobriety();
}

async function resetSobriety() {
    try {
        const data = await api(`/api/tracker/reset/${userId}`, {
            method: 'POST',
            body: JSON.stringify({}),
        });
        showToast(data.message, 'info');
        loadStats();
        loadMilestones();
    } catch (err) { /* handled */ }
}

function logout() {
    localStorage.removeItem('userId');
    localStorage.removeItem('displayName');
    window.location.href = '/';
}

// ---- Auto Evening Review (after 8 PM) ----
(function checkEveningReview() {
    const hour = new Date().getHours();
    if (hour >= 20) {
        // Could show evening review prompt - for now just add a button
        const pledgeCard = document.getElementById('pledge-card');
        if (pledgeCard && !document.getElementById('evening-btn')) {
            const btn = document.createElement('button');
            btn.id = 'evening-btn';
            btn.className = 'btn btn-outline btn-full';
            btn.style.marginTop = '12px';
            btn.style.borderColor = 'var(--primary)';
            btn.style.color = 'var(--primary)';
            btn.textContent = '🌙 סיכום יומי';
            btn.onclick = showEveningReview;
            pledgeCard.appendChild(btn);
        }
    }
})();
