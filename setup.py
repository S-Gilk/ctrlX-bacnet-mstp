# SPDX-FileCopyrightText: Bosch Rexroth AG
#
# SPDX-License-Identifier: MIT
from setuptools import setup


setup(name = 'ctrlx-bacnet-mstp',
      version = '1.0.0',
      description = 'ctrlX Data Layer provider and BACnet MS/TP driver',
      author = 'Sam Gilk',
      packages = ['misty', 'provider-source'],
      license = 'MIT License'
)