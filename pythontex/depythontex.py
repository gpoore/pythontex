#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
This is the depythontex wrapper script.  It automatically detects the version
of Python, and then imports the correct code from depythontex2.py or
depythontex3.py.  It is intended for use with the default Python installation
on your system.  If you wish to use a different version of Python, you could
launch depythontex2.py or depythontex3.py directly.  The version of Python
does not matter for depythontex, since no code is executed.

Copyright (c) 2013-2017, Geoffrey M. Poore
All rights reserved.
Licensed under the BSD 3-Clause License:
    http://www.opensource.org/licenses/BSD-3-Clause

'''

import sys
if sys.version_info[0] == 2:
    import depythontex2 as depythontex
elif sys.version_info[0] == 3:
    import depythontex3 as depythontex
