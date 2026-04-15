<?php
/**
 * MMON Setup Wizard — Router
 * Gestisce navigazione multi-step. Se wizard è locked, redirect a dashboard.
 */

require_once __DIR__ . '/includes/functions.php';
wizard_init();

// Se wizard completato, redirect
if (wizard_is_locked()) {
    header('Location: /');
    exit;
}

// Step corrente
$step = isset($_GET['step']) ? (int)$_GET['step'] : 1;
$step = max(1, min(8, $step));

// Gestione POST — salva dati e avanza
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    wizard_save_step($step, $_POST);
    if ($step < 8) {
        header("Location: ?step=" . ($step + 1));
        exit;
    }
}

// Render step
$step_file = __DIR__ . "/steps/step{$step}.php";
if (!file_exists($step_file)) {
    die("Step non trovato: {$step}");
}

include $step_file;
