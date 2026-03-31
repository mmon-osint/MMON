<?php
/**
 * Step 7 — IP delle 3 VM, configurazione Tor e Telegram puppet account
 */

require_once __DIR__ . '/../includes/functions.php';
wizard_init();

$errors = [];
$saved = wizard_get_step(7);

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $backend_ip = sanitize($_POST['backend_ip'] ?? '');
    $vm1_ip     = sanitize($_POST['vm1_ip'] ?? '');
    $vm2_ip     = sanitize($_POST['vm2_ip'] ?? '');
    $vm3_ip     = sanitize($_POST['vm3_ip'] ?? '');

    // Validazione IP obbligatori
    if ($backend_ip === '' || !validate_ip($backend_ip)) {
        $errors[] = 'IP backend non valido.';
    }
    if ($vm1_ip === '' || !validate_ip($vm1_ip)) {
        $errors[] = 'IP VM1 non valido.';
    }

    // VM2 e VM3 opzionali (sviluppo posticipato)
    if ($vm2_ip !== '' && !validate_ip($vm2_ip)) {
        $errors[] = 'IP VM2 non valido.';
    }
    if ($vm3_ip !== '' && !validate_ip($vm3_ip)) {
        $errors[] = 'IP VM3 non valido.';
    }

    // Tor config (opzionale)
    $tor_socks_port       = sanitize($_POST['tor_socks_port'] ?? '9050');
    $tor_control_port     = sanitize($_POST['tor_control_port'] ?? '9051');
    $tor_control_password = sanitize($_POST['tor_control_password'] ?? '');

    // Telegram config (opzionale)
    $tg_api_id  = sanitize($_POST['tg_api_id'] ?? '');
    $tg_api_hash = sanitize($_POST['tg_api_hash'] ?? '');
    $tg_phone    = sanitize($_POST['tg_phone'] ?? '');

    if (empty($errors)) {
        wizard_save_step(7, [
            'backend_ip'           => $backend_ip,
            'vm1_ip'               => $vm1_ip,
            'vm2_ip'               => $vm2_ip,
            'vm3_ip'               => $vm3_ip,
            'tor_socks_port'       => $tor_socks_port,
            'tor_control_port'     => $tor_control_port,
            'tor_control_password' => $tor_control_password,
            'tg_api_id'            => $tg_api_id,
            'tg_api_hash'          => $tg_api_hash,
            'tg_phone'             => $tg_phone,
        ]);
        header('Location: /index.php?step=8');
        exit;
    }
}

render_header(7);
?>

<div class="wizard-card">
    <div class="card-inner">
        <h2>Infrastruttura</h2>
        <p class="step-description">
            Configura gli indirizzi IP delle VM e i parametri di connessione per Tor e Telegram.
            VM2 e VM3 sono opzionali in questa fase (sviluppo M8/M9).
        </p>

        <?php if (!empty($errors)): ?>
            <div class="alert alert-error">
                <?php foreach ($errors as $err): ?>
                    <div><?= $err ?></div>
                <?php endforeach; ?>
            </div>
        <?php endif; ?>

        <form method="POST" action="/index.php?step=7">

            <!-- IP VM -->
            <div class="form-group">
                <label>IP Backend <span class="required">*</span></label>
                <input type="text" name="backend_ip"
                    value="<?= sanitize($saved['backend_ip'] ?? $_POST['backend_ip'] ?? '127.0.0.1') ?>"
                    placeholder="192.168.1.10">
                <div class="hint">IP della macchina che ospita FastAPI, PostgreSQL, Redis, Dashboard.</div>
            </div>

            <div class="form-group">
                <label>IP VM1 — CLEARNET-ENGINE <span class="required">*</span></label>
                <input type="text" name="vm1_ip"
                    value="<?= sanitize($saved['vm1_ip'] ?? $_POST['vm1_ip'] ?? '') ?>"
                    placeholder="192.168.1.11">
                <div class="hint">Se VM1 e backend sono sulla stessa macchina (Personal mode), usa 127.0.0.1.</div>
            </div>

            <div class="form-group">
                <label>IP VM2 — DEEP-ENGINE</label>
                <input type="text" name="vm2_ip"
                    value="<?= sanitize($saved['vm2_ip'] ?? $_POST['vm2_ip'] ?? '') ?>"
                    placeholder="192.168.1.12">
                <div class="hint">Opzionale. Configurare quando VM2 sarà operativa (M8).</div>
            </div>

            <div class="form-group">
                <label>IP VM3 — TG-ENGINE</label>
                <input type="text" name="vm3_ip"
                    value="<?= sanitize($saved['vm3_ip'] ?? $_POST['vm3_ip'] ?? '') ?>"
                    placeholder="192.168.1.13">
                <div class="hint">Opzionale. Configurare quando VM3 sarà operativa (M9).</div>
            </div>

            <hr style="border-color: var(--border); margin: 32px 0;">

            <!-- Tor Configuration -->
            <h2 style="font-size: 16px; margin-bottom: 16px;">Tor Configuration (VM2)</h2>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                <div class="form-group">
                    <label>SOCKS Port</label>
                    <input type="number" name="tor_socks_port"
                        value="<?= sanitize($saved['tor_socks_port'] ?? '9050') ?>"
                        placeholder="9050">
                </div>
                <div class="form-group">
                    <label>Control Port</label>
                    <input type="number" name="tor_control_port"
                        value="<?= sanitize($saved['tor_control_port'] ?? '9051') ?>"
                        placeholder="9051">
                </div>
            </div>

            <div class="form-group">
                <label>Tor Control Password</label>
                <input type="password" name="tor_control_password"
                    value="<?= sanitize($saved['tor_control_password'] ?? '') ?>"
                    placeholder="Password per Tor ControlPort"
                    autocomplete="off">
                <div class="hint">Opzionale. Generare con: <code>tor --hash-password "tua_password"</code></div>
            </div>

            <hr style="border-color: var(--border); margin: 32px 0;">

            <!-- Telegram Configuration -->
            <h2 style="font-size: 16px; margin-bottom: 16px;">Telegram Puppet Account (VM3)</h2>

            <div class="form-group">
                <label>Telegram API ID</label>
                <input type="text" name="tg_api_id"
                    value="<?= sanitize($saved['tg_api_id'] ?? '') ?>"
                    placeholder="12345678">
                <div class="hint">Ottenibile da <a href="https://my.telegram.org" target="_blank" style="color: var(--accent);">my.telegram.org</a></div>
            </div>

            <div class="form-group">
                <label>Telegram API Hash</label>
                <input type="password" name="tg_api_hash"
                    value="<?= sanitize($saved['tg_api_hash'] ?? '') ?>"
                    placeholder="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                    autocomplete="off">
            </div>

            <div class="form-group">
                <label>Numero di telefono puppet</label>
                <input type="text" name="tg_phone"
                    value="<?= sanitize($saved['tg_phone'] ?? '') ?>"
                    placeholder="+391234567890">
                <div class="hint">Numero del puppet account Telegram dedicato al monitoring.</div>
            </div>

            <div class="alert alert-warning">
                Usa un numero di telefono dedicato per il puppet account Telegram.
                Non usare il tuo numero personale.
            </div>

            <div class="btn-row">
                <a href="/index.php?step=6" class="btn btn-secondary">&#8592; Indietro</a>
                <button type="submit" class="btn btn-primary">Riepilogo &#8594;</button>
            </div>
        </form>
    </div>
</div>

<?php render_footer(); ?>
