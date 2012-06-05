# -*- coding: ascii -*-
'''
PythonTeX types

Provides a class for defining the code types that may be executed by default.

Copyright (c) 2012, Geoffrey M. Poore
All rights reserved.
Licensed under the BSD 3-Clause License:
    http://www.opensource.org/licenses/BSD-3-Clause

'''


# Imports
import sys
import textwrap
import copy


class Codetype(object):
    '''
    Create a class that is used for defining command and environment families
    
    The class provides methods that are used for writing the individual 
    scripts that PythonTeX executes.
    '''
    def __init__(self, language, extension, command, default_code, utils_code, 
                 command_options=None, shebang='', custom_code=None):
        '''
        Assign values and do some type checking and default-value assignment
        '''
        # We need a unicode-agnostic way to detect strings under both Python 2 and 3
        try:
            str = basestring
        except:
            pass
        
        if isinstance(language, str):
            self.language = language
        else:
            raise TypeError("'language' must be a string")
        
        if isinstance(extension, str):
            self.extension = extension
        else:
            raise TypeError("'extension' must be a string")
        
        if isinstance(command, str):
            self.command = command
        else:
            raise TypeError("'command' must be a string")

        if isinstance(default_code, list):
            self.default_code = default_code
        else:
            raise TypeError("'default_code' must be a list")
        
        if isinstance(utils_code, list):
            self.utils_code = utils_code
        else:
            raise TypeError("'utils_code' must be a list")
        
        if command_options == None:
            self.command_options == []
        elif isinstance(command_options, list):
            self.command_options = command_options
        else:
            raise TypeError("'command_options' must be a list")
        
        if isinstance(shebang, str):
            self.shebang = shebang
        else:
            raise TypeError("'shebang' must be a string")
                
        if custom_code == None:
            self.custom_code = []
        elif isinstance(custom_code, list):
            self.custom_code = custom_code
        else:
            raise TypeError("'custom_code' must be a list")
        
        '''
        Finish setup by assigning "template strings" based on language
        '''
        self._init_strings()
    
    '''
    Create dicts of "template code" strings that are used when creating 
    individual scripts.  The dicts are organized by language.
    
    The strings are created so that the str.format() method may be used to
    insert the actual values; hence, the presence of integers in curley 
    braces.  Strings defined with triple quotes may be indented for clarity.
    Any leading whitespace is removed during __init__ by _init_strings().  
    Strings defined with triple quotes should begin and end with two blank 
    lines, to ensure that error line numbers may be correctly determined.
    
    These dicts may need to be moved outside the class definition eventually,
    if more languages are added.
    ''' 
    inputs_string_const_dict = dict()
    inputs_string_var_dict = dict()
    open_macrofile_string_dict = dict()
    close_macrofile_string_dict = dict()
    set_workingdir_string_dict = dict()
    inline_string_dict = dict()
    
    inputs_string_const_dict['python'] = """
            
            pytex.inputtype = '{0}'
            pytex.inputsession = '{1}'
            pytex.inputgroup = '{2}'
            
            """    
    inputs_string_var_dict['python'] = """
            
            pytex.inputinstance = '{0}'
            print('=>PYTHONTEX#PRINT#{0}#')
            pytex.inputcommand = '{1}'
            pytex.inputstyle = '{2}'
            pytex.inputline = '{3}'
            
            """
    open_macrofile_string_dict['python'] = """
            if os.path.exists('{0}'):
                pytex.macrofile = open(os.path.join('{0}', '{1}.pytxref'), 'w')
            else:
                pytex.macrofile = open('{1}.pytxref', 'w')
            """
    close_macrofile_string_dict['python'] = 'pytex.macrofile.close()\n'
    set_workingdir_string_dict['python'] = """
            if os.path.exists('{0}'):
                os.chdir('{0}')
            """
    inline_string_dict['python'] = 'pytex._print_via_macro({0})\n'
    
    def _init_strings(self):
        '''
        Assign strings used for creating individual scripts, cleaning up 
        unneeded leading indentation in the process
        
        Removing leading indentation is necessary because we want to indent 
        the triple-quoted strings so that they look better, but don't need 
        the indentation in the actual code files
        '''
        self.inputs_string_const = textwrap.dedent(self.inputs_string_const_dict[self.language])
        self.inputs_string_var = textwrap.dedent(self.inputs_string_var_dict[self.language])
        self.open_macrofile_string = textwrap.dedent(self.open_macrofile_string_dict[self.language])
        self.close_macrofile_string = textwrap.dedent(self.close_macrofile_string_dict[self.language])
        self.set_workingdir_string = textwrap.dedent(self.set_workingdir_string_dict[self.language])
        self.inline_string = textwrap.dedent(self.inline_string_dict[self.language])
    
    def set_inputs_const(self, inputtype, inputsession, inputgroup):
        '''
        Format an inputs_string_const for use
        '''
        return self.inputs_string_const.format(inputtype, inputsession, inputgroup)
        
    def set_inputs_var(self, inputinstance, inputcommand, inputstyle, inputline):
        '''
        Format an inputs_string_var for use
        '''
        return self.inputs_string_var.format(inputinstance, inputcommand, inputstyle, inputline)
    
    def open_macrofile(self, pytexdir, jobname):
        '''
        Create code that will open a file in which LateX macros containing 
        outputted content are saved.
        '''
        return self.open_macrofile_string.format(pytexdir, jobname)
    
    def close_macrofile(self):
        '''
        Create code that will close the macro file.
        '''
        return self.close_macrofile_string

    def set_workingdir(self, workingdir):
        '''
        Set the working directory
        '''
        return self.set_workingdir_string.format(workingdir)
    
    def inline(self, codeline):
        '''
        Create code that will save content via a macro
        '''
        return self.inline_string.format(codeline.rstrip('\r\n'))


'''
Create a dictionary of command and environment families

Create the py, sympy, and pylab families
'''
typedict = dict()


typedict['py'] = Codetype(
    language = 'python',
    extension = 'py',
    command = 'python',
    command_options = [],
    shebang = '#!/usr/bin/env python',
    default_code = ['import os', 'import sys'],
    utils_code = [],
    custom_code = [])


typedict['sympy'] = copy.deepcopy(typedict['py'])
typedict['sympy'].utils_code.extend(["pytex.set_formatter('sympy_latex')"])
typedict['sympy'].custom_code.extend(['from sympy import *'])


typedict['pylab'] = copy.deepcopy(typedict['py'])
typedict['pylab'].custom_code.extend(['from pylab import *'])


'''
Detect if running under Python 2.x

If so, make Python scripts import from future (only imports relevant to >= 2.6)

We DO NOT automatically import unicode_literals, because it can produce 
problems with imported packages (for example, SymPy).  Given the acceptance of
PEP 414 (http://www.python.org/dev/peps/pep-0414/) for Python 3.3+, the 
need to import unicode_literals is also somewhat lessened.
'''
if sys.version_info[0] == 2:
    for codetype in typedict:
        if typedict[codetype].language == 'python':
            typedict[codetype].default_code.insert(0, 'from __future__ import absolute_import')
            typedict[codetype].default_code.insert(0, 'from __future__ import division')
            typedict[codetype].default_code.insert(0, 'from __future__ import print_function')
            #typedict[codetype].default_code.insert(0, 'from __future__ import unicode_literals')


def set_utils_location(script_path):
    '''
    Update the utils_code variable in each family in the typedict with the 
    location of utilities scripts
    '''
    for eachtype in typedict:
        if typedict[eachtype].language == 'python':
            typedict[eachtype].utils_code = ["sys.path.append('{0}')".format(script_path), 'from pythontex_utils import PythontexUtils', 'pytex = PythontexUtils()'] + typedict[eachtype].utils_code
