/**
 * MMON — Widget Engine Core
 * Gestisce auth, GridStack, widget lifecycle, filtri, auto-refresh.
 */

const MMON = (function () {
    'use strict';

    // ── State ──
    let _token = localStorage.getItem('mmon_token') || null;
    let _grid = null;
    const _widgets = {};
    const _filters = { severity: ['critical', 'high', 'medium', 'low', 'info'], source_vm: null, date_from: null, date_to: null };
    let _refreshTimer = null;

    // ── Auth ──
    function setToken(t) { _token = t; localStorage.setItem('mmon_token', t); }
    function clearToken() { _token = null; localStorage.removeItem('mmon_token'); }

    async function login() {
        const user = document.getElementById('login-user').value;
        const pass = document.getElementById('login-pass').value;
        const errEl = document.getElementById('login-error');
        errEl.textContent = '';

        try {
            const resp = await fetch('/api/v1/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: user, password: pass }),
            });
            if (!resp.ok) {
                const data = await resp.json();
                errEl.textContent = data.detail || 'Login failed';
                return;
            }
            const data = await resp.json();
            setToken(data.access_token);
            showApp();
        } catch (e) {
            errEl.textContent = 'Connection error';
        }
    }

    function logout() { clearToken(); location.reload(); }

    // ── API Fetch ──
    async function apiFetch(path, opts = {}) {
        const url = path.startsWith('/') ? `/api/v1${path}` : `/api/v1/${path}`;
        const headers = { 'Content-Type': 'application/json', ...(opts.headers || {}) };
        if (_token) headers['Authorization'] = `Bearer ${_token}`;

        const resp = await fetch(url, { ...opts, headers });
        if (resp.status === 401) { clearToken(); location.reload(); return null; }
        if (!resp.ok) throw new Error(`API ${resp.status}: ${resp.statusText}`);
        return resp.json();
    }

    // ── GridStack Init ──
    function initGrid() {
        _grid = GridStack.init({
            column: 12,
            cellHeight: 80,
            margin: 8,
            animate: true,
            float: false,
            draggable: { handle: '.widget-header' },
            resizable: { handles: 'se' },
        }, '#grid');

        _grid.on('change', saveLayout);
    }

    // ── Widget Registration ──
    function registerWidget(id, config) {
        _widgets[id] = config;
    }

    function createWidgetHTML(id, config) {
        return `
            <div class="grid-stack-item" gs-id="${id}" gs-x="${config.gridPos.x}" gs-y="${config.gridPos.y}" gs-w="${config.gridPos.w}" gs-h="${config.gridPos.h}">
                <div class="grid-stack-item-content">
                    <div class="widget-header">
                        <span class="widget-title">${config.title}</span>
                        <div class="widget-actions">
                            <button class="widget-btn" onclick="MMON.refreshWidget('${id}')" title="Refresh">↻</button>
                        </div>
                    </div>
                    <div class="widget-body" id="widget-body-${id}">
                        <div class="spinner"></div>
                    </div>
                </div>
            </div>`;
    }

    function mountWidgets() {
        const html = Object.entries(_widgets).map(([id, cfg]) => createWidgetHTML(id, cfg)).join('');
        document.getElementById('grid').innerHTML = html;
        initGrid();

        // Load saved layout
        const saved = localStorage.getItem('mmon_layout');
        if (saved) {
            try { _grid.load(JSON.parse(saved)); } catch (e) { /* ignore */ }
        }

        // Render tutti
        Object.keys(_widgets).forEach(id => refreshWidget(id));
    }

    async function refreshWidget(id) {
        const config = _widgets[id];
        if (!config || !config.render) return;

        const body = document.getElementById(`widget-body-${id}`);
        if (!body) return;

        try {
            body.innerHTML = '<div class="spinner"></div>';
            await config.render(body, _filters);
        } catch (e) {
            body.innerHTML = `<div class="widget-empty"><div style="color:var(--error);">Error: ${e.message}</div></div>`;
        }
    }

    function refreshAll() { Object.keys(_widgets).forEach(id => refreshWidget(id)); updateQuickStats(); }

    // ── Layout Save/Load ──
    function saveLayout() {
        if (!_grid) return;
        const items = _grid.save(false);
        localStorage.setItem('mmon_layout', JSON.stringify(items));
    }

    function resetLayout() {
        localStorage.removeItem('mmon_layout');
        location.reload();
    }

    // ── Filters ──
    function applyFilters() {
        // Severity
        const sevFilters = document.querySelectorAll('#sev-filters .sev-filter');
        _filters.severity = [];
        sevFilters.forEach(el => {
            const cb = el.querySelector('input');
            if (cb.checked) {
                _filters.severity.push(el.dataset.sev);
                el.classList.add('active');
            } else {
                el.classList.remove('active');
            }
        });

        // VM
        _filters.source_vm = document.getElementById('vm-filter').value || null;

        // Date
        _filters.date_from = document.getElementById('date-from').value || null;
        _filters.date_to = document.getElementById('date-to').value || null;

        refreshAll();
    }

    // ── Quick Stats ──
    async function updateQuickStats() {
        try {
            const data = await apiFetch('/findings?page_size=1');
            if (data) document.getElementById('stat-findings').textContent = data.total || 0;
        } catch (e) { /* ignore */ }
    }

    // ── API Status ──
    async function checkApiStatus() {
        try {
            const resp = await fetch('/health');
            const dot = document.getElementById('api-status-dot');
            const txt = document.getElementById('api-status-text');
            if (resp.ok) {
                dot.classList.remove('offline');
                txt.textContent = 'Connected';
            } else {
                dot.classList.add('offline');
                txt.textContent = 'Degraded';
            }
        } catch (e) {
            document.getElementById('api-status-dot').classList.add('offline');
            document.getElementById('api-status-text').textContent = 'Offline';
        }
    }

    // ── Utilities ──
    function severityClass(sev) { return `sev sev-${sev}`; }

    function truncate(str, max) {
        if (!str) return '';
        return str.length > max ? str.slice(0, max) + '...' : str;
    }

    function timeAgo(dateStr) {
        const d = new Date(dateStr);
        const now = new Date();
        const diff = (now - d) / 1000;
        if (diff < 60) return 'now';
        if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
        if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
        return Math.floor(diff / 86400) + 'd ago';
    }

    // ── Show App ──
    function showApp() {
        document.getElementById('login-overlay').style.display = 'none';
        document.getElementById('app').style.display = 'grid';
        mountWidgets();
        checkApiStatus();
        updateQuickStats();

        // Auto-refresh ogni 5 minuti
        _refreshTimer = setInterval(() => { refreshAll(); checkApiStatus(); }, 300000);

        // Severity filter click handlers
        document.querySelectorAll('#sev-filters .sev-filter').forEach(el => {
            el.addEventListener('click', () => {
                const cb = el.querySelector('input');
                cb.checked = !cb.checked;
                applyFilters();
            });
        });
    }

    // ── Init ──
    if (_token) {
        showApp();
    }

    // ── Public API ──
    return {
        registerWidget, refreshWidget, refreshAll, resetLayout,
        applyFilters, login, logout,
        apiFetch, severityClass, truncate, timeAgo,
    };
})();
