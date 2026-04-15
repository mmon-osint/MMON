/**
 * MMON Widget — Competitors Intelligence
 */
MMON.registerWidget('competitors', {
    title: 'Competitors',
    gridPos: { x: 0, y: 8, w: 12, h: 4 },

    async render(container, filters) {
        const data = await MMON.apiFetch('/widgets/competitors?limit=50');
        if (!data.items || data.items.length === 0) {
            container.innerHTML = '<div class="widget-empty"><div class="empty-icon">🎯</div><div>No competitor data yet</div></div>';
            return;
        }

        const byComp = {};
        data.items.forEach(item => {
            const key = item.competitor_name || item.target || 'unknown';
            if (!byComp[key]) byComp[key] = [];
            byComp[key].push(item);
        });

        let html = '';
        for (const [name, findings] of Object.entries(byComp)) {
            html += `<div style="margin-bottom:16px"><div style="display:flex;align-items:center;gap:10px;margin-bottom:8px"><span style="font-family:var(--font-mono);font-size:14px;font-weight:700">${name}</span><span style="font-size:11px;color:var(--text-muted);background:var(--bg-input);padding:2px 8px;border-radius:3px">${findings.length} findings</span></div><div class="card-grid">`;
            findings.slice(0, 8).forEach(f => {
                html += `<div class="mini-card"><div style="display:flex;justify-content:space-between;margin-bottom:4px"><span class="card-platform">${f.finding_type || f.category || ''}</span><span class="${MMON.severityClass(f.severity)}" style="font-size:9px">${f.severity}</span></div><div style="font-size:12px;color:var(--text-secondary)">${MMON.truncate(f.description || '', 50)}</div></div>`;
            });
            html += '</div></div>';
        }
        container.innerHTML = html;
    }
});
