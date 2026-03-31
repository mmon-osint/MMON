/**
 * MMON — Widget Engine
 * Core del sistema dashboard: auth, fetch, grid, widget lifecycle.
 */

const MMON = (() => {
    'use strict';

    // =========================================================
    // STATE
    // =========================================================

    const state = {
        token: localStorage.getItem('mmon_token') || null,
        grid: null,
        widgets: {},       // registry: { id: { render, refresh } }
        filters: {
            severity: ['critical', 'high', 'medium', 'low', 'info'],
            source_vm: '',
            date_from: '',
            date_to: '',
        },
    };

    const API_BASE = '/api/v1';

    // =========================================================
    // AUTH
    // =========================================================

    function isAuthenticated() {
        return !!state.token;
    }

    function setToken(token) {
        state.token = token;
        localStorage.setItem('mmon_token', token);
    }

    function clearToken() {
        state.token = null;
        localStorage.removeItem('mmon_token');
    }

    async function login(username, password) {
        const res = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password }),
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || 'Login fallito');
        }

        const data = await res.json();
        setToken(data.access_token);
        return data;
    }

    function logout() {
        clearToken();
        location.reload();
    }

    // =========================================================
    // API FETCH
    // =========================================================

    async function apiFetch(endpoint, options = {}) {
        const headers = {
            'Content-Type': 'application/json',
            ...(state.token ? { 'Authorization': `Bearer ${state.token}` } : {}),
            ...(options.headers || {}),
        };

        const res = await fetch(`${API_BASE}${endpoint}`, {
            ...options,
            headers,
        });

        if (res.status === 401) {
            clearToken();
            showLogin();
            throw new Error('Sessione scaduta');
        }

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `HTTP ${res.status}`);
        }

        return res.json();
    }

    // =========================================================
    // GRID (GridStack)
    // =========================================================

    function initGrid() {
        state.grid = GridStack.init({
            column: 12,
            cellHeight: 80,
            margin: 8,
            animate: true,
            float: true,
            removable: false,
            resizable: { handles: 'se, sw' },
            draggable: { handle: '.widget-header' },
        }, '#widget-grid');

        // Salva layout quando cambia
        state.grid.on('change', saveLayout);
    }

    function saveLayout() {
        if (!state.grid) return;
        const items = state.grid.save(false);
        localStorage.setItem('mmon_layout', JSON.stringify(items));
    }

    function loadLayout() {
        const saved = localStorage.getItem('mmon_layout');
        if (!saved) return null;
        try {
            return JSON.parse(saved);
        } catch {
            return null;
        }
    }

    function resetLayout() {
        localStorage.removeItem('mmon_layout');
        location.reload();
    }

    // =========================================================
    // WIDGET MANAGEMENT
    // =========================================================

    /**
     * Registra un widget nel sistema.
     * @param {string} id - ID univoco del widget
     * @param {object} config - { title, gridPos: {x,y,w,h}, render(container), refresh() }
     */
    function registerWidget(id, config) {
        state.widgets[id] = config;
    }

    function createWidgetHTML(id, title) {
        return `
            <div class="grid-stack-item-content" id="widget-${id}">
                <div class="widget-header">
                    <span class="widget-title">${title}</span>
                    <div class="widget-actions">
                        <span class="widget-count" id="count-${id}">—</span>
                        <button class="widget-btn" onclick="MMON.refreshWidget('${id}')" title="Refresh">&#8635;</button>
                    </div>
                </div>
                <div class="widget-body" id="body-${id}">
                    <div class="widget-loading">
                        <div class="spinner"></div>
                        Loading...
                    </div>
                </div>
            </div>
        `;
    }

    function mountWidgets() {
        const savedLayout = loadLayout();

        for (const [id, config] of Object.entries(state.widgets)) {
            const html = createWidgetHTML(id, config.title);
            let gridPos = config.gridPos;

            // Usare posizione salvata se disponibile
            if (savedLayout) {
                const saved = savedLayout.find(s => s.id === id);
                if (saved) {
                    gridPos = { x: saved.x, y: saved.y, w: saved.w, h: saved.h };
                }
            }

            state.grid.addWidget({
                id: id,
                x: gridPos.x,
                y: gridPos.y,
                w: gridPos.w,
                h: gridPos.h,
                content: html,
            });
        }
    }

    async function refreshWidget(id) {
        const config = state.widgets[id];
        if (!config) return;

        const body = document.getElementById(`body-${id}`);
        if (!body) return;

        body.innerHTML = '<div class="widget-loading"><div class="spinner"></div>Loading...</div>';

        try {
            await config.render(body, state.filters);
        } catch (err) {
            body.innerHTML = `<div class="widget-empty"><div class="empty-icon">&#9888;</div><div>${err.message}</div></div>`;
        }
    }

    async function refreshAllWidgets() {
        const promises = Object.keys(state.widgets).map(id => refreshWidget(id));
        await Promise.allSettled(promises);
    }

    // =========================================================
    // FILTERS
    // =========================================================

    function initFilters() {
        // Severity toggle
        document.getElementById('severity-filters')?.addEventListener('click', (e) => {
            const badge = e.target.closest('.severity-badge');
            if (!badge) return;

            badge.classList.toggle('active');
            state.filters.severity = Array.from(
                document.querySelectorAll('.severity-badge.active')
            ).map(b => b.dataset.severity);

            refreshAllWidgets();
        });

        // VM filter
        document.getElementById('filter-vm')?.addEventListener('change', (e) => {
            state.filters.source_vm = e.target.value;
            refreshAllWidgets();
        });

        // Date filters
        document.getElementById('filter-date-from')?.addEventListener('change', (e) => {
            state.filters.date_from = e.target.value;
            refreshAllWidgets();
        });

        document.getElementById('filter-date-to')?.addEventListener('change', (e) => {
            state.filters.date_to = e.target.value;
            refreshAllWidgets();
        });
    }

    // =========================================================
    // API STATUS + QUICK STATS
    // =========================================================

    async function checkApiStatus() {
        const dot = document.getElementById('api-status');
        const text = document.getElementById('api-status-text');

        try {
            const data = await fetch('/health').then(r => r.json());
            dot.className = 'status-dot';
            text.textContent = `Online — ${data.mode}`;
        } catch {
            dot.className = 'status-dot offline';
            text.textContent = 'Offline';
        }
    }

    async function updateQuickStats() {
        try {
            const data = await apiFetch('/findings?page_size=1');
            document.getElementById('stat-total').textContent = data.total || 0;

            const crit = await apiFetch('/findings?severity=critical&page_size=1');
            const high = await apiFetch('/findings?severity=high&page_size=1');
            document.getElementById('stat-critical').textContent =
                (crit.total || 0) + (high.total || 0);
        } catch {
            // silently fail
        }
    }

    // =========================================================
    // LOGIN UI
    // =========================================================

    function showLogin() {
        document.getElementById('login-overlay').style.display = 'flex';
    }

    function hideLogin() {
        document.getElementById('login-overlay').style.display = 'none';
    }

    function initLoginForm() {
        document.getElementById('login-form')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const errEl = document.getElementById('login-error');
            errEl.style.display = 'none';

            const user = document.getElementById('login-user').value;
            const pass = document.getElementById('login-pass').value;

            try {
                await login(user, pass);
                hideLogin();
                startDashboard();
            } catch (err) {
                errEl.textContent = err.message;
                errEl.style.display = 'block';
            }
        });
    }

    // =========================================================
    // UTILITY
    // =========================================================

    function severityClass(severity) {
        return `sev sev-${severity}`;
    }

    function timeAgo(dateStr) {
        const now = new Date();
        const date = new Date(dateStr);
        const diff = Math.floor((now - date) / 1000);

        if (diff < 60) return `${diff}s ago`;
        if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
        return `${Math.floor(diff / 86400)}d ago`;
    }

    function truncate(str, max = 40) {
        if (!str) return '';
        return str.length > max ? str.substring(0, max) + '...' : str;
    }

    // =========================================================
    // INIT
    // =========================================================

    async function startDashboard() {
        initGrid();
        mountWidgets();
        initFilters();
        await checkApiStatus();
        await refreshAllWidgets();
        await updateQuickStats();

        // Auto-refresh ogni 5 minuti
        setInterval(() => {
            refreshAllWidgets();
            updateQuickStats();
            checkApiStatus();
        }, 300000);
    }

    function init() {
        initLoginForm();

        // Button handlers
        document.getElementById('btn-refresh')?.addEventListener('click', refreshAllWidgets);
        document.getElementById('btn-reset-layout')?.addEventListener('click', resetLayout);
        document.getElementById('btn-logout')?.addEventListener('click', logout);

        if (isAuthenticated()) {
            hideLogin();
            startDashboard();
        } else {
            showLogin();
        }
    }

    // =========================================================
    // PUBLIC API
    // =========================================================

    return {
        init,
        registerWidget,
        refreshWidget,
        refreshAllWidgets,
        apiFetch,
        severityClass,
        timeAgo,
        truncate,
        state,
    };

})();
