#!/usr/bin/env bash
# Run make build in mstplib prior to snap build
set -e
sudo snapcraft clean
sudo snapcraft --build-for=amd64 --verbosity=verbose