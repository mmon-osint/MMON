/**
 * MMON Widget — Social Footprint
 * Mostra presenza social per username/nome: card per piattaforma.
 */

MMON.registerWidget('social-footprint', {
    title: 'Social Footprint',
    gridPos: { x: 0, y: 0, w: 6, h: 4 },

    async render(container, filters) {
        const data = await MMON.apiFetch('/widgets/social-footprint?limit=100');
        const countEl = document.getElementById('count-social-footprint');

        if (!data.items || data.items.length === 0) {
            container.innerHTML = `
                <div class="widget-empty">
                    <div class="empty-icon">&#128100;</div>
                    <div>No social profiles found yet</div>
                    <div style="font-size:11px; color:var(--text-muted);">Run maigret/mosint scan to discover profiles</div>
                </div>`;
            if (countEl) countEl.textContent = '0';
            return;
        }

        if (countEl) countEl.textContent = data.total_profiles;

        // Raggruppare per username
        const byUser = {};
        data.items.forEach(item => {
            const key = item.username || 'unknown';
            if (!byUser[key]) byUser[key] = [];
            byUser[key].push(item);
        });

        let html = '';
        for (const [username, profiles] of Object.entries(byUser)) {
            html += `<div style="margin-bottom: 16px;">`;
            html += `<div style="font-family:var(--font-mono); font-size:13px; font-weight:600; color:var(--text-primary); margin-bottom:8px;">
                        @${username} <span style="color:var(--text-muted); font-weight:400;">(${profiles.length} platforms)</span>
                     </div>`;
            html += '<div class="card-grid">';

            profiles.forEach(p => {
                const url = p.profile_url || '#';
                html += `
                    <div class="mini-card">
                        <div class="card-platform">${p.platform}</div>
                        <div class="card-username">${p.username}</div>
                        ${url !== '#' ? `<a class="card-link" href="${url}" target="_blank" rel="noopener">View profile &rarr;</a>` : ''}
                    </div>`;
            });

            html += '</div></div>';
        }

        container.innerHTML = html;
    }
});
