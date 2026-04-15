/**
 * MMON Widget — Monitored Channels (VM3)
 */
MMON.registerWidget('monitored-channels', {
    title: 'Monitored Channels',
    gridPos: { x: 9, y: 15, w: 3, h: 3 },

    async render(container) {
        const data = await MMON.apiFetch('/widgets/monitored-channels?limit=20');

        if (!data.items || data.items.length === 0) {
            container.innerHTML = '<div class="widget-empty"><div class="empty-icon">📺</div><div>No channels monitored</div><div style="font-size:11px;color:var(--text-muted)">Configure Telegram in the wizard</div></div>';
            return;
        }

        let html = '';
        data.items.forEach(item => {
            html += `<div class="mini-card" style="margin-bottom:6px;padding:10px">
                <div style="display:flex;justify-content:space-between;align-items:center">
                    <div style="font-weight:600;font-size:13px">${item.channel_name}</div>
                    <span style="font-family:var(--font-mono);font-size:11px;color:var(--accent)">${item.messages_collected}</span>
                </div>
                <div style="font-size:11px;color:var(--text-muted);margin-top:4px">
                    ${item.members_count ? item.members_count + ' members · ' : ''}${item.last_message_at ? MMON.timeAgo(item.last_message_at) : 'no data'}
                </div>
            </div>`;
        });
        container.innerHTML = html;
    }
});
