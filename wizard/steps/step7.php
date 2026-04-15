<?php
/**
 * Step 7 — Infrastruttura: IP VM, Tor, Telegram, Keycloak
 */
require_once __DIR__ . '/../includes/functions.php';
$data = wizard_get_step(7);
$mode = wizard_get_step(1)['mode'] ?? 'personal';
render_header(7);
?>
<div class="step-content">
    <h2>Infrastruttura</h2>
    <p class="step-desc">Configurazione rete delle VM e servizi esterni.</p>

    <form method="POST" action="?step=7">
        <fieldset>
            <legend>IP delle VM</legend>
            <div class="form-row">
                <div class="form-group">
                    <label for="backend_ip">VM0 — Backend</label>
                    <input type="text" id="backend_ip" name="backend_ip"
                           value="<?= htmlspecialchars($data['backend_ip'] ?? '127.0.0.1') ?>"
                           placeholder="10.0.0.10" required>
                </div>
                <div class="form-group">
                    <label for="vm1_ip">VM1 — Clearnet</label>
                    <input type="text" id="vm1_ip" name="vm1_ip"
                           value="<?= htmlspecialchars($data['vm1_ip'] ?? '') ?>"
                           placeholder="10.0.0.11" required>
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label for="vm2_ip">VM2 — Deep Web</label>
                    <input type="text" id="vm2_ip" name="vm2_ip"
                           value="<?= htmlspecialchars($data['vm2_ip'] ?? '') ?>"
                           placeholder="10.0.0.12" required>
                </div>
                <div class="form-group">
                    <label for="vm3_ip">VM3 — Telegram</label>
                    <input type="text" id="vm3_ip" name="vm3_ip"
                           value="<?= htmlspecialchars($data['vm3_ip'] ?? '') ?>"
                           placeholder="10.0.0.13" required>
                </div>
            </div>
        </fieldset>

        <fieldset>
            <legend>Tor (VM2)</legend>
            <div class="form-row">
                <div class="form-group">
                    <label for="tor_socks_port">SOCKS Port</label>
                    <input type="number" id="tor_socks_port" name="tor_socks_port"
                           value="<?= htmlspecialchars($data['tor_socks_port'] ?? '9050') ?>">
                </div>
                <div class="form-group">
                    <label for="tor_control_port">Control Port</label>
                    <input type="number" id="tor_control_port" name="tor_control_port"
                           value="<?= htmlspecialchars($data['tor_control_port'] ?? '9051') ?>">
                </div>
            </div>
            <div class="form-group">
                <label for="tor_password">Control Password</label>
                <input type="password" id="tor_password" name="tor_password"
                       value="<?= htmlspecialchars($data['tor_password'] ?? '') ?>"
                       placeholder="Password per Tor ControlPort" autocomplete="off">
            </div>
        </fieldset>

        <fieldset>
            <legend>Telegram Puppet Account (VM3)</legend>
            <div class="form-row">
                <div class="form-group">
                    <label for="tg_api_id">API ID</label>
                    <input type="text" id="tg_api_id" name="tg_api_id"
                           value="<?= htmlspecialchars($data['tg_api_id'] ?? '') ?>"
                           placeholder="12345678">
                </div>
                <div class="form-group">
                    <label for="tg_api_hash">API Hash</label>
                    <input type="password" id="tg_api_hash" name="tg_api_hash"
                           value="<?= htmlspecialchars($data['tg_api_hash'] ?? '') ?>"
                           placeholder="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" autocomplete="off">
                </div>
            </div>
            <div class="form-group">
                <label for="tg_phone">Phone Number</label>
                <input type="text" id="tg_phone" name="tg_phone"
                       value="<?= htmlspecialchars($data['tg_phone'] ?? '') ?>"
                       placeholder="+39123456789">
            </div>
        </fieldset>

        <?php if ($mode === 'company'): ?>
        <fieldset>
            <legend>Keycloak (Company Mode)</legend>
            <div class="form-group">
                <label for="keycloak_url">Keycloak Server URL</label>
                <input type="url" id="keycloak_url" name="keycloak_url"
                       value="<?= htmlspecialchars($data['keycloak_url'] ?? '') ?>"
                       placeholder="https://keycloak.example.com" required>
            </div>
            <div class="form-group">
                <label for="keycloak_secret">Client Secret</label>
                <input type="password" id="keycloak_secret" name="keycloak_secret"
                       value="<?= htmlspecialchars($data['keycloak_secret'] ?? '') ?>"
                       placeholder="Client secret del realm MMON" autocomplete="off" required>
            </div>
        </fieldset>
        <?php endif; ?>

        <div class="step-actions">
            <a href="?step=6" class="btn btn-ghost">← Indietro</a>
            <button type="submit" class="btn btn-primary">Avanti →</button>
        </div>
    </form>
</div>
<?php render_footer(); ?>
