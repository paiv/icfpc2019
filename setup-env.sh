#!/bin/bash
set -e

app="${1:-icfpc}"

python -m venv ".venv/$app"

. activate

pip install -U setuptools
pip install -U pip
pip install -r requirements.txt
