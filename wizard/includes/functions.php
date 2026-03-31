<?php
/**
 * MMON Setup Wizard — Funzioni condivise
 */

define('MMON_BASE', '/opt/mmon');
define('MMON_CONFIG_PATH', MMON_BASE . '/config/mmon.conf');
define('MMON_LOCK_FILE', MMON_BASE . '/config/.wizard_completed');
define('TOTAL_STEPS', 7);

/**
 * Inizializza la sessione del wizard.
 */
function wizard_init(): void
{
    if (session_status() === PHP_SESSION_NONE) {
        session_start();
    }
    if (!isset($_SESSION['wizard_data'])) {
        $_SESSION['wizard_data'] = [];
    }
}

/**
 * Controlla se il wizard è già stato completato (lock file).
 * Restituisce true se il wizard è bloccato.
 */
function wizard_is_locked(): bool
{
    return file_exists(MMON_LOCK_FILE);
}

/**
 * Salva i dati di uno step nella sessione.
 *
 * @param int   $step  Numero dello step
 * @param array $data  Dati validati dello step
 */
function wizard_save_step(int $step, array $data): void
{
    $_SESSION['wizard_data']["step_{$step}"] = $data;
    $_SESSION['wizard_data']['last_completed_step'] = $step;
}

/**
 * Recupera i dati di uno step dalla sessione.
 *
 * @param int $step Numero dello step
 * @return array Dati dello step (vuoto se non compilato)
 */
function wizard_get_step(int $step): array
{
    return $_SESSION['wizard_data']["step_{$step}"] ?? [];
}

/**
 * Restituisce l'ultimo step completato.
 */
function wizard_last_step(): int
{
    return $_SESSION['wizard_data']['last_completed_step'] ?? 0;
}

/**
 * Valida un campo come non vuoto.
 *
 * @param string $value Valore da validare
 * @param string $name  Nome campo per messaggio di errore
 * @return string|null  Messaggio di errore o null se valido
 */
function validate_required(string $value, string $name): ?string
{
    $value = trim($value);
    if ($value === '') {
        return "{$name} è obbligatorio.";
    }
    return null;
}

/**
 * Valida un indirizzo IP (v4 o v6).
 */
function validate_ip(string $ip): bool
{
    return filter_var(trim($ip), FILTER_VALIDATE_IP) !== false;
}

/**
 * Valida un dominio.
 */
function validate_domain(string $domain): bool
{
    $domain = trim($domain);
    return (bool) preg_match('/^([a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$/', $domain);
}

/**
 * Valida un indirizzo email.
 */
function validate_email(string $email): bool
{
    return filter_var(trim($email), FILTER_VALIDATE_EMAIL) !== false;
}

/**
 * Sanitizza input stringa.
 */
function sanitize(string $input): string
{
    return htmlspecialchars(trim($input), ENT_QUOTES, 'UTF-8');
}

/**
 * Sanitizza un array di stringhe separate da virgola o newline.
 * Restituisce array pulito.
 */
function sanitize_list(string $input): array
{
    $items = preg_split('/[,\n\r]+/', $input);
    $result = [];
    foreach ($items as $item) {
        $item = trim($item);
        if ($item !== '') {
            $result[] = sanitize($item);
        }
    }
    return $result;
}

/**
 * Genera la configurazione mmon.conf dai dati wizard.
 *
 * @param array $data Tutti i dati wizard raccolti
 * @return string Contenuto del file mmon.conf
 */
function generate_config(array $data): string
{
    $s1 = $data['step_1'] ?? [];
    $s2 = $data['step_2'] ?? [];
    $s3 = $data['step_3'] ?? [];
    $s4 = $data['step_4'] ?? [];
    $s5 = $data['step_5'] ?? [];
    $s6 = $data['step_6'] ?? [];
    $s7 = $data['step_7'] ?? [];

    $jwt_secret = bin2hex(random_bytes(32));
    $db_password = file_exists(MMON_BASE . '/config/.db_password')
        ? trim(file_get_contents(MMON_BASE . '/config/.db_password'))
        : bin2hex(random_bytes(16));

    $domains = implode(',', $s2['domains'] ?? []);
    $ips = implode(',', $s2['public_ips'] ?? []);
    $emails = implode(',', $s2['emails'] ?? []);
    $usernames = implode(',', $s3['usernames'] ?? []);
    $full_names = implode(',', $s3['full_names'] ?? []);
    $technologies = implode(',', $s4['technologies'] ?? []);
    $products = implode(',', $s5['products'] ?? []);

    $conf = <<<CONF
; MMON Configuration File
; Generato dal Setup Wizard — {$_SERVER['SERVER_ADDR']} — {date('Y-m-d H:i:s')}
; NON committare questo file nel repository.

[general]
mode = {$s1['mode']}

[target]
company_name = {$s2['company_name']}
domains = {$domains}
public_ips = {$ips}
emails = {$emails}

[social]
usernames = {$usernames}
full_names = {$full_names}

[technologies]
stack = {$technologies}

[sector]
industry = {$s5['industry']}
products = {$products}

[api_keys]
shodan_key = {$s6['shodan_key']}
criminal_ip_key = {$s6['criminal_ip_key']}
quake360_key = {$s6['quake360_key']}

[infrastructure]
backend_ip = {$s7['backend_ip']}
vm1_ip = {$s7['vm1_ip']}
vm2_ip = {$s7['vm2_ip']}
vm3_ip = {$s7['vm3_ip']}

[database]
host = 127.0.0.1
port = 5432
name = mmon
user = mmon
password = {$db_password}

[redis]
host = 127.0.0.1
port = 6379

[tor]
socks_port = {$s7['tor_socks_port']}
control_port = {$s7['tor_control_port']}
control_password = {$s7['tor_control_password']}

[telegram]
api_id = {$s7['tg_api_id']}
api_hash = {$s7['tg_api_hash']}
phone = {$s7['tg_phone']}

[scheduler]
scan_interval_hours = 24
max_concurrent_tools = 3

[jwt]
secret_key = {$jwt_secret}
algorithm = HS256
access_token_expire_minutes = 60

[ollama]
base_url = http://127.0.0.1:11434
model = qwen2.5:14b
CONF;

    return $conf;
}

/**
 * Scrive il file mmon.conf e crea il lock file.
 *
 * @param string $config_content Contenuto config
 * @return bool True se scritto correttamente
 */
function write_config(string $config_content): bool
{
    $config_dir = MMON_BASE . '/config';

    if (!is_dir($config_dir)) {
        @mkdir($config_dir, 0700, true);
    }

    $written = @file_put_contents(MMON_CONFIG_PATH, $config_content);
    if ($written === false) {
        return false;
    }

    @chmod(MMON_CONFIG_PATH, 0600);

    // Lock file per impedire ri-esecuzione
    @file_put_contents(MMON_LOCK_FILE, date('Y-m-d H:i:s'));

    return true;
}

/**
 * Inizializza i target nel database PostgreSQL.
 *
 * @param array $data Dati wizard
 * @return bool True se inserimento riuscito
 */
function init_db_targets(array $data): bool
{
    $db_password = file_exists(MMON_BASE . '/config/.db_password')
        ? trim(file_get_contents(MMON_BASE . '/config/.db_password'))
        : '';

    try {
        $dsn = "pgsql:host=127.0.0.1;port=5432;dbname=mmon";
        $pdo = new PDO($dsn, 'mmon', $db_password, [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        ]);

        $s2 = $data['step_2'] ?? [];
        $s3 = $data['step_3'] ?? [];
        $s4 = $data['step_4'] ?? [];
        $s5 = $data['step_5'] ?? [];

        $stmt = $pdo->prepare("
            INSERT INTO targets (company_name, domains, public_ips, emails, usernames, full_names, technologies, industry, products)
            VALUES (:company, :domains, :ips, :emails, :usernames, :names, :tech, :industry, :products)
        ");

        $stmt->execute([
            ':company'   => $s2['company_name'] ?? '',
            ':domains'   => '{' . implode(',', array_map(fn($d) => '"' . $d . '"', $s2['domains'] ?? [])) . '}',
            ':ips'       => '{' . implode(',', array_map(fn($d) => '"' . $d . '"', $s2['public_ips'] ?? [])) . '}',
            ':emails'    => '{' . implode(',', array_map(fn($d) => '"' . $d . '"', $s2['emails'] ?? [])) . '}',
            ':usernames' => '{' . implode(',', array_map(fn($d) => '"' . $d . '"', $s3['usernames'] ?? [])) . '}',
            ':names'     => '{' . implode(',', array_map(fn($d) => '"' . $d . '"', $s3['full_names'] ?? [])) . '}',
            ':tech'      => '{' . implode(',', array_map(fn($d) => '"' . $d . '"', $s4['technologies'] ?? [])) . '}',
            ':industry'  => $s5['industry'] ?? '',
            ':products'  => '{' . implode(',', array_map(fn($d) => '"' . $d . '"', $s5['products'] ?? [])) . '}',
        ]);

        // Aggiornare config.wizard_completed
        $pdo->exec("UPDATE config SET wizard_completed = TRUE WHERE config_id = (SELECT config_id FROM config LIMIT 1)");

        return true;
    } catch (PDOException $e) {
        error_log("MMON Wizard DB Error: " . $e->getMessage());
        return false;
    }
}

/**
 * Renderizza l'header HTML del wizard.
 */
function render_header(int $current_step): void
{
    $step_labels = [
        1 => 'Mode',
        2 => 'Target',
        3 => 'Social',
        4 => 'Tech',
        5 => 'Sector',
        6 => 'API',
        7 => 'Infra',
    ];

    echo '<!DOCTYPE html>';
    echo '<html lang="it">';
    echo '<head>';
    echo '<meta charset="UTF-8">';
    echo '<meta name="viewport" content="width=device-width, initial-scale=1.0">';
    echo '<title>MMON — Setup Wizard</title>';
    echo '<link rel="preconnect" href="https://fonts.googleapis.com">';
    echo '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">';
    echo '<link rel="stylesheet" href="/assets/style.css">';
    echo '</head>';
    echo '<body>';

    echo '<div class="wizard-header">';
    echo '<h1>MMON</h1>';
    echo '<div class="subtitle">Morpheus MONitoring — Setup Wizard</div>';
    echo '</div>';

    echo '<div class="progress-container">';
    echo '<div class="progress-steps">';
    foreach ($step_labels as $num => $label) {
        $class = '';
        if ($num < $current_step) $class = 'done';
        elseif ($num === $current_step) $class = 'active';
        echo "<div class=\"progress-step {$class}\">";
        echo "<div class=\"step-dot\">{$num}</div>";
        echo "<div class=\"step-label\">{$label}</div>";
        echo '</div>';
    }
    echo '</div>';
    echo '</div>';
}

/**
 * Renderizza il footer HTML.
 */
function render_footer(): void
{
    echo '</body></html>';
}
