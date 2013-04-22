# -*- coding: utf-8 -*-
'''
This is the PythonTeX wrapper script.  It automatically detects the version
of Python, and then imports the correct code from depythontex2.py or 
depythontex3.py.

Copyright (c) 2013, Geoffrey M. Poore
All rights reserved.
Licensed under the BSD 3-Clause License:
    http://www.opensource.org/licenses/BSD-3-Clause

'''

import sys
if sys.version_info[0] == 2:
    import depythontex2 as depythontex
elif sys.version_info[0] == 3:
    import depythontex3 as depythontex
