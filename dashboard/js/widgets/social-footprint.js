/**
 * MMON Widget — Social Footprint
 * Presenza social per username/nome, raggruppamento per piattaforma.
 */
MMON.registerWidget('social-footprint', {
    title: 'Social Footprint',
    gridPos: { x: 0, y: 0, w: 6, h: 4 },

    async render(container, filters) {
        const params = new URLSearchParams();
        if (filters.severity?.length) params.set('severity', filters.severity.join(','));

        const data = await MMON.apiFetch(`/widgets/social-footprint?${params}`);

        if (!data.items || data.items.length === 0) {
            container.innerHTML = '<div class="widget-empty"><div class="empty-icon">👤</div><div>No social data yet</div></div>';
            return;
        }

        // Raggruppa per username
        const byUser = {};
        data.items.forEach(item => {
            const u = item.username || 'unknown';
            if (!byUser[u]) byUser[u] = [];
            byUser[u].push(item);
        });

        let html = '<div class="card-grid">';
        for (const [user, accounts] of Object.entries(byUser)) {
            for (const acc of accounts) {
                const link = acc.profile_url ? `<a href="${acc.profile_url}" target="_blank" rel="noopener" style="color:var(--accent); text-decoration:none; font-size:11px;">View →</a>` : '';
                html += `<div class="mini-card"><div class="card-platform">${acc.platform}</div><div style="font-size:13px; margin:4px 0;">${user}</div>${link}</div>`;
            }
        }
        html += '</div>';
        container.innerHTML = html;
    }
});
