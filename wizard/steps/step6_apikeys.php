<?php
/**
 * Step 6 — API keys opzionali (Shodan, Criminal IP, Quake360)
 */

require_once __DIR__ . '/../includes/functions.php';
wizard_init();

$errors = [];
$saved = wizard_get_step(6);

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $shodan_key      = sanitize($_POST['shodan_key'] ?? '');
    $criminal_ip_key = sanitize($_POST['criminal_ip_key'] ?? '');
    $quake360_key    = sanitize($_POST['quake360_key'] ?? '');

    // Le API key sono tutte opzionali — nessuna validazione obbligatoria
    wizard_save_step(6, [
        'shodan_key'      => $shodan_key,
        'criminal_ip_key' => $criminal_ip_key,
        'quake360_key'    => $quake360_key,
    ]);
    header('Location: /index.php?step=7');
    exit;
}

render_header(6);
?>

<div class="wizard-card">
    <div class="card-inner">
        <h2>API Keys</h2>
        <p class="step-description">
            Configura le API key per i servizi di intelligence esterni. Tutte le chiavi sono opzionali
            ma migliorano significativamente i risultati dei widget Infrastructure e CVE Feed.
        </p>

        <form method="POST" action="/index.php?step=6">
            <div class="form-group">
                <label>Shodan API Key</label>
                <div class="api-key-row">
                    <input type="password" name="shodan_key" id="shodan_key"
                        value="<?= sanitize($saved['shodan_key'] ?? '') ?>"
                        placeholder="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                        autocomplete="off">
                    <button type="button" class="btn-test" onclick="testApiKey('shodan')">Test</button>
                </div>
                <div class="hint">Necessaria per il widget Infrastructure Exposure. <a href="https://account.shodan.io" target="_blank" style="color: var(--accent);">Ottieni key</a></div>
                <div id="shodan_result" class="test-result"></div>
            </div>

            <div class="form-group">
                <label>Criminal IP API Key</label>
                <div class="api-key-row">
                    <input type="password" name="criminal_ip_key" id="criminal_ip_key"
                        value="<?= sanitize($saved['criminal_ip_key'] ?? '') ?>"
                        placeholder="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                        autocomplete="off">
                    <button type="button" class="btn-test" onclick="testApiKey('criminal_ip')">Test</button>
                </div>
                <div class="hint">Opzionale. Aggiunge dati di threat intelligence sugli IP. <a href="https://www.criminalip.io" target="_blank" style="color: var(--accent);">Ottieni key</a></div>
                <div id="criminal_ip_result" class="test-result"></div>
            </div>

            <div class="form-group">
                <label>Quake360 API Key</label>
                <div class="api-key-row">
                    <input type="password" name="quake360_key" id="quake360_key"
                        value="<?= sanitize($saved['quake360_key'] ?? '') ?>"
                        placeholder="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                        autocomplete="off">
                    <button type="button" class="btn-test" onclick="testApiKey('quake360')">Test</button>
                </div>
                <div class="hint">Opzionale. Motore di ricerca alternativo per asset esposti. <a href="https://quake.360.net" target="_blank" style="color: var(--accent);">Ottieni key</a></div>
                <div id="quake360_result" class="test-result"></div>
            </div>

            <div class="alert alert-info">
                Le API key vengono salvate in <code>mmon.conf</code> con permessi restrittivi (600).
                Non vengono mai trasmesse a servizi esterni diversi dal provider della key stessa.
            </div>

            <div class="btn-row">
                <a href="/index.php?step=5" class="btn btn-secondary">&#8592; Indietro</a>
                <button type="submit" class="btn btn-primary">Avanti &#8594;</button>
            </div>
        </form>
    </div>
</div>

<script>
function testApiKey(provider) {
    const input = document.getElementById(provider + '_key');
    const result = document.getElementById(provider + '_result');
    const key = input.value.trim();

    if (!key) {
        result.className = 'test-result error';
        result.textContent = 'Inserisci una API key prima di testare.';
        return;
    }

    result.className = 'test-result';
    result.textContent = 'Testing...';

    // Test connessione verso il backend (che fa da proxy)
    // In assenza di backend attivo, mostriamo un messaggio informativo
    fetch('/api/v1/test-apikey', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider: provider, key: key })
    })
    .then(r => r.json())
    .then(data => {
        if (data.valid) {
            result.className = 'test-result success';
            result.textContent = 'Key valida. Credits: ' + (data.credits || 'N/A');
        } else {
            result.className = 'test-result error';
            result.textContent = 'Key non valida: ' + (data.error || 'errore sconosciuto');
        }
    })
    .catch(() => {
        result.className = 'test-result error';
        result.textContent = 'Backend non raggiungibile. Il test sarà disponibile dopo il setup.';
    });
}
</script>

<?php render_footer(); ?>
