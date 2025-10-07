#!/usr/bin/env bash
python3 -m venv .venv
. .venv/bin/activate
pip install -U pip setuptools wheel

# install your provider package
pip install -e ./provider-source

# (optional) dev-only deps
pip install autopep8 isort

# build/install Misty (compiles the .so into your venv)
cd misty
# builds the C library and installs in editable mode
python -m pip install . 


