<?php
/**
 * Step 8 — Summary + Conferma + Genera config
 */
require_once __DIR__ . '/../includes/functions.php';
$w = $_SESSION['wizard'];
$s1 = $w['step1'] ?? [];
$s2 = $w['step2'] ?? [];
$s3 = $w['step3'] ?? [];
$s4 = $w['step4'] ?? [];
$s5 = $w['step5'] ?? [];
$s6 = $w['step6'] ?? [];
$s7 = $w['step7'] ?? [];

// Se POST su step 8 → genera config e scrivi
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['confirm'])) {
    $conf_ok = write_config();
    $db_ok = init_db_targets();

    if ($conf_ok) {
        // Redirect a pagina successo
        header('Location: ?step=8&done=1');
        exit;
    }
}

render_header(8);

// Pagina successo post-config
if (isset($_GET['done'])):
?>
<div class="step-content success-page">
    <div class="success-icon">✓</div>
    <h2>Setup Completato!</h2>
    <p>La configurazione è stata scritta in <code>/opt/mmon/config/mmon.conf</code></p>
    <p>I target sono stati inizializzati nel database.</p>

    <div class="next-steps">
        <h3>Prossimi passi:</h3>
        <ol>
            <li>Avvia il backend: <code>sudo systemctl start mmon-api</code></li>
            <li>Avvia VM1 scheduler: <code>sudo systemctl start mmon-scheduler</code> (sulla VM1)</li>
            <li>Imposta la password admin al primo login nella dashboard</li>
        </ol>
    </div>

    <div class="step-actions">
        <a href="/" class="btn btn-primary">Vai alla Dashboard →</a>
    </div>
</div>
<?php render_footer(); return; endif; ?>

<div class="step-content">
    <h2>Riepilogo Configurazione</h2>
    <p class="step-desc">Verifica i dati prima di generare la configurazione.</p>

    <div class="summary-sections">
        <div class="summary-card">
            <h3>Modalità</h3>
            <p class="summary-value"><?= ucfirst($s1['mode'] ?? 'personal') ?></p>
        </div>

        <div class="summary-card">
            <h3>Target</h3>
            <p><strong>Azienda:</strong> <?= htmlspecialchars($s2['company_name'] ?? '—') ?></p>
            <p><strong>Domini:</strong> <?= htmlspecialchars($s2['domains'] ?? '—') ?></p>
            <p><strong>IP:</strong> <?= htmlspecialchars($s2['public_ips'] ?? '—') ?></p>
            <p><strong>Email:</strong> <?= htmlspecialchars($s2['emails'] ?? '—') ?></p>
        </div>

        <div class="summary-card">
            <h3>Social</h3>
            <p><strong>Username:</strong> <?= nl2br(htmlspecialchars($s3['usernames'] ?? '—')) ?></p>
            <p><strong>Nomi:</strong> <?= nl2br(htmlspecialchars($s3['full_names'] ?? '—')) ?></p>
        </div>

        <div class="summary-card">
            <h3>Tecnologie</h3>
            <?php
            $tech_fields = ['web_server', 'database', 'language', 'cms', 'cloud', 'security', 'mail', 'network'];
            foreach ($tech_fields as $f):
                $val = $s4[$f] ?? [];
                if (is_array($val) && !empty($val)):
            ?>
            <p><strong><?= ucfirst(str_replace('_', ' ', $f)) ?>:</strong> <?= implode(', ', $val) ?></p>
            <?php endif; endforeach; ?>
        </div>

        <div class="summary-card">
            <h3>Settore</h3>
            <p><strong>Industria:</strong> <?= ucfirst($s5['industry'] ?? '—') ?></p>
            <p><strong>Prodotti:</strong> <?= htmlspecialchars($s5['products'] ?? '—') ?></p>
            <p><strong>Competitor:</strong> <?= htmlspecialchars($s5['competitors'] ?? '—') ?></p>
        </div>

        <div class="summary-card">
            <h3>API Keys</h3>
            <p><strong>Shodan:</strong> <?= !empty($s6['shodan']) ? '✓ Configurata' : '✗ Non impostata' ?></p>
            <p><strong>Criminal IP:</strong> <?= !empty($s6['criminal_ip']) ? '✓ Configurata' : '✗ Non impostata' ?></p>
            <p><strong>Quake360:</strong> <?= !empty($s6['quake360']) ? '✓ Configurata' : '✗ Non impostata' ?></p>
        </div>

        <div class="summary-card">
            <h3>Infrastruttura</h3>
            <p><strong>Backend (VM0):</strong> <?= htmlspecialchars($s7['backend_ip'] ?? '—') ?></p>
            <p><strong>Clearnet (VM1):</strong> <?= htmlspecialchars($s7['vm1_ip'] ?? '—') ?></p>
            <p><strong>Deep Web (VM2):</strong> <?= htmlspecialchars($s7['vm2_ip'] ?? '—') ?></p>
            <p><strong>Telegram (VM3):</strong> <?= htmlspecialchars($s7['vm3_ip'] ?? '—') ?></p>
        </div>
    </div>

    <form method="POST" action="?step=8">
        <div class="step-actions">
            <a href="?step=7" class="btn btn-ghost">← Indietro</a>
            <button type="submit" name="confirm" value="1" class="btn btn-primary btn-confirm">
                Conferma e Genera Configurazione
            </button>
        </div>
    </form>
</div>
<?php render_footer(); ?>
