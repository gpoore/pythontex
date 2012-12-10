#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Install PythonTeX

This script installs one set of PythonTeX scripts for use under Python 2.6-2.7 
(names end in "2") and another set for user under Python 3 (names end in "3").
You will need to launch the correct script depending on the default version of
Python on your system.

This script should work with most TeX distributions.  It is primarily written 
for TeX Live.  It should work with other TeX distributions that use the 
Kpathsea library (such as MiKTeX), though with reduced functionality in some 
cases.  It should work with additional distributions as well, but will require 
manual input when Kpathsea is not present.  When the script cannot find TeX 
Live-style functionality, it alerts the user and attempts to proceed.

The script will overwrite (and thus update) all previously installed PythonTeX 
files.  During automated installation (Kpathsea), files are NOT installed in 
the LOCAL texmf tree, because we want auto-updating once PythonTeX is added to 
CTAN.  The texhash command (if present) is executed to make the system aware 
of any new files.

Copyright (c) 2012, Geoffrey M. Poore
All rights reserved.
Licensed under the BSD 3-Clause License:
    http://www.opensource.org/licenses/BSD-3-Clause

'''


# Imports
import sys
import platform
from os import path, mkdir, symlink, chmod
from subprocess import check_call, check_output, CalledProcessError
from shutil import copy


# We need a version of input that works under both Python 2 and 3
try:
    input = raw_input
except:
    pass


# Make sure all necessary files are present
needed_files = ['pythontex2.py', 'pythontex_types2.py', 'pythontex_utils2.py', 
                'pythontex3.py', 'pythontex_types3.py', 'pythontex_utils3.py', 
                'pythontex.sty', 'pythontex.ins', 'pythontex.dtx', 
                'pythontex.pdf', 'README.rst', 'async_pylab_save.py']
missing_files = False
# Print a list of all files that are missing, and exit if any are
for eachfile in needed_files:
    if not path.exists(eachfile):
        print('Could not find file ' + eachfile)
        missing_files = True
if missing_files:
    print('Exiting.')
    sys.exit(1)

# Retrieve the location of a valid TeX tree
# Attempt to use kpsewhich; otherwise, resort to manual input 
try:
    if sys.version_info[0] == 2:
        texmf_path = check_output(['kpsewhich', '-var-value', 'TEXMFDIST']).rstrip('\r\n')
    else:
        texmf_path = check_output(['kpsewhich', '-var-value', 'TEXMFDIST']).decode('utf-8').rstrip('\r\n')
except OSError:
    print('\nYour system appears to lack kpsewhich.')
    print('Cannot automatically find a valid texmf path.')
    texmf_path = input('Please enter a valid texmf path: ').rstrip('\r\n')
except CalledProcessError:
    print('\nkpsewhich is not happy with its arguments.')
    print('Cannot automatically find a valid texmf path.')
    texmf_path = input('Please enter a valid texmf path: ').rstrip('\r\n')

# Print starting message
print('\nInstalling PythonTeX into directory ' + texmf_path)

# Make sure path slashes are compatible with the operating system 
# This is only needed for Windows
texmf_path = path.normcase(texmf_path)
# Check to make sure the path is valid 
# This is only really needed for manual input 
# The '' check is for empty manual input
if texmf_path == '' or not path.exists(texmf_path):
    print('Invalid texmf path.  Exiting.')
    sys.exit(1)
# Now check that all other needed paths are present
doc_path = path.join(texmf_path, 'doc', 'latex')
package_path = path.join(texmf_path, 'tex', 'latex')
scripts_path = path.join(texmf_path, 'scripts')
source_path = path.join(texmf_path, 'source', 'latex')
missing_paths = False
for eachpath in [doc_path, package_path, scripts_path, source_path]:
    if not path.exists(eachpath):
        print('Could not find path ' + eachpath)
        missing_paths = True
if missing_paths:
    print('Exiting.')
    sys.exit(1)
# Modify the paths by adding the pythontex directory, which will be created
doc_path = path.join(doc_path, 'pythontex')
package_path = path.join(package_path, 'pythontex')
scripts_path = path.join(scripts_path, 'pythontex')
source_path = path.join(source_path, 'pythontex')


#Install docs
if not path.exists(doc_path):
    mkdir(doc_path)
copy('pythontex.pdf', doc_path)
copy('README.rst', doc_path)
# Install package
if not path.exists(package_path):
    mkdir(package_path)
copy('pythontex.sty', package_path)
# Install scripts
if not path.exists(scripts_path):
    mkdir(scripts_path)
copy('pythontex2.py', scripts_path)
copy('pythontex_types2.py', scripts_path)
copy('pythontex_utils2.py', scripts_path)
copy('pythontex3.py', scripts_path)
copy('pythontex_types3.py', scripts_path)
copy('pythontex_utils3.py', scripts_path)
copy('async_pylab_save.py', scripts_path)
# Install source
if not path.exists(source_path):
    mkdir(source_path)
copy('pythontex.ins', source_path)
copy('pythontex.dtx', source_path)


# Install "binaries" or suggest the cretaion of binaries/batch files/symlinks
# This part is operating-system dependent
#
# If under Windows, we create a binary wrapper if under TeX Live and otherwise
# alert the user regarding the need for a wrapper or batch file
if platform.system() == 'Windows':
    # Assembly the binary path, assuming TeX Live
    # The directory bin/ should be at the same level as texmf
    bin_path = path.join(path.split(texmf_path)[0], 'bin', 'win32') 
    if path.exists(path.join(bin_path, 'runscript.exe')):
        print('\nCreating binary wrapper...')        
        copy(path.join(bin_path, 'runscript.exe'), path.join(bin_path, 'pythontex2.exe'))
        copy(path.join(bin_path, 'runscript.exe'), path.join(bin_path, 'pythontex3.exe'))
    else:
        print('\nCould not create a wrapper for launching pythontex.py.')
        print('You will need to create a wrapper manually, or use a batch file.')
        print('The wrapper or batch file should be placed somewhere on the Windows PATH.')
        print('The bin/ directory in your TeX distribution may be a good location.')
        print('The script pythontex.py is located in the following directory:')
        print('    ' + scripts_path)
elif platform.system() in ['Linux', 'Darwin']: # todo: check for unix (maybe just check to see if os.symlink fails or not?)
    root_path = path.split(texmf_path)[0]
    bin_path = path.join(path.split(root_path)[0], 'bin')
    if path.exists(bin_path):
        for ver in [2, 3]:
            link = path.join(bin_path, 'pythontex{0}.py'.format(ver))
            try:
                symlink(path.join(scripts_path, 'pythontex{0}.py'.format(ver)), link)
            except OSError as e:
                if e.errno == 17:
                    pass # File exists
                else:
                    raise OSError(e)
            chmod(link, 0775)
            print('symlink created ' + link)
    else:
        print('\nCreating symlink failed, you may wish to create a symlink to pythontex.py.')
        print('You may also want to make it executable via chmod.')
        print('The script pythontex.py is located in the following directory:')
        print('    ' + scripts_path)
# If not under known system, we alert the user regarding what is necessary to launch
# pythontex.py
else:
    print('\nYou may wish to create a symlink to pythontex.py.')
    print('You may also want to make it executable via chmod.')
    print('The script pythontex.py is located in the following directory:')
    print('    ' + scripts_path)


# Alert TeX to the existence of the package via texhash
print('\nRunning texhash...')
try:
    check_call(['texhash'])
except OSError:
    print('Could not run texhash.  Your system appears to lack texhash.')
    print('Your system may not be aware of newly installed files.')


# Alert the user to the need to choose a version
print('\n\n* * *')
print('PythonTeX contains separate scripts for Python 2 and Python 3.')
print('Choose the correct scripts based on your Python installation.')
print('See the documentation for more information.')
print('* * *\n')

if platform.system() == 'Windows':
    # Pause so that the user can see any errors or other messages
    input('\n[Press ENTER to exit]')
