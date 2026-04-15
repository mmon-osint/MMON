<?php
/**
 * Step 3 — Social: username e nominativi da monitorare
 */
require_once __DIR__ . '/../includes/functions.php';
$data = wizard_get_step(3);
render_header(3);
?>
<div class="step-content">
    <h2>Social Footprint</h2>
    <p class="step-desc">Username e nominativi da monitorare su piattaforme social e motori di ricerca.</p>

    <form method="POST" action="?step=3">
        <div class="form-group">
            <label for="usernames">Username (uno per riga)</label>
            <textarea id="usernames" name="usernames" rows="5"
                      placeholder="johndoe&#10;jane_doe&#10;acme_official"><?= htmlspecialchars($data['usernames'] ?? '') ?></textarea>
            <span class="form-hint">Username usati su social media, forum, repository</span>
        </div>

        <div class="form-group">
            <label for="full_names">Nomi completi (uno per riga)</label>
            <textarea id="full_names" name="full_names" rows="5"
                      placeholder="John Doe&#10;Jane Smith"><?= htmlspecialchars($data['full_names'] ?? '') ?></textarea>
            <span class="form-hint">Persone chiave dell'organizzazione (CEO, CTO, admin)</span>
        </div>

        <div class="step-actions">
            <a href="?step=2" class="btn btn-ghost">← Indietro</a>
            <button type="submit" class="btn btn-primary">Avanti →</button>
        </div>
    </form>
</div>
<?php render_footer(); ?>
