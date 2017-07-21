#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Convert PythonTeX scripts from Python 2 to Python 3

It isn't possible to have a single PythonTeX code base, since unicode text
needs to be supported.  Under Python 2, this means importing unicode_literals
from __future__, or using the unicode function or "u" prefix.  Under Python 3,
all strings are automatically unicode.

At the same time, the differences between the Python 2 and 3 versions are
usually very small, involving only a few lines of code.  To keep the code base
unified, while simultaneously fully supporting both Python 2 and 3, the
following scheme was devised.  The code is written for Python 2.  Whenever
code is not compatible with Python 3, it is enclosed with the tags
"#// Python 2" and "#\\ End Python 2" (each on its own line, by itself).  If
a Python 3 version of the code is needed, it is included between analogous
tags "#// Python 3" and "#\\ End Python 2".  The Python 3 code is commented
out with "#", at the same indentation level as the Python 3 tags.

This script creates Python 3 scripts from the original Python 2 scripts
by commenting out everything between the Python 2 tags, and uncommenting
everything between the Python 3 tags.  In this way, full compatibility is
maintained with both Python 2 and 3 while keeping the code base essentially
unified.  This approach also allows greater customization of version-specific
code than would be possible if automatic translation with a tool like 2to3
was required.

Copyright (c) 2012-2017, Geoffrey M. Poore
All rights reserved.
Licensed under the BSD 3-Clause License:
    http://www.opensource.org/licenses/BSD-3-Clause

'''


# Imports
from __future__ import unicode_literals
from io import open
import re


files_to_process = ('pythontex2.py', 'depythontex2.py')
encoding = 'utf-8'


def from2to3(list_of_code):
    fixed = []
    in_2 = False
    in_3 = False
    indent = ''

    for line in list_of_code:
        if r'#// Python 2' in line:
            in_2 = True
            indent = line.split('#', 1)[0]
        elif r'#\\ End Python 2' in line:
            in_2 = False
        elif r'#// Python 3' in line:
            in_3 = True
            indent = line.split('#', 1)[0]
        elif r'#\\ End Python 3' in line:
            in_3 = False
        elif in_2:
            line = re.sub(indent, indent + '#', line, count=1)
        elif in_3:
            line = re.sub(indent + '#', indent, line, count=1)
        fixed.append(line)
    if fixed[0].startswith('#!/usr/bin/env python2'):
        fixed[0] = fixed[0].replace('python2', 'python3')
    return fixed


for file in files_to_process:
    f = open(file, 'r', encoding=encoding)
    converted_code = from2to3(f.readlines())
    f.close()
    f = open(re.sub('2', '3', file), 'w', encoding=encoding)
    f.write(''.join(converted_code))
    f.close()


