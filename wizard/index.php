<?php
/**
 * MMON Setup Wizard — Router principale
 * Gestisce il routing degli step e la navigazione.
 */

require_once __DIR__ . '/includes/functions.php';

wizard_init();

// Se il wizard è già stato completato, redirect alla dashboard
if (wizard_is_locked()) {
    header('Location: /');
    exit;
}

// Determinare lo step corrente
$step = isset($_GET['step']) ? (int) $_GET['step'] : 1;
$step = max(1, min($step, TOTAL_STEPS + 1)); // +1 per pagina riepilogo

// Mappatura step → file
$step_files = [
    1 => 'steps/step1_mode.php',
    2 => 'steps/step2_target.php',
    3 => 'steps/step3_social.php',
    4 => 'steps/step4_tech.php',
    5 => 'steps/step5_sector.php',
    6 => 'steps/step6_apikeys.php',
    7 => 'steps/step7_infra.php',
    8 => 'steps/complete.php',
];

if (!isset($step_files[$step])) {
    $step = 1;
}

require_once __DIR__ . '/' . $step_files[$step];
