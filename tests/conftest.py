"""
MMON — pytest configuration.
Imposta l'env var per usare settings default (senza mmon.conf).
"""

import os

# Forza config vuota per test (usa Settings default)
os.environ["MMON_CONFIG"] = "/dev/null"
