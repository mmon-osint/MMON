<?php
/**
 * Step 4 — Tecnologie utilizzate (per CVE feed + Infrastructure)
 */

require_once __DIR__ . '/../includes/functions.php';
wizard_init();

$errors = [];
$saved = wizard_get_step(4);

// Lista tecnologie comuni con categorie
$tech_options = [
    'Web Server'   => ['nginx', 'apache', 'iis', 'caddy', 'traefik'],
    'Database'     => ['postgresql', 'mysql', 'mariadb', 'mongodb', 'redis', 'elasticsearch', 'mssql', 'oracle'],
    'Language'     => ['python', 'php', 'java', 'nodejs', 'golang', 'ruby', 'dotnet', 'rust'],
    'CMS/Platform' => ['wordpress', 'drupal', 'joomla', 'magento', 'shopify', 'confluence', 'sharepoint'],
    'Cloud/Infra'  => ['aws', 'azure', 'gcp', 'docker', 'kubernetes', 'vmware', 'proxmox', 'terraform'],
    'Security'     => ['fortinet', 'paloalto', 'cisco-asa', 'sophos', 'crowdstrike', 'wazuh'],
    'Mail'         => ['exchange', 'postfix', 'zimbra', 'google-workspace', 'microsoft-365'],
    'Network'      => ['cisco-ios', 'mikrotik', 'ubiquiti', 'juniper', 'openvpn', 'wireguard'],
];

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $selected = $_POST['technologies'] ?? [];
    $custom   = sanitize_list($_POST['custom_tech'] ?? '');

    // Validare che le tecnologie selezionate siano nella lista
    $all_valid = [];
    foreach ($tech_options as $options) {
        $all_valid = array_merge($all_valid, $options);
    }

    $technologies = [];
    foreach ($selected as $tech) {
        $tech = sanitize($tech);
        if (in_array($tech, $all_valid)) {
            $technologies[] = $tech;
        }
    }

    // Aggiungere tecnologie custom
    $technologies = array_merge($technologies, $custom);
    $technologies = array_unique($technologies);

    if (empty($technologies)) {
        $errors[] = 'Seleziona almeno una tecnologia per il feed CVE.';
    }

    if (empty($errors)) {
        wizard_save_step(4, ['technologies' => $technologies]);
        header('Location: /index.php?step=5');
        exit;
    }
}

$saved_tech = $saved['technologies'] ?? [];

render_header(4);
?>

<div class="wizard-card">
    <div class="card-inner">
        <h2>Stack Tecnologico</h2>
        <p class="step-description">
            Seleziona le tecnologie in uso nell'organizzazione. Il widget CVE Feed monitorerà
            le vulnerabilità note per queste tecnologie.
        </p>

        <?php if (!empty($errors)): ?>
            <div class="alert alert-error">
                <?php foreach ($errors as $err): ?>
                    <div><?= $err ?></div>
                <?php endforeach; ?>
            </div>
        <?php endif; ?>

        <form method="POST" action="/index.php?step=4">
            <?php foreach ($tech_options as $category => $options): ?>
                <div class="form-group">
                    <label><?= $category ?></label>
                    <div class="checkbox-grid">
                        <?php foreach ($options as $tech): ?>
                            <div class="checkbox-item">
                                <input type="checkbox" name="technologies[]" value="<?= $tech ?>"
                                    id="tech_<?= $tech ?>"
                                    <?= in_array($tech, $saved_tech) ? 'checked' : '' ?>>
                                <label for="tech_<?= $tech ?>"><?= $tech ?></label>
                            </div>
                        <?php endforeach; ?>
                    </div>
                </div>
            <?php endforeach; ?>

            <div class="form-group">
                <label>Tecnologie aggiuntive</label>
                <textarea name="custom_tech" placeholder="custom-app-v2.1&#10;internal-tool&#10;legacy-system"
                    rows="2"><?= sanitize($_POST['custom_tech'] ?? '') ?></textarea>
                <div class="hint">Opzionale. Aggiungi tecnologie non presenti nella lista sopra, una per riga.</div>
            </div>

            <div class="btn-row">
                <a href="/index.php?step=3" class="btn btn-secondary">&#8592; Indietro</a>
                <button type="submit" class="btn btn-primary">Avanti &#8594;</button>
            </div>
        </form>
    </div>
</div>

<?php render_footer(); ?>
