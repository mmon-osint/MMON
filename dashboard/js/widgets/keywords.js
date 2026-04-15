/**
 * MMON Widget — Keywords Monitor
 */
MMON.registerWidget('keywords', {
    title: 'Keywords Monitor',
    gridPos: { x: 6, y: 4, w: 6, h: 4 },

    async render(container, filters) {
        const params = new URLSearchParams();
        if (filters.severity?.length) params.set('severity', filters.severity.join(','));
        const data = await MMON.apiFetch(`/widgets/keywords?${params}`);

        if (!data.items || data.items.length === 0) {
            container.innerHTML = '<div class="widget-empty"><div class="empty-icon">🔍</div><div>No keyword hits yet</div></div>';
            return;
        }

        let html = '<table class="widget-table"><thead><tr><th>Keyword</th><th>Context</th><th>Source</th><th>Sev</th></tr></thead><tbody>';
        data.items.forEach(item => {
            const kw = item.keyword || '—';
            html += `<tr><td><span style="font-family:var(--font-mono);font-size:12px;background:var(--accent-dim);padding:2px 6px;border-radius:3px;color:var(--accent)">${kw}</span></td><td style="font-size:12px;color:var(--text-secondary)">${MMON.truncate(item.context || '', 50)}</td><td style="font-size:11px;color:var(--text-muted)">${item.source_tool || ''}</td><td><span class="${MMON.severityClass(item.severity)}">${item.severity}</span></td></tr>`;
        });
        html += '</tbody></table>';

        if (data.keyword_counts && Object.keys(data.keyword_counts).length > 0) {
            html += '<div style="display:flex;flex-wrap:wrap;gap:6px;padding:10px 0 0;border-top:1px solid var(--border);margin-top:10px">';
            for (const [kw, count] of Object.entries(data.keyword_counts)) {
                html += `<span style="font-family:var(--font-mono);font-size:11px;background:rgba(123,97,255,0.15);color:var(--accent-secondary);padding:2px 8px;border-radius:3px">${kw}: ${count}</span>`;
            }
            html += '</div>';
        }
        container.innerHTML = html;
    }
});
