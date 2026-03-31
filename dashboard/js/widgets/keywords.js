/**
 * MMON Widget — Keywords Monitor
 * Mostra menzioni di keyword monitorate (leak, dork, mention).
 */

MMON.registerWidget('keywords', {
    title: 'Keywords Monitor',
    gridPos: { x: 6, y: 4, w: 6, h: 4 },

    async render(container, filters) {
        const params = new URLSearchParams();
        if (filters.severity?.length) params.set('severity', filters.severity.join(','));
        if (filters.date_from) params.set('date_from', filters.date_from);
        if (filters.date_to) params.set('date_to', filters.date_to);

        const data = await MMON.apiFetch(`/widgets/keywords?${params}`);
        const countEl = document.getElementById('count-keywords');

        if (!data.items || data.items.length === 0) {
            container.innerHTML = `
                <div class="widget-empty">
                    <div class="empty-icon">&#128270;</div>
                    <div>No keyword hits yet</div>
                    <div style="font-size:11px; color:var(--text-muted);">Matches from dorks, leaks, and dark web mentions will appear here</div>
                </div>`;
            if (countEl) countEl.textContent = '0';
            return;
        }

        if (countEl) countEl.textContent = data.total_hits;

        let html = `
            <table class="widget-table">
                <thead>
                    <tr>
                        <th>Keyword</th>
                        <th>Context</th>
                        <th>Source</th>
                        <th>Sev</th>
                        <th>When</th>
                    </tr>
                </thead>
                <tbody>`;

        data.items.forEach(item => {
            const keyword = item.keyword || item.matched_keyword || '—';
            const context = MMON.truncate(item.context || item.snippet || item.description || '', 55);
            const source = item.source_tool || item.source || '—';
            const sev = item.severity || 'info';
            const sevBadge = `<span class="${MMON.severityClass(sev)}">${sev}</span>`;
            const when = item.created_at ? MMON.timeAgo(item.created_at) : '—';

            // Source URL se disponibile
            const sourceUrl = item.source_url || item.url;
            const sourceLink = sourceUrl
                ? `<a href="${sourceUrl}" target="_blank" rel="noopener" style="color:var(--accent-secondary); text-decoration:none; font-size:11px;">${source} &rarr;</a>`
                : `<span style="color:var(--text-muted); font-size:11px;">${source}</span>`;

            html += `
                <tr>
                    <td>
                        <span style="font-family:var(--font-mono); font-size:12px; background:var(--accent-dim); padding:2px 6px; border-radius:3px; color:var(--accent);">
                            ${keyword}
                        </span>
                    </td>
                    <td title="${item.context || item.snippet || ''}" style="font-size:12px; color:var(--text-secondary);">${context}</td>
                    <td>${sourceLink}</td>
                    <td>${sevBadge}</td>
                    <td style="color:var(--text-muted); font-size:11px;">${when}</td>
                </tr>`;
        });

        html += '</tbody></table>';

        // Keyword frequency summary
        if (data.keyword_counts && Object.keys(data.keyword_counts).length > 0) {
            html += `<div style="display:flex; flex-wrap:wrap; gap:8px; padding:12px 0 0; border-top:1px solid var(--border); margin-top:12px;">`;
            for (const [kw, count] of Object.entries(data.keyword_counts)) {
                html += `<span style="font-family:var(--font-mono); font-size:11px; background:rgba(123,97,255,0.15); color:var(--accent-secondary); padding:3px 8px; border-radius:3px;">${kw}: ${count}</span>`;
            }
            html += '</div>';
        }

        container.innerHTML = html;
    }
});
