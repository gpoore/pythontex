#!/usr/bin/env python

# Copyright (c) 2012, Geoffrey M. Poore
# All rights reserved.
# Licensed under the Modified BSD License.
#

from collections import defaultdict
from copy import deepcopy
from os import path
from re import match
import sys

#Create a class that is used for command/environment families
#The class provides functions for managing the following:
#--Passing parameters to Python scripts through set_inputs
#--Managing printing through set_printing
#--Setting working directory through set_workingdir
#--Opening and closing the file to which labels are written, through open_reffile and close_reffile
class Codetype:
    def __init__(self,language,extension,command,shebang,imports):
        self.language=language
        self.extension=extension
        self.command=command
        self.shebang=shebang
        self.imports=imports
    def set_inputs(self,inputtype,inputsession,inputgroup,inputinstance,inputcmd,inputstyle,inputline):
        mystr='pytex.inputtype=\''+inputtype+'\'\n'
        mystr+='pytex.inputsession=\''+inputsession+'\'\n'
        mystr+='pytex.inputgroup=\''+inputgroup+'\'\n'
        mystr+='pytex.inputinstance=\''+inputinstance+'\'\n'
        mystr+='pytex.inputcmd=\''+inputcmd+'\'\n'
        mystr+='pytex.inputstyle=\''+inputstyle+'\'\n'
        mystr+='pytex.inputline=\''+inputline+'\'\n'
        return mystr
    def set_printing(self,inputinstance):
        return 'print(\'=>PYTHONTEX#PRINT#'+inputinstance+'#\')\n'
    def set_workingdir(self,pytexdir):
        return 'os.chdir(\''+pytexdir+'\')\n'
    def open_reffile(self,pytexdir,jobname):
        return 'pytex.reffile=open(\''+jobname+'.pytxref\',\'w\')\n'
    def close_reffile(self,pytexdir,jobname):
        return 'pytex.reffile.close()\n'
    def inline(self,codeline):
        return 'pytex.reffile.write(pytex.refprint('+codeline.rstrip('\r\n')+'))\n'


typedict=defaultdict(Codetype)

typedict['py']=Codetype(
    'python',
    'py',
    r'python ',
    '#!/usr/bin/env python',
    ['import os',
     'import pythontex_utils as pytex']
    
typedict['sympy']=deepcopy(typedict['py'])
typedict['sympy'].imports.extend(['from sympy import *'])
typedict['sympy'].imports.extend(['pytex.use_sympy_latex_printer=True'])

typedict['pylab']=deepcopy(typedict['py'])
typedict['pylab'].imports.extend(['from pylab import *'])


#Detect if running under Python 2.x
#If so, make Python scripts import division and the print function
if sys.version_info[0]==2:
    for codetype in typedict:
        if typedict[codetype].language=='python':
            typedict[codetype].imports.insert(0,'from __future__ import division')
            typedict[codetype].imports.insert(0,'from __future__ import print_function')

def update_types_import(script_path):
    for eachtype in typedict:
        if typedict[eachtype].language=='python':
            line=0
            while '__future__' in typedict[eachtype].imports[line]:
                line+=1
            typedict[eachtype].imports.insert(line,'import sys')
            typedict[eachtype].imports.insert(line+1,'sys.path.append(\''+script_path+'\')')
