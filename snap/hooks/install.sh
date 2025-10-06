#!/bin/sh
set -e

mkdir -p "$SNAP_COMMON/config"

# Only create if missing
if [ ! -f "$SNAP_COMMON/config/bc.ini" ]; then
  cp "$SNAP/defaults/bc.ini" "$SNAP_COMMON/config/bc.ini"
fi
