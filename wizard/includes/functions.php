<?php
/**
 * MMON Setup Wizard — Shared Functions
 */

define('MMON_BASE', '/opt/mmon');
define('MMON_CONF', MMON_BASE . '/config/mmon.conf');
define('MMON_LOCK', MMON_BASE . '/config/.wizard_lock');

/**
 * Inizializza sessione wizard.
 */
function wizard_init(): void {
    if (session_status() === PHP_SESSION_NONE) {
        session_start();
    }
    if (!isset($_SESSION['wizard'])) {
        $_SESSION['wizard'] = [];
    }
}

/**
 * Controlla se wizard è già stato completato.
 */
function wizard_is_locked(): bool {
    return file_exists(MMON_LOCK);
}

/**
 * Salva dati di uno step nella sessione.
 */
function wizard_save_step(int $step, array $data): void {
    $_SESSION['wizard']["step{$step}"] = $data;
}

/**
 * Recupera dati di uno step dalla sessione.
 */
function wizard_get_step(int $step): array {
    return $_SESSION['wizard']["step{$step}"] ?? [];
}

/**
 * Sanitizza lista separata da newline → array pulito.
 */
function sanitize_list(string $input, string $separator = "\n"): array {
    $items = explode($separator, $input);
    return array_values(array_filter(array_map('trim', $items), fn($v) => $v !== ''));
}

/**
 * Validazione dominio.
 */
function validate_domain(string $domain): bool {
    return (bool)preg_match('/^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z]{2,})+$/', trim($domain));
}

/**
 * Validazione IP v4.
 */
function validate_ip(string $ip): bool {
    return filter_var(trim($ip), FILTER_VALIDATE_IP, FILTER_FLAG_IPV4) !== false;
}

/**
 * Validazione email.
 */
function validate_email(string $email): bool {
    return filter_var(trim($email), FILTER_VALIDATE_EMAIL) !== false;
}

/**
 * Genera file mmon.conf INI dai dati wizard in sessione.
 */
function generate_config(): string {
    $w = $_SESSION['wizard'];
    $s1 = $w['step1'] ?? [];
    $s2 = $w['step2'] ?? [];
    $s3 = $w['step3'] ?? [];
    $s4 = $w['step4'] ?? [];
    $s5 = $w['step5'] ?? [];
    $s6 = $w['step6'] ?? [];
    $s7 = $w['step7'] ?? [];

    $jwt_secret = bin2hex(random_bytes(32));

    $conf = "; MMON Configuration — generato dal Setup Wizard\n";
    $conf .= "; " . date('Y-m-d H:i:s') . "\n\n";

    // [general]
    $mode = $s1['mode'] ?? 'personal';
    $conf .= "[general]\n";
    $conf .= "deploy_mode = {$mode}\n";
    $conf .= "instance_name = MMON\n";
    $conf .= "version = 1.0.0\n\n";

    // [target]
    $conf .= "[target]\n";
    $conf .= "company_name = " . ($s2['company_name'] ?? '') . "\n";
    $conf .= "domains = " . ($s2['domains'] ?? '') . "\n";
    $conf .= "public_ips = " . ($s2['public_ips'] ?? '') . "\n";
    $conf .= "emails = " . ($s2['emails'] ?? '') . "\n\n";

    // [social]
    $usernames = implode(',', sanitize_list($s3['usernames'] ?? ''));
    $fullnames = implode(',', sanitize_list($s3['full_names'] ?? ''));
    $conf .= "[social]\n";
    $conf .= "usernames = {$usernames}\n";
    $conf .= "full_names = {$fullnames}\n\n";

    // [technologies]
    $conf .= "[technologies]\n";
    $tech_fields = ['web_server', 'database', 'language', 'cms', 'cloud', 'security', 'mail', 'network'];
    foreach ($tech_fields as $f) {
        $val = $s4[$f] ?? '';
        if (is_array($val)) $val = implode(',', $val);
        $conf .= "{$f} = {$val}\n";
    }
    if (!empty($s4['custom_tech'])) {
        $conf .= "custom = " . $s4['custom_tech'] . "\n";
    }
    $conf .= "\n";

    // [sector]
    $conf .= "[sector]\n";
    $conf .= "industry = " . ($s5['industry'] ?? '') . "\n";
    $conf .= "products = " . ($s5['products'] ?? '') . "\n";
    $conf .= "competitors = " . ($s5['competitors'] ?? '') . "\n\n";

    // [api_keys]
    $conf .= "[api_keys]\n";
    $conf .= "shodan = " . ($s6['shodan'] ?? '') . "\n";
    $conf .= "criminal_ip = " . ($s6['criminal_ip'] ?? '') . "\n";
    $conf .= "quake360 = " . ($s6['quake360'] ?? '') . "\n\n";

    // [infrastructure]
    $conf .= "[infrastructure]\n";
    $conf .= "backend_ip = " . ($s7['backend_ip'] ?? '127.0.0.1') . "\n";
    $conf .= "vm1_ip = " . ($s7['vm1_ip'] ?? '') . "\n";
    $conf .= "vm2_ip = " . ($s7['vm2_ip'] ?? '') . "\n";
    $conf .= "vm3_ip = " . ($s7['vm3_ip'] ?? '') . "\n\n";

    // [database]
    $db_pass = '';
    $pass_file = MMON_BASE . '/config/.db_password';
    if (file_exists($pass_file)) {
        $db_pass = trim(file_get_contents($pass_file));
    }
    $conf .= "[database]\n";
    $conf .= "host = 127.0.0.1\nport = 5432\nname = mmon_db\nuser = mmon\n";
    $conf .= "password = {$db_pass}\n\n";

    // [redis]
    $conf .= "[redis]\nhost = 127.0.0.1\nport = 6379\ndb = 0\n\n";

    // [tor]
    $conf .= "[tor]\n";
    $conf .= "socks_port = " . ($s7['tor_socks_port'] ?? '9050') . "\n";
    $conf .= "control_port = " . ($s7['tor_control_port'] ?? '9051') . "\n";
    $conf .= "control_password = " . ($s7['tor_password'] ?? '') . "\n\n";

    // [telegram]
    $conf .= "[telegram]\n";
    $conf .= "api_id = " . ($s7['tg_api_id'] ?? '') . "\n";
    $conf .= "api_hash = " . ($s7['tg_api_hash'] ?? '') . "\n";
    $conf .= "phone = " . ($s7['tg_phone'] ?? '') . "\n\n";

    // [scheduler]
    $conf .= "[scheduler]\nscan_interval_hours = 24\nmax_concurrent_tools = 3\n\n";

    // [jwt]
    $conf .= "[jwt]\nsecret_key = {$jwt_secret}\nalgorithm = HS256\nexpire_minutes = 1440\n\n";

    // [keycloak]
    $kc_enabled = ($mode === 'company') ? 'true' : 'false';
    $conf .= "[keycloak]\n";
    $conf .= "enabled = {$kc_enabled}\n";
    $conf .= "server_url = " . ($s7['keycloak_url'] ?? '') . "\n";
    $conf .= "realm = mmon\n";
    $conf .= "client_id = mmon-dashboard\n";
    $conf .= "client_secret = " . ($s7['keycloak_secret'] ?? '') . "\n\n";

    // [ollama]
    $conf .= "[ollama]\nbase_url = http://127.0.0.1:11434\nmodel = qwen2.5:14b\ntimeout = 120\n";

    return $conf;
}

/**
 * Scrive config e lock file.
 */
function write_config(): bool {
    $conf = generate_config();
    $dir = dirname(MMON_CONF);
    if (!is_dir($dir)) {
        mkdir($dir, 0750, true);
    }
    $ok = file_put_contents(MMON_CONF, $conf);
    if ($ok !== false) {
        chmod(MMON_CONF, 0640);
        file_put_contents(MMON_LOCK, date('Y-m-d H:i:s'));
        return true;
    }
    return false;
}

/**
 * Inizializza target nel DB da dati wizard.
 */
function init_db_targets(): bool {
    $w = $_SESSION['wizard'];
    $s2 = $w['step2'] ?? [];
    $s3 = $w['step3'] ?? [];

    // Leggi password DB
    $db_pass = '';
    $pass_file = MMON_BASE . '/config/.db_password';
    if (file_exists($pass_file)) {
        $db_pass = trim(file_get_contents($pass_file));
    }

    try {
        $dsn = "pgsql:host=127.0.0.1;port=5432;dbname=mmon_db";
        $pdo = new PDO($dsn, 'mmon', $db_pass, [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION
        ]);

        $stmt = $pdo->prepare("INSERT INTO targets (name, target_type, value) VALUES (?, ?, ?) ON CONFLICT DO NOTHING");

        // Domini
        foreach (sanitize_list($s2['domains'] ?? '', ',') as $d) {
            if (validate_domain($d)) $stmt->execute([$d, 'domain', $d]);
        }
        // IP
        foreach (sanitize_list($s2['public_ips'] ?? '', ',') as $ip) {
            if (validate_ip($ip)) $stmt->execute([$ip, 'ip', $ip]);
        }
        // Email
        foreach (sanitize_list($s2['emails'] ?? '', ',') as $e) {
            if (validate_email($e)) $stmt->execute([$e, 'email', $e]);
        }
        // Username
        foreach (sanitize_list($s3['usernames'] ?? '') as $u) {
            $stmt->execute([$u, 'username', $u]);
        }
        // Full names
        foreach (sanitize_list($s3['full_names'] ?? '') as $n) {
            $stmt->execute([$n, 'fullname', $n]);
        }
        // Company
        if (!empty($s2['company_name'])) {
            $stmt->execute([$s2['company_name'], 'company', $s2['company_name']]);
        }

        return true;
    } catch (PDOException $e) {
        error_log("MMON Wizard DB Error: " . $e->getMessage());
        return false;
    }
}

/**
 * Render header HTML con progress bar.
 */
function render_header(int $current_step, int $total_steps = 8): void {
    $steps = [
        1 => 'Modalità',
        2 => 'Target',
        3 => 'Social',
        4 => 'Tecnologie',
        5 => 'Settore',
        6 => 'API Keys',
        7 => 'Infrastruttura',
        8 => 'Conferma',
    ];
    ?>
    <!DOCTYPE html>
    <html lang="it">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>MMON Setup — Step <?= $current_step ?>/<?= $total_steps ?></title>
        <link rel="stylesheet" href="assets/style.css">
    </head>
    <body>
    <div class="wizard-container">
        <div class="wizard-brand">
            <span class="brand-icon">◉</span> MMON <span class="brand-sub">Setup Wizard</span>
        </div>
        <div class="progress-bar">
            <?php foreach ($steps as $num => $label): ?>
                <div class="progress-step <?= $num < $current_step ? 'done' : ($num === $current_step ? 'active' : '') ?>">
                    <div class="step-num"><?= $num ?></div>
                    <div class="step-label"><?= $label ?></div>
                </div>
            <?php endforeach; ?>
        </div>
    <?php
}

/**
 * Render footer HTML.
 */
function render_footer(): void {
    ?>
    </div><!-- .wizard-container -->
    </body>
    </html>
    <?php
}
