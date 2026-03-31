/**
 * MMON Widget — Infrastructure Exposure
 * Mostra asset esposti: domini, IP, porte aperte, servizi.
 */

MMON.registerWidget('infrastructure', {
    title: 'Infrastructure Exposure',
    gridPos: { x: 6, y: 0, w: 6, h: 4 },

    async render(container, filters) {
        const params = new URLSearchParams();
        if (filters.severity?.length) params.set('severity', filters.severity.join(','));
        if (filters.source_vm) params.set('source_vm', filters.source_vm);

        const data = await MMON.apiFetch(`/widgets/infrastructure?${params}`);
        const countEl = document.getElementById('count-infrastructure');

        if (!data.items || data.items.length === 0) {
            container.innerHTML = `
                <div class="widget-empty">
                    <div class="empty-icon">&#127760;</div>
                    <div>No infrastructure data yet</div>
                    <div style="font-size:11px; color:var(--text-muted);">Run bbot/shodan scan to discover assets</div>
                </div>`;
            if (countEl) countEl.textContent = '0';
            return;
        }

        if (countEl) countEl.textContent = data.total_findings;

        // Tabella principale
        let html = `
            <table class="widget-table">
                <thead>
                    <tr>
                        <th>Asset</th>
                        <th>Type</th>
                        <th>Details</th>
                        <th>Sev</th>
                        <th>Source</th>
                        <th>When</th>
                    </tr>
                </thead>
                <tbody>`;

        data.items.forEach(item => {
            const sev = item.severity || 'info';
            const sevBadge = `<span class="${MMON.severityClass(sev)}">${sev}</span>`;
            const asset = item.asset || item.target || '—';
            const type = item.finding_type || item.category || '—';
            const details = MMON.truncate(item.details || item.description || '', 50);
            const source = item.source_tool || '—';
            const when = item.created_at ? MMON.timeAgo(item.created_at) : '—';

            html += `
                <tr>
                    <td class="mono">${asset}</td>
                    <td>${type}</td>
                    <td title="${item.details || ''}">${details}</td>
                    <td>${sevBadge}</td>
                    <td style="color:var(--text-muted); font-size:11px;">${source}</td>
                    <td style="color:var(--text-muted); font-size:11px;">${when}</td>
                </tr>`;
        });

        html += '</tbody></table>';

        // Summary bar
        if (data.severity_counts) {
            const sc = data.severity_counts;
            html += `
                <div style="display:flex; gap:12px; padding:12px 0 0; border-top:1px solid var(--border); margin-top:12px; font-family:var(--font-mono); font-size:11px;">
                    <span style="color:var(--critical);">CRIT: ${sc.critical || 0}</span>
                    <span style="color:var(--error);">HIGH: ${sc.high || 0}</span>
                    <span style="color:var(--warning);">MED: ${sc.medium || 0}</span>
                    <span style="color:var(--accent);">LOW: ${sc.low || 0}</span>
                    <span style="color:var(--text-muted);">INFO: ${sc.info || 0}</span>
                </div>`;
        }

        container.innerHTML = html;
    }
});
