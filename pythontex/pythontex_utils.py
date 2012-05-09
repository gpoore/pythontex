#!/usr/bin/env python
#PythonTeX utilities

# Copyright (c) 2012, Geoffrey M. Poore
# All rights reserved.
# Licensed under the Modified BSD License.
#

from collections import defaultdict
try:
    from sympy.printing.latex import LatexPrinter
    sympy_exists=True
except ImportError:
    sympy_exists=False


#Variables for keeping track of PythonTeX instance and document line number in .tex file
inputtype=''
inputsession=''
inputgroup=''
inputinstance=''
inputcmd=''
inputstyle=''
inputline=''


#Context-aware interface to SymPy's latex function
if sympy_exists:
    sympy_settings=defaultdict(dict)
    sympy_settings['nonmath']={
    }
    sympy_settings['text']={
        "mat_str": "smallmatrix",
        "mat_delim": "(",
        #If there's ever an option for using a total derivative symbol
        #"total_deriv_symbol": False,
    }
    sympy_settings['display']={
        "mat_str": "pmatrix",
        "mat_delim": None,
        #If there's ever an option for using a total derivative symbol
        #"total_deriv_symbol": False,
    }
    # ####
    # The following needs to be revised so that any value are allowed in settings
    # ####
    def sympy_latex(expr):
        if inputstyle in ['align', 'gather', 'display']:
            return LatexPrinter(sympy_settings['display']).doprint(expr)
        elif inputstyle=='text':
            return LatexPrinter(sympy_settings['text']).doprint(expr)
        else:
            return LatexPrinter(sympy_settings['nonmath']).doprint(expr)
#Determine whether SymPy's latex is invoked for printing references
use_sympy_latex_printer=False


#Function for "printing" via references
def refprint(expr):
    before='\\newlabel{pytx@'+inputtype+'@'+inputsession+'@'+inputgroup+'@'+inputinstance+'}{{'
    after='}{}{}{}{}}\n'
    if use_sympy_latex_printer:
        return before+sympy_latex(expr)+after
    else:
        return before+str(expr)+after
