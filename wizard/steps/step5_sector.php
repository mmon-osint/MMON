<?php
/**
 * Step 5 — Settore/industria e prodotti (widget Competitors)
 */

require_once __DIR__ . '/../includes/functions.php';
wizard_init();

$errors = [];
$saved = wizard_get_step(5);

$industries = [
    'cybersecurity',
    'fintech',
    'healthcare',
    'e-commerce',
    'saas',
    'manufacturing',
    'energy',
    'telecommunications',
    'government',
    'education',
    'media',
    'logistics',
    'real-estate',
    'legal',
    'consulting',
    'other',
];

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $industry = sanitize($_POST['industry'] ?? '');
    $industry_custom = sanitize($_POST['industry_custom'] ?? '');
    $products_raw = $_POST['products'] ?? '';

    if ($industry === 'other' && $industry_custom !== '') {
        $industry = $industry_custom;
    }

    if ($industry === '' || $industry === 'other') {
        $errors[] = 'Seleziona o specifica un settore.';
    }

    $products = sanitize_list($products_raw);

    if (empty($errors)) {
        wizard_save_step(5, [
            'industry' => $industry,
            'products' => $products,
        ]);
        header('Location: /index.php?step=6');
        exit;
    }
}

render_header(5);
?>

<div class="wizard-card">
    <div class="card-inner">
        <h2>Settore e Prodotti</h2>
        <p class="step-description">
            Queste informazioni alimentano il widget Competitors, che identifica aziende
            e prodotti competitor nel tuo settore di riferimento.
        </p>

        <?php if (!empty($errors)): ?>
            <div class="alert alert-error">
                <?php foreach ($errors as $err): ?>
                    <div><?= $err ?></div>
                <?php endforeach; ?>
            </div>
        <?php endif; ?>

        <form method="POST" action="/index.php?step=5">
            <div class="form-group">
                <label>Settore / Industria <span class="required">*</span></label>
                <select name="industry" id="industry_select" onchange="toggleCustomIndustry()">
                    <option value="">— Seleziona settore —</option>
                    <?php foreach ($industries as $ind): ?>
                        <option value="<?= $ind ?>"
                            <?= ($saved['industry'] ?? '') === $ind ? 'selected' : '' ?>>
                            <?= ucfirst(str_replace('-', ' ', $ind)) ?>
                        </option>
                    <?php endforeach; ?>
                </select>
            </div>

            <div class="form-group" id="custom_industry_group"
                style="display: <?= ($saved['industry'] ?? '') === 'other' ? 'block' : 'none' ?>;">
                <label>Specifica settore</label>
                <input type="text" name="industry_custom"
                    value="<?= sanitize($saved['industry_custom'] ?? $_POST['industry_custom'] ?? '') ?>"
                    placeholder="Il tuo settore specifico">
            </div>

            <div class="form-group">
                <label>Prodotti / Servizi principali</label>
                <textarea name="products" placeholder="monitoring platform&#10;threat intelligence&#10;SIEM as a service"
                    rows="3"><?= sanitize(implode("\n", $saved['products'] ?? []) ?: ($_POST['products'] ?? '')) ?></textarea>
                <div class="hint">Opzionale. I tuoi prodotti/servizi principali, uno per riga. Aiutano a identificare competitor diretti.</div>
            </div>

            <div class="btn-row">
                <a href="/index.php?step=4" class="btn btn-secondary">&#8592; Indietro</a>
                <button type="submit" class="btn btn-primary">Avanti &#8594;</button>
            </div>
        </form>
    </div>
</div>

<script>
function toggleCustomIndustry() {
    const sel = document.getElementById('industry_select');
    const grp = document.getElementById('custom_industry_group');
    grp.style.display = sel.value === 'other' ? 'block' : 'none';
}
</script>

<?php render_footer(); ?>
