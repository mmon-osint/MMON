<?php
/**
 * Step 8 — Riepilogo + Scrittura mmon.conf + Init DB + Lock wizard
 */

require_once __DIR__ . '/../includes/functions.php';
wizard_init();

$data = $_SESSION['wizard_data'] ?? [];
$errors = [];
$success = false;

// Verificare che tutti gli step siano completati
for ($i = 1; $i <= TOTAL_STEPS; $i++) {
    if (!isset($data["step_{$i}"])) {
        header("Location: /index.php?step={$i}");
        exit;
    }
}

// Gestione conferma (POST)
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['confirm'])) {
    // Generare e scrivere mmon.conf
    $config_content = generate_config($data);
    $written = write_config($config_content);

    if (!$written) {
        $errors[] = 'Errore nella scrittura di mmon.conf. Verifica i permessi di /opt/mmon/config/.';
    }

    // Inizializzare target nel DB
    if (empty($errors)) {
        $db_ok = init_db_targets($data);
        if (!$db_ok) {
            $errors[] = 'Errore nell\'inizializzazione del database. Verifica che PostgreSQL sia attivo.';
        }
    }

    if (empty($errors)) {
        $success = true;
        // Pulire sessione wizard
        unset($_SESSION['wizard_data']);
    }
}

// Dati per riepilogo
$s1 = $data['step_1'] ?? [];
$s2 = $data['step_2'] ?? [];
$s3 = $data['step_3'] ?? [];
$s4 = $data['step_4'] ?? [];
$s5 = $data['step_5'] ?? [];
$s6 = $data['step_6'] ?? [];
$s7 = $data['step_7'] ?? [];

// Usare step fittizio 8 per mostrare tutti i dot come "done"
render_header(TOTAL_STEPS + 1);
?>

<div class="wizard-card">
    <div class="card-inner">

        <?php if ($success): ?>
            <!-- SUCCESSO -->
            <div class="success-container">
                <div class="success-icon">&#9889;</div>
                <h2>Setup Completato</h2>
                <p class="step-description">
                    MMON è stato configurato correttamente. La configurazione è stata salvata
                    e il database è stato inizializzato con i dati target.
                </p>
                <div class="config-path">/opt/mmon/config/mmon.conf</div>
                <p style="color: var(--text-secondary); font-size: 14px; margin-top: 16px;">
                    Il wizard è stato bloccato. Per riconfigurare, eliminare il file
                    <code>/opt/mmon/config/.wizard_completed</code> e riavviare.
                </p>
                <div class="btn-row" style="justify-content: center; border: none; margin-top: 32px;">
                    <a href="/" class="btn btn-primary">Apri Dashboard &#8594;</a>
                </div>
            </div>

        <?php else: ?>
            <!-- RIEPILOGO -->
            <h2>Riepilogo Configurazione</h2>
            <p class="step-description">
                Verifica i dati inseriti. Premendo "Conferma e installa" verrà scritto il file
                di configurazione e inizializzato il database.
            </p>

            <?php if (!empty($errors)): ?>
                <div class="alert alert-error">
                    <?php foreach ($errors as $err): ?>
                        <div><?= $err ?></div>
                    <?php endforeach; ?>
                </div>
            <?php endif; ?>

            <!-- Deployment Mode -->
            <div class="summary-section">
                <h3>Deployment</h3>
                <div class="summary-row">
                    <span class="label">Modalità</span>
                    <span class="value"><?= ucfirst($s1['mode'] ?? 'N/A') ?></span>
                </div>
            </div>

            <!-- Target -->
            <div class="summary-section">
                <h3>Target</h3>
                <div class="summary-row">
                    <span class="label">Azienda</span>
                    <span class="value"><?= sanitize($s2['company_name'] ?? 'N/A') ?></span>
                </div>
                <div class="summary-row">
                    <span class="label">Domini</span>
                    <span class="value"><?= sanitize(implode(', ', $s2['domains'] ?? [])) ?></span>
                </div>
                <div class="summary-row">
                    <span class="label">IP Pubblici</span>
                    <span class="value"><?= sanitize(implode(', ', $s2['public_ips'] ?? []) ?: '—') ?></span>
                </div>
                <div class="summary-row">
                    <span class="label">Email</span>
                    <span class="value"><?= sanitize(implode(', ', $s2['emails'] ?? []) ?: '—') ?></span>
                </div>
            </div>

            <!-- Social -->
            <div class="summary-section">
                <h3>Social Footprint</h3>
                <div class="summary-row">
                    <span class="label">Username</span>
                    <span class="value"><?= sanitize(implode(', ', $s3['usernames'] ?? []) ?: '—') ?></span>
                </div>
                <div class="summary-row">
                    <span class="label">Nominativi</span>
                    <span class="value"><?= sanitize(implode(', ', $s3['full_names'] ?? []) ?: '—') ?></span>
                </div>
            </div>

            <!-- Tech -->
            <div class="summary-section">
                <h3>Tecnologie</h3>
                <div class="summary-row">
                    <span class="label">Stack</span>
                    <span class="value"><?= sanitize(implode(', ', $s4['technologies'] ?? []) ?: '—') ?></span>
                </div>
            </div>

            <!-- Sector -->
            <div class="summary-section">
                <h3>Settore</h3>
                <div class="summary-row">
                    <span class="label">Industria</span>
                    <span class="value"><?= sanitize($s5['industry'] ?? 'N/A') ?></span>
                </div>
                <div class="summary-row">
                    <span class="label">Prodotti</span>
                    <span class="value"><?= sanitize(implode(', ', $s5['products'] ?? []) ?: '—') ?></span>
                </div>
            </div>

            <!-- API Keys -->
            <div class="summary-section">
                <h3>API Keys</h3>
                <div class="summary-row">
                    <span class="label">Shodan</span>
                    <span class="value"><?= ($s6['shodan_key'] ?? '') !== '' ? '&#9679;&#9679;&#9679;&#9679; configurata' : '— non configurata' ?></span>
                </div>
                <div class="summary-row">
                    <span class="label">Criminal IP</span>
                    <span class="value"><?= ($s6['criminal_ip_key'] ?? '') !== '' ? '&#9679;&#9679;&#9679;&#9679; configurata' : '— non configurata' ?></span>
                </div>
                <div class="summary-row">
                    <span class="label">Quake360</span>
                    <span class="value"><?= ($s6['quake360_key'] ?? '') !== '' ? '&#9679;&#9679;&#9679;&#9679; configurata' : '— non configurata' ?></span>
                </div>
            </div>

            <!-- Infrastructure -->
            <div class="summary-section">
                <h3>Infrastruttura</h3>
                <div class="summary-row">
                    <span class="label">Backend</span>
                    <span class="value"><?= sanitize($s7['backend_ip'] ?? 'N/A') ?></span>
                </div>
                <div class="summary-row">
                    <span class="label">VM1 (Clearnet)</span>
                    <span class="value"><?= sanitize($s7['vm1_ip'] ?? 'N/A') ?></span>
                </div>
                <div class="summary-row">
                    <span class="label">VM2 (Deep)</span>
                    <span class="value"><?= sanitize($s7['vm2_ip'] ?? '') ?: '— non configurata' ?></span>
                </div>
                <div class="summary-row">
                    <span class="label">VM3 (Telegram)</span>
                    <span class="value"><?= sanitize($s7['vm3_ip'] ?? '') ?: '— non configurata' ?></span>
                </div>
                <div class="summary-row">
                    <span class="label">Tor</span>
                    <span class="value"><?= ($s7['tor_control_password'] ?? '') !== '' ? 'configurato' : '— non configurato' ?></span>
                </div>
                <div class="summary-row">
                    <span class="label">Telegram</span>
                    <span class="value"><?= ($s7['tg_api_id'] ?? '') !== '' ? 'configurato' : '— non configurato' ?></span>
                </div>
            </div>

            <form method="POST" action="/index.php?step=8">
                <div class="alert alert-warning">
                    Una volta confermato, il file <code>mmon.conf</code> verrà scritto e il wizard
                    verrà bloccato. Per riconfigurare sarà necessario un reset manuale.
                </div>

                <div class="btn-row">
                    <a href="/index.php?step=7" class="btn btn-secondary">&#8592; Modifica</a>
                    <button type="submit" name="confirm" value="1" class="btn btn-primary">
                        &#9889; Conferma e installa
                    </button>
                </div>
            </form>

        <?php endif; ?>

    </div>
</div>

<?php render_footer(); ?>
