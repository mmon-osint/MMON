<?php
/**
 * Step 6 — API Keys (opzionali)
 */
require_once __DIR__ . '/../includes/functions.php';
$data = wizard_get_step(6);
render_header(6);
?>
<div class="step-content">
    <h2>API Keys</h2>
    <p class="step-desc">Chiavi API per tool di intelligence. Tutte opzionali — i tool funzionano anche senza, con risultati limitati.</p>

    <form method="POST" action="?step=6">
        <div class="form-group">
            <label for="shodan">Shodan API Key</label>
            <div class="input-with-action">
                <input type="password" id="shodan" name="shodan"
                       value="<?= htmlspecialchars($data['shodan'] ?? '') ?>"
                       placeholder="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                       autocomplete="off">
                <button type="button" class="btn btn-sm btn-ghost" onclick="testApiKey('shodan')">Test</button>
            </div>
            <span class="form-hint">Necessaria per scan infrastruttura e CVE feed avanzati</span>
        </div>

        <div class="form-group">
            <label for="criminal_ip">Criminal IP API Key</label>
            <div class="input-with-action">
                <input type="password" id="criminal_ip" name="criminal_ip"
                       value="<?= htmlspecialchars($data['criminal_ip'] ?? '') ?>"
                       placeholder="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                       autocomplete="off">
                <button type="button" class="btn btn-sm btn-ghost" onclick="testApiKey('criminal_ip')">Test</button>
            </div>
        </div>

        <div class="form-group">
            <label for="quake360">Quake360 API Key</label>
            <div class="input-with-action">
                <input type="password" id="quake360" name="quake360"
                       value="<?= htmlspecialchars($data['quake360'] ?? '') ?>"
                       placeholder="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                       autocomplete="off">
                <button type="button" class="btn btn-sm btn-ghost" onclick="testApiKey('quake360')">Test</button>
            </div>
        </div>

        <div class="step-actions">
            <a href="?step=5" class="btn btn-ghost">← Indietro</a>
            <button type="submit" class="btn btn-primary">Avanti →</button>
        </div>
    </form>
</div>

<div id="test-result" class="test-toast" style="display:none;"></div>

<script>
async function testApiKey(provider) {
    const key = document.getElementById(provider).value;
    if (!key) { showToast('Inserisci una API key prima di testare', 'warn'); return; }

    const toast = document.getElementById('test-result');
    showToast('Testing ' + provider + '...', 'info');

    try {
        const resp = await fetch('/api/v1/test-apikey', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ provider, key })
        });
        const data = await resp.json();
        showToast(data.valid ? provider + ': ✓ Key valida' : provider + ': ✗ Key non valida',
                  data.valid ? 'ok' : 'error');
    } catch (e) {
        showToast('Errore di connessione al backend', 'error');
    }
}

function showToast(msg, type) {
    const t = document.getElementById('test-result');
    t.textContent = msg;
    t.className = 'test-toast toast-' + type;
    t.style.display = 'block';
    setTimeout(() => t.style.display = 'none', 4000);
}
</script>
<?php render_footer(); ?>
