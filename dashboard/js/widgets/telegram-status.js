/**
 * MMON Widget — Telegram Status (VM3)
 */
MMON.registerWidget('telegram-status', {
    title: 'Telegram Status',
    gridPos: { x: 6, y: 15, w: 3, h: 3 },

    async render(container) {
        const data = await MMON.apiFetch('/widgets/telegram-status');

        const statusColors = {
            active: 'var(--success)', idle: 'var(--warning)',
            not_working: 'var(--error)', not_configured: 'var(--text-muted)'
        };
        const statusLabels = {
            active: 'ACTIVE', idle: 'IDLE', not_working: 'ERROR', not_configured: 'NOT CONFIGURED'
        };

        const color = statusColors[data.status] || 'var(--text-muted)';
        const label = statusLabels[data.status] || data.status.toUpperCase();

        container.innerHTML = `
            <div style="text-align:center;padding:16px 0">
                <div style="width:64px;height:64px;border-radius:50%;border:3px solid ${color};display:flex;align-items:center;justify-content:center;margin:0 auto 12px;font-size:28px">📡</div>
                <div style="font-family:var(--font-mono);font-size:16px;font-weight:700;color:${color}">${label}</div>
                ${data.channels_count ? `<div style="font-size:12px;color:var(--text-muted);margin-top:8px">${data.channels_count} channels monitored</div>` : ''}
                ${data.last_message_at ? `<div style="font-size:11px;color:var(--text-muted);margin-top:4px">Last msg: ${MMON.timeAgo(data.last_message_at)}</div>` : ''}
            </div>`;
    }
});
