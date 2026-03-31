<?php
/**
 * Step 3 — Username e nominativi da monitorare (Social Footprint + Keywords)
 */

require_once __DIR__ . '/../includes/functions.php';
wizard_init();

$errors = [];
$saved = wizard_get_step(3);

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $usernames_raw  = $_POST['usernames'] ?? '';
    $full_names_raw = $_POST['full_names'] ?? '';

    $usernames  = sanitize_list($usernames_raw);
    $full_names = sanitize_list($full_names_raw);

    if (empty($usernames) && empty($full_names)) {
        $errors[] = 'Inserisci almeno un username o un nominativo da monitorare.';
    }

    if (empty($errors)) {
        wizard_save_step(3, [
            'usernames'  => $usernames,
            'full_names' => $full_names,
        ]);
        header('Location: /index.php?step=4');
        exit;
    }
}

render_header(3);
?>

<div class="wizard-card">
    <div class="card-inner">
        <h2>Social Footprint</h2>
        <p class="step-description">
            Username e nominativi delle persone chiave da monitorare. Questi dati alimentano
            i widget Social Footprint e Keywords tramite maigret, mosint e Google Dorks.
        </p>

        <?php if (!empty($errors)): ?>
            <div class="alert alert-error">
                <?php foreach ($errors as $err): ?>
                    <div><?= $err ?></div>
                <?php endforeach; ?>
            </div>
        <?php endif; ?>

        <form method="POST" action="/index.php?step=3">
            <div class="form-group">
                <label>Username da monitorare</label>
                <textarea name="usernames" placeholder="johndoe&#10;janedoe&#10;ceo_handle"
                    rows="4"><?= sanitize(implode("\n", $saved['usernames'] ?? []) ?: ($_POST['usernames'] ?? '')) ?></textarea>
                <div class="hint">Uno per riga. Verranno cercati su tutte le piattaforme social note (maigret).</div>
            </div>

            <div class="form-group">
                <label>Nomi e Cognomi</label>
                <textarea name="full_names" placeholder="Mario Rossi&#10;Laura Bianchi"
                    rows="4"><?= sanitize(implode("\n", $saved['full_names'] ?? []) ?: ($_POST['full_names'] ?? '')) ?></textarea>
                <div class="hint">Uno per riga. Usati per Google Dorks e ricerche cross-platform.</div>
            </div>

            <div class="alert alert-info">
                Inserisci le figure chiave dell'organizzazione: CEO, CTO, CISO, responsabili IT,
                e chiunque abbia un profilo pubblico rilevante.
            </div>

            <div class="btn-row">
                <a href="/index.php?step=2" class="btn btn-secondary">&#8592; Indietro</a>
                <button type="submit" class="btn btn-primary">Avanti &#8594;</button>
            </div>
        </form>
    </div>
</div>

<?php render_footer(); ?>
