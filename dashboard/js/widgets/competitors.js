/**
 * MMON Widget — Competitors Intelligence
 * Mostra info raccolte sui competitor: domini, tech stack, asset esposti.
 */

MMON.registerWidget('competitors', {
    title: 'Competitors',
    gridPos: { x: 0, y: 8, w: 12, h: 4 },

    async render(container, filters) {
        const data = await MMON.apiFetch('/widgets/competitors?limit=50');
        const countEl = document.getElementById('count-competitors');

        if (!data.items || data.items.length === 0) {
            container.innerHTML = `
                <div class="widget-empty">
                    <div class="empty-icon">&#127919;</div>
                    <div>No competitor data yet</div>
                    <div style="font-size:11px; color:var(--text-muted);">Configure competitors in the wizard to start monitoring</div>
                </div>`;
            if (countEl) countEl.textContent = '0';
            return;
        }

        if (countEl) countEl.textContent = data.total_competitors;

        // Raggruppare per competitor
        const byCompetitor = {};
        data.items.forEach(item => {
            const key = item.competitor_name || item.target || 'unknown';
            if (!byCompetitor[key]) byCompetitor[key] = [];
            byCompetitor[key].push(item);
        });

        let html = '';
        for (const [name, findings] of Object.entries(byCompetitor)) {
            // Header competitor
            html += `<div style="margin-bottom: 20px;">`;
            html += `<div style="display:flex; align-items:center; gap:12px; margin-bottom:10px;">`;
            html += `<span style="font-family:var(--font-mono); font-size:14px; font-weight:700; color:var(--text-primary);">${name}</span>`;
            html += `<span style="font-family:var(--font-mono); font-size:11px; color:var(--text-muted); background:var(--bg-input); padding:2px 8px; border-radius:3px;">${findings.length} findings</span>`;

            // Severity breakdown per competitor
            const sevCounts = { critical: 0, high: 0, medium: 0, low: 0, info: 0 };
            findings.forEach(f => {
                const s = f.severity || 'info';
                if (sevCounts[s] !== undefined) sevCounts[s]++;
            });

            if (sevCounts.critical > 0) html += `<span class="sev sev-critical">${sevCounts.critical} crit</span>`;
            if (sevCounts.high > 0) html += `<span class="sev sev-high">${sevCounts.high} high</span>`;
            html += `</div>`;

            // Card grid dei finding
            html += '<div class="card-grid">';
            findings.slice(0, 12).forEach(f => {
                const type = f.finding_type || f.category || 'finding';
                const desc = MMON.truncate(f.description || f.details || '', 60);
                const sev = f.severity || 'info';
                const tool = f.source_tool || '';

                html += `
                    <div class="mini-card">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                            <span class="card-platform">${type}</span>
                            <span class="${MMON.severityClass(sev)}" style="font-size:9px;">${sev}</span>
                        </div>
                        <div style="font-size:12px; color:var(--text-secondary); margin-bottom:4px;">${desc}</div>
                        ${tool ? `<div style="font-size:10px; color:var(--text-muted); font-family:var(--font-mono);">via ${tool}</div>` : ''}
                    </div>`;
            });

            if (findings.length > 12) {
                html += `<div class="mini-card" style="display:flex; align-items:center; justify-content:center; color:var(--text-muted); font-size:12px;">+${findings.length - 12} more</div>`;
            }

            html += '</div></div>';
        }

        container.innerHTML = html;
    }
});
