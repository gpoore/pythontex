#!/usr/bin/env python

# Install PythonTeX.
# This script is written for Windows with TeX Live, but should be mostly functional with TeX Live under other operating systems, and may also be coaxed into working with other TeX distributions.
# This will overwrite (and thus update) all previously installed PythonTeX files.
# Files are NOT installed in the LOCAL texmf tree, because we want auto-updating once PythonTeX is added to CTAN.
# The texhash command is also executed, to make the system aware of any new files.
#
# Copyright (c) 2012, Geoffrey M. Poore
# All rights reserved.
# Licensed under the Modified BSD License.
#


# Imports
import sys
import platform
from os import path, mkdir, listdir
from subprocess import call, check_output, CalledProcessError
from shutil import copy


# Make sure all necessary files are present
needed_files=['pythontex.py', 'pythontex_types.py', 'pythontex_utils.py', 'pythontex.sty', \
        'pythontex.ins', 'pythontex.dtx', 'pythontex.pdf', 'README.rst']
for file in needed_files:
    if not path.exists(file):
        print('Could not find file ' + file + '.  Exiting.')
        sys.exit(1)


# Print starting message
print('Installing PythonTeX...')


# We need to use input sometimes, but must account for differences between Python 2 and 3
try:
    input=raw_input
except:
    pass


# Retrieve the location of a valid TeX tree
try:
    texmf_path=check_output('kpsewhich -var-value TEXMFDIST'.split()).rstrip('\r\n')
    texmf_path=path.normcase(texmf_path)
except CalledProcessError:
    print('Cannot automatically find a valid texmf path.')
    texmf_path=input('Please enter a valid texmf path: ').rstrip('\r\n')
    texmf_path=path.normcase(texmf_path)
# Check to make sure path is valid
if not path.exists(texmf_path):
    print('Invalid texmf path.  Exiting.')
    sys.exit(1)
# Now check that all other needed paths are present
scripts_path=path.join(texmf_path,'scripts')
bin_path=path.join(path.split(texmf_path)[0],'bin') # bin/ is at the same level as texmf
if not(path.exists(bin_path)):                      # Hmm, what if it is one level down? (is on macport install)
    bin_path=path.split(texmf_path)[0]
    bin_path=path.split(bin_path)[0]
    bin_path=path.join(bin_path, 'bin')
if len(listdir(bin_path))>0:
    # We need to find the name of the system-specific subdirectory within bin/ in which binary files are kept
    bin_path=path.join(bin_path,listdir(bin_path)[0])
else:
    print('Cannot find system-specific directory within bin/.  Exiting.')
    sys.exit(1)
package_path=path.join(texmf_path,'tex','latex')
source_path=path.join(texmf_path,'source','latex')
doc_path=path.join(texmf_path,'doc','latex')
for eachpath in [scripts_path, bin_path, package_path, source_path, doc_path]:
    if not path.exists(eachpath):
        print('Could not find path ' + eachpath + '.')
        sys.exit(1)
scripts_path=path.join(scripts_path,'pythontex')
package_path=path.join(package_path,'pythontex')
source_path=path.join(source_path,'pythontex')
doc_path=path.join(doc_path,'pythontex')


# Install scripts
if not path.exists(scripts_path):
    mkdir(scripts_path)
copy('pythontex.py', scripts_path)
copy('pythontex_types.py', scripts_path)
copy('pythontex_utils.py', scripts_path)


# Install "binaries"
if platform.system()=='Windows':
    try:
        copy(path.join(bin_path, 'runscript.exe'), path.join(bin_path, 'pythontex.exe'))
    except IOError:
        print('Could not create a wrapper for launching pythontex.py.')
        print('You will need to create a wrapper manually, or use a batch file.')
else:
    print('You will need to create a symlink to pythontex.py,\n or otherwise configure your system to launch it.')

    
# Install package
if not path.exists(package_path):
    mkdir(package_path)
copy('pythontex.sty', package_path)


# Install source and docs
if not path.exists(source_path):
    mkdir(source_path)
copy('pythontex.ins', source_path)
copy('pythontex.dtx', source_path)
if not path.exists(doc_path):
    mkdir(doc_path)
copy('pythontex.pdf', doc_path)
copy('README.rst', doc_path)


# Alert TeX to the existence of the package if necessary
print('\nRunning texhash...')
call('texhash')


# Pause so that the user can see any errors or other messages
input('\n[Press ENTER to exit]')
