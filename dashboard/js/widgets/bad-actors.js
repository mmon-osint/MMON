/**
 * MMON Widget — Top Active Bad Actors (VM2)
 */
MMON.registerWidget('bad-actors', {
    title: 'Top Active Bad Actors',
    gridPos: { x: 4, y: 12, w: 4, h: 3 },

    async render(container) {
        const data = await MMON.apiFetch('/widgets/bad-actors?limit=10');

        if (!data.items || data.items.length === 0) {
            container.innerHTML = '<div class="widget-empty"><div class="empty-icon">👹</div><div>No threat actors detected</div><div style="font-size:11px;color:var(--text-muted)">Data from VM2 deep web crawling</div></div>';
            return;
        }

        let html = '<table class="widget-table"><thead><tr><th>Actor</th><th>Aliases</th><th>Threat</th><th>Last Seen</th></tr></thead><tbody>';
        data.items.forEach(item => {
            const aliases = (item.aliases || []).slice(0, 3).join(', ') || '—';
            const level = item.threat_level || 'medium';
            html += `<tr><td style="font-weight:600">${item.actor_name}</td><td style="font-size:11px;color:var(--text-muted)">${aliases}</td><td><span class="${MMON.severityClass(level)}">${level}</span></td><td style="font-size:11px;color:var(--text-muted)">${item.last_seen ? MMON.timeAgo(item.last_seen) : '—'}</td></tr>`;
        });
        html += '</tbody></table>';
        container.innerHTML = html;
    }
});
