<?php
/**
 * Step 2 — Dati target: nome azienda, domini, IP pubblici, email
 */

require_once __DIR__ . '/../includes/functions.php';
wizard_init();

$errors = [];
$saved = wizard_get_step(2);

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $company_name = sanitize($_POST['company_name'] ?? '');
    $domains_raw  = $_POST['domains'] ?? '';
    $ips_raw      = $_POST['public_ips'] ?? '';
    $emails_raw   = $_POST['emails'] ?? '';

    // Validazione
    if ($company_name === '') {
        $errors[] = 'Il nome azienda/organizzazione è obbligatorio.';
    }

    $domains = sanitize_list($domains_raw);
    foreach ($domains as $d) {
        if (!validate_domain($d)) {
            $errors[] = "Dominio non valido: {$d}";
        }
    }
    if (empty($domains)) {
        $errors[] = 'Inserisci almeno un dominio.';
    }

    $public_ips = sanitize_list($ips_raw);
    foreach ($public_ips as $ip) {
        if (!validate_ip($ip)) {
            $errors[] = "IP non valido: {$ip}";
        }
    }

    $emails = sanitize_list($emails_raw);
    foreach ($emails as $email) {
        if (!validate_email($email)) {
            $errors[] = "Email non valida: {$email}";
        }
    }

    if (empty($errors)) {
        wizard_save_step(2, [
            'company_name' => $company_name,
            'domains'      => $domains,
            'public_ips'   => $public_ips,
            'emails'       => $emails,
        ]);
        header('Location: /index.php?step=3');
        exit;
    }
}

render_header(2);
?>

<div class="wizard-card">
    <div class="card-inner">
        <h2>Dati Target</h2>
        <p class="step-description">
            Inserisci le informazioni dell'organizzazione da monitorare. Questi dati alimentano
            tutti i moduli di scanning e i widget della dashboard.
        </p>

        <?php if (!empty($errors)): ?>
            <div class="alert alert-error">
                <?php foreach ($errors as $err): ?>
                    <div><?= $err ?></div>
                <?php endforeach; ?>
            </div>
        <?php endif; ?>

        <form method="POST" action="/index.php?step=2">
            <div class="form-group">
                <label>Nome Azienda / Organizzazione <span class="required">*</span></label>
                <input type="text" name="company_name"
                    value="<?= sanitize($saved['company_name'] ?? $_POST['company_name'] ?? '') ?>"
                    placeholder="Acme Corporation">
            </div>

            <div class="form-group">
                <label>Domini <span class="required">*</span></label>
                <textarea name="domains" placeholder="example.com&#10;example.org&#10;sub.example.com"
                    rows="3"><?= sanitize(implode("\n", $saved['domains'] ?? []) ?: ($_POST['domains'] ?? '')) ?></textarea>
                <div class="hint">Un dominio per riga, oppure separati da virgola.</div>
            </div>

            <div class="form-group">
                <label>IP Pubblici</label>
                <textarea name="public_ips" placeholder="203.0.113.10&#10;203.0.113.11"
                    rows="2"><?= sanitize(implode("\n", $saved['public_ips'] ?? []) ?: ($_POST['public_ips'] ?? '')) ?></textarea>
                <div class="hint">Opzionale. IP pubblici dell'organizzazione per scansione infrastruttura.</div>
            </div>

            <div class="form-group">
                <label>Email Aziendali</label>
                <textarea name="emails" placeholder="info@example.com&#10;admin@example.com"
                    rows="2"><?= sanitize(implode("\n", $saved['emails'] ?? []) ?: ($_POST['emails'] ?? '')) ?></textarea>
                <div class="hint">Opzionale. Email da monitorare per breach e leak.</div>
            </div>

            <div class="btn-row">
                <a href="/index.php?step=1" class="btn btn-secondary">&#8592; Indietro</a>
                <button type="submit" class="btn btn-primary">Avanti &#8594;</button>
            </div>
        </form>
    </div>
</div>

<?php render_footer(); ?>
