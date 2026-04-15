/**
 * MMON Widget — Alerts (VM2)
 * Occorrenze del target nel deep web.
 */
MMON.registerWidget('alerts', {
    title: 'Deep Web Alerts',
    gridPos: { x: 0, y: 15, w: 6, h: 3 },

    async render(container, filters) {
        const params = new URLSearchParams();
        if (filters.severity?.length) params.set('severity', filters.severity.join(','));
        const data = await MMON.apiFetch(`/widgets/alerts?${params}`);

        if (!data.items || data.items.length === 0) {
            container.innerHTML = '<div class="widget-empty"><div class="empty-icon">🔔</div><div>No deep web alerts</div><div style="font-size:11px;color:var(--text-muted)">Target mentions from dark web monitoring</div></div>';
            return;
        }

        let html = '<table class="widget-table"><thead><tr><th>Type</th><th>Matched</th><th>Context</th><th>Sev</th><th>When</th></tr></thead><tbody>';
        data.items.forEach(item => {
            html += `<tr>
                <td style="font-size:11px;text-transform:uppercase;color:var(--accent-secondary)">${item.alert_type}</td>
                <td><span style="font-family:var(--font-mono);font-size:12px;background:rgba(255,23,68,0.1);padding:2px 6px;border-radius:3px;color:var(--critical)">${MMON.truncate(item.matched_text || '', 25)}</span></td>
                <td style="font-size:12px;color:var(--text-secondary)">${MMON.truncate(item.context || '', 40)}</td>
                <td><span class="${MMON.severityClass(item.severity)}">${item.severity}</span></td>
                <td style="font-size:11px;color:var(--text-muted)">${item.found_at ? MMON.timeAgo(item.found_at) : '—'}</td>
            </tr>`;
        });
        html += '</tbody></table>';
        container.innerHTML = html;
    }
});
