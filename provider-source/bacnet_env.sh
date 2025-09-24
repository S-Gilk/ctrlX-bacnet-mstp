#!/bin/bash
# BACnet MS/TP environment setup script

# Notes:
# Build
    # make clean
    # make BACDL=mstp
# Modified /ports/linux/rs485.c to set RTS

# Serial device for your FTDI RS-485 adapter
export BACNET_IFACE=/dev/ttyUSB0

# Baud rate (must match your slave device)
export BACNET_MSTP_BAUD=38400

# Local MS/TP MAC address (use a low unused address, e.g. 1 or 2)
export BACNET_MSTP_MAC=9

# Optional: adjust if you need more frames per token
export BACNET_MAX_INFO_FRAMES=1

# Optional: max master address (default 127)
export BACNET_MAX_MASTER=10

echo "BACnet MS/TP environment configured:"
echo "  BACNET_IFACE=$BACNET_IFACE"
echo "  BACNET_BAUD=$BACNET_BAUD"
echo "  DEFAULT_MAC_ADDRESS=$DEFAULT_MAC_ADDRESS"
echo "  BACNET_MAX_INFO_FRAMES=$BACNET_MAX_INFO_FRAMES"
echo "  BACNET_MAX_MASTER=$BACNET_MAX_MASTER"