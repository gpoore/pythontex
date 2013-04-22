# -*- coding: utf-8 -*-
'''
PythonTeX types.

Provides a class for defining the code types that may be executed by default.
Uses this class to create the default code types.  Provides functions for 
dealing with the code types.

Copyright (c) 2012-2013, Geoffrey M. Poore
All rights reserved.
Licensed under the BSD 3-Clause License:
    http://www.opensource.org/licenses/BSD-3-Clause

'''

# Imports
#// Python 2
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
#\\ End Python 2
import textwrap
import copy


class Codetype(object):
    '''
    A class that is used for defining command and environment families.
    
    The class provides methods that are used for writing the individual 
    scripts that PythonTeX executes.
    '''
    def __init__(self, language, extension, command, default_code, utils_code, 
                 command_options=None, shebang='', custom_code_begin=None, 
                 custom_code_end=None):        
        # Process arguments and do some type checking
        
        #// Python 2
        if isinstance(language, basestring):
        #\\ End Python 2
        #// Python 3
        #if isinstance(language, str):
        #\\ End Python 3
            self.language = language
        else:
            raise TypeError("'language' must be a string")
        
        #// Python 2
        if isinstance(extension, basestring):
        #\\ End Python 2
        #// Python 3
        #if isinstance(extension, str):
        #\\ End Python 3
            self.extension = extension
        else:
            raise TypeError("'extension' must be a string")
        
        #// Python 2
        if isinstance(command, basestring):
        #\\ End Python 2
        #// Python 3
        #if isinstance(command, str):
        #\\ End Python 3
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
        
        #// Python 2
        if isinstance(shebang, basestring):
        #\\ End Python 2
        #// Python 3
        #if isinstance(shebang, str):
        #\\ End Python 3
            self.shebang = shebang
        else:
            raise TypeError("'shebang' must be a string")
                
        if custom_code_begin == None:
            self.custom_code_begin = []
        elif isinstance(custom_code_begin, list):
            self.custom_code_begin = custom_code_begin
        else:
            raise TypeError("'custom_code_begin' must be a list")
        if custom_code_end == None:
            self.custom_code_end = []
        elif isinstance(custom_code_end, list):
            self.custom_code_end = custom_code_end
        else:
            raise TypeError("'custom_code_end' must be a list")
        
        # Finish setup by assigning "template strings" based on language
        self._init_strings()
    
    # Create dicts of "template code" strings that are used when creating 
    # individual scripts.  The dicts are organized by language.
    #
    # The strings are created so that the str.format() method may be used to
    # insert the actual values; hence, the presence of integers in curley 
    # braces.  Strings defined with triple quotes may be indented for clarity.
    # Any leading whitespace is removed during __init__ by _init_strings().  
    # The inputs_string_var should begin and end with two blank lines, to 
    # ensure that error line numbers may be correctly determined.
    #
    # These dicts may need to be moved outside the class definition eventually,
    # if more languages are added.
    utils_string_dict = dict()
    inputs_string_const_dict = dict()
    inputs_string_var_dict = dict()
    encode_stdout_string_dict = dict()    
    open_macrofile_string_dict = dict()
    close_macrofile_string_dict = dict()
    cleanup_string_dict = dict()
    set_workingdir_string_dict = dict()
    inline_string_dict = dict()
    encoding_string_dict = dict()
    
    utils_string_dict['python'] = """
            sys.path.append('{0}')
            from pythontex_utils import PythontexUtils
            pytex = PythontexUtils()
            """
    
    inputs_string_const_dict['python'] = """
            
            pytex.inputtype = '{0}'
            pytex.inputsession = '{1}'
            pytex.inputgroup = '{2}'
            
            """    
    
    inputs_string_var_dict['python'] = """
            
            pytex.inputinstance = '{0}'
            print('=>PYTHONTEX:PRINT#{0}#')
            pytex.inputcommand = '{1}'
            pytex.inputcontext = '{2}'
            pytex.inputline = '{3}'
            
            """
    
    # stdout is redirected to a file, and requires appropriate encoding
    #// Python 2
    encode_stdout_string_dict['python'] = """
            sys.stdout = codecs.getwriter('{0}')(sys.stdout, 'strict')
            sys.stderr = codecs.getwriter('{0}')(sys.stderr, 'strict')
            """
    #\\ End Python 2
    #// Python 3
    #encode_stdout_string_dict['python'] = """
    #        sys.stdout = codecs.getwriter('{0}')(sys.stdout.buffer, 'strict')
    #        sys.stderr = codecs.getwriter('{0}')(sys.stderr.buffer, 'strict')
    #        """
    #\\ End Python 3
    
    # Use conditionals for opening macrofile, so that the script will run 
    # from both the document root directory (standard) and the 
    # pythontex-files-* directory (for debugging, if keeptemps is used).
    #// Python 2
    open_macrofile_string_dict['python'] = """
            if os.path.exists('{0}'):
                pytex.macrofile = io.open(os.path.join('{0}', '{1}.pytxmcr'), 'w', encoding='{2}')
            else:
                pytex.macrofile = io.open('{1}.pytxmcr', 'w', encoding='{2}')
            """
    #\\ End Python 2
    #// Python 3
    #open_macrofile_string_dict['python'] = """
    #        if os.path.exists('{0}'):
    #            pytex.macrofile = open(os.path.join('{0}', '{1}.pytxmcr'), 'w', encoding='{2}')
    #        else:
    #            pytex.macrofile = open('{1}.pytxmcr', 'w', encoding='{2}')
    #        """
    #\\ End Python 3
    
    close_macrofile_string_dict['python'] = 'pytex.macrofile.close()\n'
    
    cleanup_string_dict['python'] = 'pytex._cleanup()\n'
    
    set_workingdir_string_dict['python'] = """
            if os.path.exists('{0}'):
                os.chdir('{0}')
            """
    
    inline_string_dict['python'] = 'pytex._print_via_macro({0})\n'
    
    encoding_string_dict['python'] = '# -*- coding: {0} -*-\n'
    
    
    def _init_strings(self):
        '''
        Assign strings used for creating individual scripts, cleaning up 
        unneeded leading indentation in the process.
        
        Removing leading indentation is necessary because we want to indent 
        the triple-quoted strings so that they look better, but don't need 
        the indentation in the actual code files.  All strings are dedented.
        '''
        self.utils_string = textwrap.dedent(self.utils_string_dict[self.language])
        self.inputs_string_const = textwrap.dedent(self.inputs_string_const_dict[self.language])
        self.inputs_string_var = textwrap.dedent(self.inputs_string_var_dict[self.language])
        self.encode_stdout_string = textwrap.dedent(self.encode_stdout_string_dict[self.language])
        self.open_macrofile_string = textwrap.dedent(self.open_macrofile_string_dict[self.language])
        self.close_macrofile_string = textwrap.dedent(self.close_macrofile_string_dict[self.language])
        self.cleanup_string = textwrap.dedent(self.cleanup_string_dict[self.language])
        self.set_workingdir_string = textwrap.dedent(self.set_workingdir_string_dict[self.language])
        self.inline_string = textwrap.dedent(self.inline_string_dict[self.language])
        self.encoding_string = textwrap.dedent(self.encoding_string_dict[self.language])
    
    def set_encoding_string(self, encoding):
        '''
        Set the encoding string at the beginning of the script.
        '''
        return self.encoding_string.format(encoding)
    
    def set_stdout_encoding(self, encoding):
        '''
        Set the encoding for stdout, based on the file to which it is 
        redirected.
        '''
        return self.encode_stdout_string.format(encoding)
    
    def set_inputs_const(self, inputtype, inputsession, inputgroup):
        '''
        Format an inputs_string_const for use.
        '''
        return self.inputs_string_const.format(inputtype, inputsession, inputgroup)
        
    def set_inputs_var(self, inputinstance, inputcommand, inputcontext, inputline):
        '''
        Format an inputs_string_var for use.
        '''
        return self.inputs_string_var.format(inputinstance, inputcommand, inputcontext, inputline)
    
    def open_macrofile(self, outputdir, jobname, encoding):
        '''
        Create code that will open a file in which LateX macros containing 
        outputted content are saved.
        '''
        return self.open_macrofile_string.format(outputdir, jobname, encoding)
    
    def close_macrofile(self):
        '''
        Create code that will close the macro file.
        '''
        return self.close_macrofile_string
    
    def cleanup(self):
        '''
        Create code that will close the macro file.
        '''
        return self.cleanup_string

    def set_workingdir(self, workingdir):
        '''
        Set the working directory.
        '''
        return self.set_workingdir_string.format(workingdir)
    
    def inline(self, codeline):
        '''
        Create code that will save content via a macro.
        '''
        return self.inline_string.format(codeline.rstrip('\r\n'))


# Create a dictionary of command and environment families
#
# Create the py, sympy, and pylab families
# Families must always define default_code, but never custom_code_*;
# custome_code_* should only contain code from the user.

typedict = dict()


typedict['py'] = Codetype(
    language = 'python',
    extension = 'py',
    command = 'python',
    command_options = [],
    shebang = '#!/usr/bin/env python',
    default_code = ['import os', 
                    'import sys', 
                    'import codecs'],
    utils_code = [])


typedict['sympy'] = copy.deepcopy(typedict['py'])
typedict['sympy'].utils_code.extend(["pytex.set_formatter('sympy_latex')"])
typedict['sympy'].default_code.extend(['from sympy import *'])


typedict['pylab'] = copy.deepcopy(typedict['py'])
typedict['pylab'].default_code.extend(['from pylab import *'])


def set_utils_location(script_path):
    '''
    Update the utils_code in each family in the typedict with the location of 
    the utilities scripts
    '''
    for eachtype in typedict:
        typedict[eachtype].utils_code.insert(0, typedict[eachtype].utils_string.format(script_path))


#// Python 2
# Import io so that files can be written with encoding via io.open().
#
# Make Python scripts import from __future__ most features that are relevant.
# We DO NOT automatically import unicode_literals, because it can 
# produce problems with some packages for Python 2 (for example, SymPy), 
# especially when isinstance() is used for type checking with str rather than
# basestring.  Given the acceptance of PEP 414 
# (http://www.python.org/dev/peps/pep-0414/) for Python 3.3+, the need to 
# use unicode_literals is perhaps somewhat lessened.
def update_default_code2(pyfuture):
    for codetype in typedict:
        if typedict[codetype].language == 'python':
            typedict[codetype].default_code.append('import io')
            if pyfuture in ('all', 'default'):
                typedict[codetype].default_code.insert(0, 'from __future__ import absolute_import')
                typedict[codetype].default_code.insert(0, 'from __future__ import division')
                typedict[codetype].default_code.insert(0, 'from __future__ import print_function')
            if pyfuture == 'all':
                typedict[codetype].default_code.insert(0, 'from __future__ import unicode_literals')
#\\ End Python 2

