/**
 * MMON Widget — Top Active Criminal Forums (VM2)
 */
MMON.registerWidget('criminal-forums', {
    title: 'Criminal Forums',
    gridPos: { x: 8, y: 12, w: 4, h: 3 },

    async render(container) {
        const data = await MMON.apiFetch('/widgets/criminal-forums?limit=10');

        if (!data.items || data.items.length === 0) {
            container.innerHTML = '<div class="widget-empty"><div class="empty-icon">🕵</div><div>No forums monitored yet</div><div style="font-size:11px;color:var(--text-muted)">VM2 deep web intelligence</div></div>';
            return;
        }

        let html = '';
        data.items.forEach(item => {
            const statusColor = item.status === 'active' ? 'var(--success)' : 'var(--text-muted)';
            html += `<div class="mini-card" style="margin-bottom:8px;display:flex;justify-content:space-between;align-items:center">
                <div>
                    <div style="font-weight:600;font-size:13px">${item.forum_name}</div>
                    <div style="font-size:11px;color:var(--text-muted)">${item.mentions_count} mentions · ${item.last_crawl ? MMON.timeAgo(item.last_crawl) : 'never'}</div>
                </div>
                <span style="color:${statusColor};font-size:11px;font-weight:600">${item.status.toUpperCase()}</span>
            </div>`;
        });
        container.innerHTML = html;
    }
});
