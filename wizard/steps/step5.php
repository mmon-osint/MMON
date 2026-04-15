<?php
/**
 * Step 5 — Settore e prodotti (widget Competitors)
 */
require_once __DIR__ . '/../includes/functions.php';
$data = wizard_get_step(5);
render_header(5);

$industries = [
    'finance', 'healthcare', 'technology', 'manufacturing', 'retail',
    'energy', 'telecommunications', 'education', 'government', 'defense',
    'legal', 'media', 'transportation', 'real_estate', 'agriculture', 'other'
];
?>
<div class="step-content">
    <h2>Settore e Prodotti</h2>
    <p class="step-desc">Informazioni per il widget Competitors e il monitoraggio di settore.</p>

    <form method="POST" action="?step=5">
        <div class="form-group">
            <label for="industry">Settore</label>
            <select id="industry" name="industry" required>
                <option value="">— Seleziona settore —</option>
                <?php foreach ($industries as $ind):
                    $sel = ($data['industry'] ?? '') === $ind ? 'selected' : '';
                ?>
                <option value="<?= $ind ?>" <?= $sel ?>><?= ucfirst(str_replace('_', ' ', $ind)) ?></option>
                <?php endforeach; ?>
            </select>
        </div>

        <div class="form-group">
            <label for="products">Prodotti / Servizi (uno per riga)</label>
            <textarea id="products" name="products" rows="4"
                      placeholder="ERP Cloud Platform&#10;Mobile Banking App&#10;Threat Detection Suite"><?= htmlspecialchars($data['products'] ?? '') ?></textarea>
        </div>

        <div class="form-group">
            <label for="competitors">Competitor noti (uno per riga)</label>
            <textarea id="competitors" name="competitors" rows="4"
                      placeholder="CompetitorA Inc&#10;RivalTech GmbH"><?= htmlspecialchars($data['competitors'] ?? '') ?></textarea>
            <span class="form-hint">Nomi di competitor diretti — verranno monitorati automaticamente</span>
        </div>

        <div class="step-actions">
            <a href="?step=4" class="btn btn-ghost">← Indietro</a>
            <button type="submit" class="btn btn-primary">Avanti →</button>
        </div>
    </form>
</div>
<?php render_footer(); ?>
