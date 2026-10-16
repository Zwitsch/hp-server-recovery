#!/usr/bin/env bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$ROOT"

printf '%s\n' 'HP Server Recovery - synthetic public demo'
printf '%s\n' 'No production backup or destructive restore is used.'

PYTHON="${PYTHON:-python3}"
"$PYTHON" -c 'import sys; assert sys.version_info >= (3, 12), "Python 3.12+ required"'

if ! "$PYTHON" -c 'import yaml' >/dev/null 2>&1; then
    printf '%s\n' 'Missing dependency: PyYAML'
    printf '%s\n' 'Install it in a virtual environment with: python -m pip install PyYAML'
    exit 2
fi

printf '%s\n' '[1/2] Compiling public Python sources...'
"$PYTHON" -m compileall -q lib tests

printf '%s\n' '[2/2] Running public synthetic recovery regression...'
PYTHONDONTWRITEBYTECODE=1 "$PYTHON" -m unittest \
    tests.test_t01_t35 \
    tests.test_wizard_v028 \
    tests.test_realtest_mode

printf '%s\n' 'DEMO_RESULT=PASS'
