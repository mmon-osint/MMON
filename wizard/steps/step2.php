<?php
/**
 * Step 2 — Target: azienda, domini, IP, email
 */
require_once __DIR__ . '/../includes/functions.php';
$data = wizard_get_step(2);
render_header(2);
?>
<div class="step-content">
    <h2>Dati Target</h2>
    <p class="step-desc">Informazioni sull'organizzazione da monitorare.</p>

    <form method="POST" action="?step=2">
        <div class="form-group">
            <label for="company_name">Nome Azienda / Organizzazione</label>
            <input type="text" id="company_name" name="company_name"
                   value="<?= htmlspecialchars($data['company_name'] ?? '') ?>"
                   placeholder="Acme Corp" required>
        </div>

        <div class="form-group">
            <label for="domains">Domini (separati da virgola)</label>
            <input type="text" id="domains" name="domains"
                   value="<?= htmlspecialchars($data['domains'] ?? '') ?>"
                   placeholder="example.com, sub.example.com">
            <span class="form-hint">Domini web dell'organizzazione</span>
        </div>

        <div class="form-group">
            <label for="public_ips">IP Pubblici (separati da virgola)</label>
            <input type="text" id="public_ips" name="public_ips"
                   value="<?= htmlspecialchars($data['public_ips'] ?? '') ?>"
                   placeholder="1.2.3.4, 5.6.7.8">
        </div>

        <div class="form-group">
            <label for="emails">Email Aziendali (separate da virgola)</label>
            <input type="text" id="emails" name="emails"
                   value="<?= htmlspecialchars($data['emails'] ?? '') ?>"
                   placeholder="admin@example.com, ceo@example.com">
        </div>

        <div class="step-actions">
            <a href="?step=1" class="btn btn-ghost">← Indietro</a>
            <button type="submit" class="btn btn-primary">Avanti →</button>
        </div>
    </form>
</div>
<?php render_footer(); ?>
