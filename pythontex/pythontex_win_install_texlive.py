#!/usr/bin/python

#Install PythonTeX on Windows with default TeX Live installation.
#This will overwrite (and thus update) all previously installed PythonTeX files.
#For a first-time install, the "texhash" command is also executed.


#Imports
from os import path, mkdir
from subprocess import call
from shutil import copy

#Install scripts
scripts_dir=r'C:\texlive\2011\texmf-dist\scripts\pythontex'
if not path.exists(scripts_dir):
    mkdir(scripts_dir)
    copy('pythontex.py', scripts_dir)
    copy('pythontex_types.py', scripts_dir)
    copy('pythontex_utils.py', scripts_dir)
else:
    copy('pythontex.py', scripts_dir)
    copy('pythontex_types.py', scripts_dir)
    copy('pythontex_utils.py', scripts_dir)

#Install "binaries"
bin_dir=r'C:\texlive\2011\bin\win32'
if not path.exists(path.join(bin_dir, 'pythontex.exe')):
    copy(path.join(bin_dir, 'runscript.exe'), path.join(bin_dir, 'pythontex.exe'))

package_dir=r'C:\texlive\2011\texmf-dist\tex\latex\pythontex'
if not path.exists(package_dir):
    mkdir(package_dir)
    copy('pythontex.sty', package_dir)
    call('texhash')
else:
    copy('pythontex.sty', package_dir)


#Install source and docs
source_dir=r'C:\texlive\2011\texmf-dist\source\latex\pythontex'
if not path.exists(source_dir):
    mkdir(source_dir)
    copy('pythontex.ins', source_dir)
    copy('pythontex.dtx', source_dir)
else:
    copy('pythontex.ins', source_dir)
    copy('pythontex.dtx', source_dir)
doc_dir=r'C:\texlive\2011\texmf-dist\doc\latex'
if not path.exists(doc_dir):
    mkdir(doc_dir)
    copy('pythontex.pdf', doc_dir)
    copy('README', doc_dir)
else:
    copy('pythontex.ins', source_dir)
    copy('README', doc_dir)
    
    
#Install custom SymPy LaTeX printer for Python 2.7, if applicable
#sympy_dir=r'C:\Python27\Lib\site-packages\sympy\printing'
#if path.exists(sympy_dir) and path.exists('latex.py'):
#    copy('latex.py', sympy_dir)
