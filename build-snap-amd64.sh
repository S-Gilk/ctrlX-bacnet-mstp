#!/usr/bin/env bash
# Run make build in mstplib prior to snap build. This compiles .so for host architecture.
set -e
sudo snapcraft clean provider
sudo snapcraft --build-for=amd64 --verbosity=verbose