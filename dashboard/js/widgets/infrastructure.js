/**
 * MMON Widget — Infrastructure Exposure
 */
MMON.registerWidget('infrastructure', {
    title: 'Infrastructure Exposure',
    gridPos: { x: 6, y: 0, w: 6, h: 4 },

    async render(container, filters) {
        const params = new URLSearchParams();
        if (filters.severity?.length) params.set('severity', filters.severity.join(','));
        if (filters.source_vm) params.set('source_vm', filters.source_vm);

        const data = await MMON.apiFetch(`/widgets/infrastructure?${params}`);
        if (!data.items || data.items.length === 0) {
            container.innerHTML = '<div class="widget-empty"><div class="empty-icon">🌐</div><div>No infrastructure data yet</div></div>';
            return;
        }

        let html = '<table class="widget-table"><thead><tr><th>Asset</th><th>Type</th><th>Details</th><th>Sev</th><th>Source</th></tr></thead><tbody>';
        data.items.forEach(item => {
            html += `<tr><td class="mono">${item.asset || '—'}</td><td>${item.finding_type || '—'}</td><td>${MMON.truncate(item.details || '', 40)}</td><td><span class="${MMON.severityClass(item.severity)}">${item.severity}</span></td><td style="color:var(--text-muted);font-size:11px">${item.source_tool || ''}</td></tr>`;
        });
        html += '</tbody></table>';

        if (data.severity_counts) {
            const sc = data.severity_counts;
            html += `<div style="display:flex;gap:12px;padding:10px 0 0;border-top:1px solid var(--border);margin-top:10px;font-family:var(--font-mono);font-size:11px"><span style="color:var(--critical)">CRIT:${sc.critical||0}</span><span style="color:var(--error)">HIGH:${sc.high||0}</span><span style="color:var(--warning)">MED:${sc.medium||0}</span></div>`;
        }
        container.innerHTML = html;
    }
});
