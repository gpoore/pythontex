#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
This is the PythonTeX wrapper script.  It automatically detects the version
of Python, and then imports the correct code from pythontex2.py or
pythontex3.py.  It is intended for use with the default Python installation
on your system.  If you wish to use a different version of Python, you could
launch pythontex2.py or pythontex3.py directly.  You should also consider the
command-line option `--interpreter`.  This allows you to specify the command
that is actually used to execute the code from your LaTeX documents.  Except
for Python console content, it doesn't matter which version of Python is used
to launch pythontex.py; pythontex.py just manages the execution of code from
your LaTeX document.  The interpreter setting is what determines the version
under which your code is actually executed.

Licensed under the BSD 3-Clause License:

Copyright (c) 2012-2017, Geoffrey M. Poore

All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of the <organization> nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
'''


import sys
if sys.version_info.major == 2:
    if sys.version_info.minor >= 7:
        import pythontex2 as pythontex
    else:
        sys.exit('PythonTeX require Python 2.7; you are using 2.{0}'.format(sys.version_info.minor))
elif sys.version_info.major == 3:
    if sys.version_info.minor >= 2:
        import pythontex3 as pythontex
    else:
        sys.exit('PythonTeX require Python 3.2+; you are using 3.{0}'.format(sys.version_info.minor))

# The "if" statement is needed for multiprocessing under Windows; see the
# multiprocessing documentation.
if __name__ == '__main__':
    pythontex.main()
