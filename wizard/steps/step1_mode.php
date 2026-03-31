<?php
/**
 * Step 1 — Selezione modalità: Personal / Company
 */

require_once __DIR__ . '/../includes/functions.php';
wizard_init();

$errors = [];
$saved = wizard_get_step(1);

// Gestione POST
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $mode = $_POST['mode'] ?? '';

    if (!in_array($mode, ['personal', 'company'])) {
        $errors[] = 'Seleziona una modalità di deployment.';
    }

    if (empty($errors)) {
        wizard_save_step(1, ['mode' => $mode]);
        header('Location: /index.php?step=2');
        exit;
    }
}

$current_mode = $saved['mode'] ?? '';

render_header(1);
?>

<div class="wizard-card">
    <div class="card-inner">
        <h2>Modalità di Deployment</h2>
        <p class="step-description">
            Scegli come verrà utilizzato MMON. Questa scelta determina il sistema di autenticazione
            e le funzionalità multi-utente.
        </p>

        <?php if (!empty($errors)): ?>
            <div class="alert alert-error">
                <?php foreach ($errors as $err): ?>
                    <div><?= sanitize($err) ?></div>
                <?php endforeach; ?>
            </div>
        <?php endif; ?>

        <form method="POST" action="/index.php?step=1">
            <div class="mode-selector">
                <div class="mode-option">
                    <input type="radio" name="mode" id="mode_personal" value="personal"
                        <?= $current_mode === 'personal' ? 'checked' : '' ?>>
                    <label class="mode-card" for="mode_personal">
                        <div class="mode-icon">&#128273;</div>
                        <div class="mode-title">Personal</div>
                        <div class="mode-desc">
                            Single user con autenticazione JWT locale.
                            Ideale per analisti individuali o piccoli team.
                        </div>
                    </label>
                </div>

                <div class="mode-option">
                    <input type="radio" name="mode" id="mode_company" value="company"
                        <?= $current_mode === 'company' ? 'checked' : '' ?>>
                    <label class="mode-card" for="mode_company">
                        <div class="mode-icon">&#127970;</div>
                        <div class="mode-title">Company</div>
                        <div class="mode-desc">
                            Multi-user con Keycloak: RBAC, SSO, LDAP.
                            Per SOC team e security department aziendali.
                        </div>
                    </label>
                </div>
            </div>

            <div class="alert alert-info" style="margin-top: 24px;">
                La modalità Company richiede Keycloak configurato separatamente.
                Puoi iniziare in modalità Personal e migrare successivamente.
            </div>

            <div class="btn-row">
                <span></span>
                <button type="submit" class="btn btn-primary">Avanti &#8594;</button>
            </div>
        </form>
    </div>
</div>

<?php render_footer(); ?>
