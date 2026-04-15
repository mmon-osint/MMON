<?php
/**
 * Step 4 — Tecnologie: stack usato dall'organizzazione (per CVE feed)
 */
require_once __DIR__ . '/../includes/functions.php';
$data = wizard_get_step(4);
render_header(4);

$categories = [
    'web_server' => ['Apache', 'Nginx', 'IIS', 'LiteSpeed', 'Caddy', 'Tomcat'],
    'database'   => ['PostgreSQL', 'MySQL', 'MariaDB', 'MongoDB', 'Redis', 'Oracle', 'MSSQL', 'Elasticsearch'],
    'language'   => ['Python', 'Java', 'PHP', 'Node.js', 'Go', 'Ruby', '.NET', 'Rust'],
    'cms'        => ['WordPress', 'Drupal', 'Joomla', 'Magento', 'Shopify', 'Ghost'],
    'cloud'      => ['AWS', 'Azure', 'GCP', 'DigitalOcean', 'Hetzner', 'OVH'],
    'security'   => ['Cloudflare', 'CrowdStrike', 'Palo Alto', 'Fortinet', 'Wazuh', 'Snort'],
    'mail'       => ['Exchange', 'Postfix', 'Zimbra', 'Google Workspace', 'ProtonMail'],
    'network'    => ['Cisco', 'Fortinet', 'Juniper', 'MikroTik', 'Ubiquiti', 'pfSense'],
];
?>
<div class="step-content">
    <h2>Tecnologie</h2>
    <p class="step-desc">Seleziona le tecnologie usate dall'organizzazione. Alimentano il CVE Feed e Infrastructure widget.</p>

    <form method="POST" action="?step=4">
        <div class="tech-grid">
            <?php foreach ($categories as $cat => $options): ?>
            <div class="tech-category">
                <h3><?= ucfirst(str_replace('_', ' ', $cat)) ?></h3>
                <div class="tech-options">
                    <?php foreach ($options as $opt):
                        $checked = in_array($opt, (array)($data[$cat] ?? [])) ? 'checked' : '';
                    ?>
                    <label class="tech-chip">
                        <input type="checkbox" name="<?= $cat ?>[]" value="<?= $opt ?>" <?= $checked ?>>
                        <span><?= $opt ?></span>
                    </label>
                    <?php endforeach; ?>
                </div>
            </div>
            <?php endforeach; ?>
        </div>

        <div class="form-group" style="margin-top: 24px;">
            <label for="custom_tech">Altre tecnologie (opzionale)</label>
            <input type="text" id="custom_tech" name="custom_tech"
                   value="<?= htmlspecialchars($data['custom_tech'] ?? '') ?>"
                   placeholder="Tecnologie custom, separate da virgola">
        </div>

        <div class="step-actions">
            <a href="?step=3" class="btn btn-ghost">← Indietro</a>
            <button type="submit" class="btn btn-primary">Avanti →</button>
        </div>
    </form>
</div>
<?php render_footer(); ?>
