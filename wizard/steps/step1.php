<?php
/**
 * Step 1 — Modalità: Personal o Company
 */
require_once __DIR__ . '/../includes/functions.php';
$data = wizard_get_step(1);
render_header(1);
?>
<div class="step-content">
    <h2>Scegli la modalità</h2>
    <p class="step-desc">Definisce autenticazione e gestione utenti.</p>

    <form method="POST" action="?step=1">
        <div class="card-grid mode-grid">
            <label class="mode-card <?= ($data['mode'] ?? '') === 'personal' ? 'selected' : '' ?>">
                <input type="radio" name="mode" value="personal" <?= ($data['mode'] ?? 'personal') === 'personal' ? 'checked' : '' ?> required>
                <div class="mode-icon">👤</div>
                <div class="mode-title">Personal</div>
                <div class="mode-desc">Single user, autenticazione JWT locale. Ideale per ricercatori indipendenti e freelance.</div>
            </label>
            <label class="mode-card <?= ($data['mode'] ?? '') === 'company' ? 'selected' : '' ?>">
                <input type="radio" name="mode" value="company" <?= ($data['mode'] ?? '') === 'company' ? 'checked' : '' ?>>
                <div class="mode-icon">🏢</div>
                <div class="mode-title">Company</div>
                <div class="mode-desc">Multi-user con Keycloak — RBAC, SSO, LDAP. Per SOC team e security department.</div>
            </label>
        </div>
        <div class="step-actions">
            <button type="submit" class="btn btn-primary">Avanti →</button>
        </div>
    </form>
</div>
<?php render_footer(); ?>
