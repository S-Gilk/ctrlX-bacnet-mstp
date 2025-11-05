#!/usr/bin/env bash
# Run make build in mstplib prior to snap build. This compiles .so for host architecture.
set -e
sudo snapcraft clean
sudo snapcraft --build-for=arm64 --verbosity=verbose