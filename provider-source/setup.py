# SPDX-FileCopyrightText: Bosch Rexroth AG
#
# SPDX-License-Identifier: MIT
from setuptools import setup


setup(name = 'ctrlx-bacnet-mstp',
      version = '1.0.0',
      description = 'ctrlX Data Layer provider for BACnet MS/TP interface',
      author = 'Sam Gilk',
      packages = ['config', 'helper', 'provider_nodes'],
      install_requires=['ctrlx-datalayer<=3.5', 'ctrlx-fbs'], 
      scripts = ['main.py', 'defines.py', 'utils.py'],
      license = 'MIT License'
)