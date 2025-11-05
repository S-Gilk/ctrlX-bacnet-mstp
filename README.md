This is a snap to execute BACnet MS/TP operations via the ctrlX OS datalayer.

# Instructions
## Connection properties can be modified in bc.ini
  - Make sure the interface field matches the serial device mount location
  - Make sure the address field does not collide with a device on the BACnet network
  - Make sure baud matches BACnet network baud
## Device objects are defined in bacnet_defines.json
  - Device objects can be added here. Follow the pattern provided. The access field is for the presentValue (ie. inputs are read only)
