/**
 * MMON Widget — STATUS (VM2)
 * Uptime motori, Tor status, IP VM, ultimo crawl.
 */
MMON.registerWidget('status', {
    title: 'System Status',
    gridPos: { x: 0, y: 12, w: 4, h: 3 },

    async render(container) {
        const data = await MMON.apiFetch('/widgets/status');

        const vmStatus = (s) => {
            const colors = { active: 'var(--success)', unknown: 'var(--text-muted)', error: 'var(--error)' };
            return `<span style="color:${colors[s] || colors.unknown}; font-weight:600">${s.toUpperCase()}</span>`;
        };

        const torIcon = data.tor_connected
            ? '<span style="color:var(--success)">● Connected</span>'
            : '<span style="color:var(--text-muted)">○ Disconnected</span>';

        const lastCrawl = data.last_crawl_at ? MMON.timeAgo(data.last_crawl_at) : 'Never';

        container.innerHTML = `
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
                <div class="mini-card">
                    <div class="card-platform">VM1 Clearnet</div>
                    <div style="margin-top:6px">${vmStatus(data.vm1_status)}</div>
                </div>
                <div class="mini-card">
                    <div class="card-platform">VM2 Deep Web</div>
                    <div style="margin-top:6px">${vmStatus(data.vm2_status)}</div>
                </div>
                <div class="mini-card">
                    <div class="card-platform">VM3 Telegram</div>
                    <div style="margin-top:6px">${vmStatus(data.vm3_status)}</div>
                </div>
                <div class="mini-card">
                    <div class="card-platform">Tor Circuit</div>
                    <div style="margin-top:6px">${torIcon}</div>
                    ${data.tor_exit_ip ? `<div style="font-family:var(--font-mono);font-size:11px;color:var(--text-muted);margin-top:4px">${data.tor_exit_ip}</div>` : ''}
                </div>
            </div>
            <div style="display:flex;justify-content:space-between;margin-top:12px;padding-top:10px;border-top:1px solid var(--border);font-size:12px;color:var(--text-muted)">
                <span>Total findings: <strong style="color:var(--accent)">${data.total_findings}</strong></span>
                <span>Last crawl: <strong>${lastCrawl}</strong></span>
            </div>`;
    }
});
