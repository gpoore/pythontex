# -*- coding: utf-8 -*-
'''
PythonTeX code engines.

Provides a class for managing the different languages/types of code
that may be executed.  A class instance is created for each language/type of
code.  The class provides a method for assembling the scripts that are 
executed, combining user code with templates.  It also creates the records 
needed to synchronize `stderr` with the document.

Each instance of the class is automatically added to the `engines_dict` upon
creation.  Instances are typically accessed via this dictionary.

The class is called `*CodeEngine` by analogy with a template engine, since it
combines user text (code) with existing templates to produce an output
document (script for execution).



Copyright (c) 2012-2013, Geoffrey M. Poore
All rights reserved.
Licensed under the BSD 3-Clause License:
    http://www.opensource.org/licenses/BSD-3-Clause

'''

# Imports
import sys
import textwrap
from hashlib import sha1
from collections import OrderedDict, namedtuple


interpreter_dict = {k:k for k in ('python', 'ruby', 'julia')}
# The {file} field needs to be replaced by itself, since the actual 
# substitution of the real file can only be done at runtime, whereas the
# substitution for the interpreter should be done when the engine is 
# initialized.
interpreter_dict['file'] = '{file}'


engine_dict = {}


CodeIndex = namedtuple('CodeIndex', ['input_file', 'input_command', 
                                     'input_line_int', 'lines_total', 
                                     'lines_user', 'lines_input',
                                     'inline_count'])


class CodeEngine(object):
    '''
    The base class that is used for defining language engines.  Each command 
    and environment family is based on an engine.
    
    The class assembles the individual scripts that PythonTeX executes, using
    templates and user code.  It also creates the records needed for 
    synchronizing `stderr` with the document.
    '''
    def __init__(self, name, language, extension, command, template, wrapper, 
                 formatter, errors=None, warnings=None,
                 linenumbers=None, lookbehind=False, 
                 console=False, startup=None, created=None):

        # Save raw arguments so that they may be reused by subtypes
        self._rawargs = (name, language, extension, command, template, wrapper, 
                         formatter, errors, warnings,
                         linenumbers, lookbehind, console, startup, created)
        
        # Type check all strings, and make sure everything is Unicode
        if sys.version_info[0] == 2:
            if (not isinstance(name, basestring) or 
                    not isinstance(language, basestring) or 
                    not isinstance(extension, basestring) or 
                    not isinstance(command, basestring) or 
                    not isinstance(template, basestring) or
                    not isinstance(wrapper, basestring) or
                    not isinstance(formatter, basestring)):
                raise TypeError('CodeEngine needs string in initialization')
            self.name = unicode(name)
            self.language = unicode(language)
            self.extension = unicode(extension)
            self.command = unicode(command)
            self.template = unicode(template)
            self.wrapper = unicode(wrapper)
            self.formatter = unicode(formatter)
        else:
            if (not isinstance(name, str) or 
                    not isinstance(language, str) or 
                    not isinstance(extension, str) or 
                    not isinstance(command, str) or 
                    not isinstance(template, str) or
                    not isinstance(wrapper, str) or
                    not isinstance(formatter, str)):    
                raise TypeError('CodeEngine needs string in initialization')
            self.name = name
            self.language = language
            self.extension = extension
            self.command = command
            self.template = template
            self.wrapper = wrapper
            self.formatter = formatter
        # Perform some additional formatting on some strings.  Dedent.
        # Change from {{ }} tags for replacement fields to { } tags that
        # are compatible with Python's string format() method, which is much
        # more efficient than a template engine.
        self.extension = self.extension.lstrip('.')
        self.command = self._dejinja(self.command)
        self.template = self._dedent(self._dejinja(self.template))
        self.wrapper = self._dedent(self._dejinja(self.wrapper))
        # Make sure formatter string ends with a newline
        if self.formatter.endswith('\n'):
            self.formatter = self._dejinja(self.formatter)
        else:
            self.formatter = self._dejinja(self.formatter) + '\n'
        
        # Type check errors, warnings, and linenumbers
        if errors is None:
            errors = []
        else:
            if sys.version_info[0] == 2:
                if isinstance(errors, basestring):
                    errors = [errors]
                elif not isinstance(errors, list) and not isinstance(errors, tuple):
                    raise TypeError('CodeEngine needs "errors" to be a string, list, or tuple')
                for e in errors:
                    if not isinstance(e, basestring):
                        raise TypeError('CodeEngine needs "errors" to contain strings')
                errors = [unicode(e) for e in errors]
            else:
                if isinstance(errors, str):
                    errors = [errors]
                elif not isinstance(errors, list) and not isinstance(errors, tuple):
                    raise TypeError('CodeEngine needs "errors" to be a string, list, or tuple')
                for e in errors:
                    if not isinstance(e, str):
                        raise TypeError('CodeEngine needs "errors" to contain strings')
            self.errors = errors
        if warnings is None:
            warnings = []
        else:
            if sys.version_info[0] == 2:
                if isinstance(warnings, basestring):
                    warnings = [warnings]
                elif not isinstance(warnings, list) and not isinstance(warnings, tuple):
                    raise TypeError('CodeEngine needs "warnings" to be a string, list, or tuple')
                for w in warnings:
                    if not isinstance(w, basestring):
                        raise TypeError('CodeEngine needs "warnings" to contain strings')
                warnings = [unicode(w) for w in warnings]
            else:
                if isinstance(warnings, str):
                    warnings = [warnings]
                elif not isinstance(warnings, list) and not isinstance(warnings, tuple):
                    raise TypeError('CodeEngine needs "warnings" to be a string, list, or tuple')
                for w in warnings:
                    if not isinstance(w, str):
                        raise TypeError('CodeEngine needs "warnings" to contain strings')
            self.warnings = warnings
        if linenumbers is None:
            linenumbers = 'line {{number}}'
        if sys.version_info[0] == 2:
            if isinstance(linenumbers, basestring):
                linenumbers = [linenumbers]
            elif not isinstance(linenumbers, list) and not isinstance(linenumbers, tuple):
                raise TypeError('CodeEngine needs "linenumbers" to be a string, list, or tuple')
            for l in linenumbers:
                if not isinstance(l, basestring):
                    raise TypeError('CodeEngine needs "linenumbers" to contain strings')
            linenumbers = [unicode(l) for l in linenumbers]
        else:
            if isinstance(linenumbers, str):
                linenumbers = [linenumbers]
            elif not isinstance(linenumbers, list) and not isinstance(linenumbers, tuple):
                raise TypeError('CodeEngine needs "linenumbers" to be a string, list, or tuple')
            for l in linenumbers:
                if not isinstance(l, str):
                    raise TypeError('CodeEngine needs "linenumbers" to contain strings')
        # Need to replace tags
        linenumbers = [l.replace('{{number}}', r'(\d+)') for l in linenumbers]
        self.linenumbers = linenumbers

        # Type check lookbehind
        if not isinstance(lookbehind, bool):
            raise TypeError('CodeEngine needs "lookbehind" to be bool')
        self.lookbehind = lookbehind
        
        # Type check console
        if not isinstance(console, bool):
            raise TypeError('CodeEngine needs "console" to be bool')
        self.console = console
        
        # Type check startup
        if startup is None:
            startup = ''
        if startup and not self.console:
            raise TypeError('PythonTeX can only use "startup" for console types')
        else:
            if sys.version_info[0] == 2:
                if isinstance(startup, basestring):
                    startup = unicode(startup)
                else:
                    raise TypeError('CodeEngine needs "startup" to be a string')
            else:
                if not isinstance(startup, str):
                    raise TypeError('CodeEngine needs "startup" to be a string')
            if not startup.endswith('\n'):
                startup += '\n'
        self.startup = self._dedent(startup)
        
        # Type check created; make sure it is an iterable and contains Unicode
        if created is None:
            created = []
        else:
            if sys.version_info[0] == 2:
                if isinstance(created, basestring):
                    created = [created]
                elif not isinstance(created, list) and not isinstance(created, tuple):
                    raise TypeError('CodeEngine needs "created" to be a string, list, or tuple')
                for f in created:
                    if not isinstance(f, basestring):
                        raise TypeError('CodeEngine "created" to contain strings')
                created = [unicode(f) for f in created]
            else:
                if isinstance(created, str):
                    created = [created]
                elif not isinstance(created, list) and not isinstance(created, tuple):
                    raise TypeError('CodeEngine needs "created" to be a string, list, or tuple')
                for f in created:
                    if not isinstance(f, str):
                        raise TypeError('CodeEngine needs "created" to contain strings')
        self.created = created
        
        # The base PythonTeX type does not support extend; it is used in 
        # subtyping.  But a dummy extend is needed to fill the extend field
        # in templates, if it is provided.
        self.extend = ''
        
        # Create dummy variables for console
        self.banner = ''
        self.filename = ''
        
        # Each type needs to add itself to a dict, for later access by name
        self._register()
    
    def _dedent(self, s):
        '''
        Dedent and strip leading newlines
        '''
        s = textwrap.dedent(s)
        while s.startswith('\n'):
            s = s[1:]
        return s
    
    def _dejinja(self, s):
        '''
        Switch all `{{ }}` tags into `{ }`, and all normal braces `{ }` into 
        `{{ }}`, so that Python's string format() method may be used.  Also 
        strip any whitespace surrounding the field name.
        
        This will fail if literal `{{` and `}}` are needed.  If those are 
        ever needed, then options for custom tags will be needed.
        '''
        lst = [t.replace('{', '{{') for t in s.split('{{')]
        for n in range(1, len(lst)):
            lst[n] = lst[n].lstrip(' ')
        s = '{'.join(lst)
        lst = [t.replace('}', '}}') for t in s.split('}}')]
        for n in range(0, len(lst)-1):
            lst[n] = lst[n].rstrip(' ')
        s = '}'.join(lst)
        return s
        
    def _register(self):
        '''
        Add instance to a dict for later access by name
        '''
        engine_dict[self.name] = self
        
    def customize(self, **kwargs):
        '''
        Customize the template on the fly.
        
        This provides customization based on command line arguments 
        (`--interpreter`) and customization from the TeX side (imports from
        `__future__`).  Ideally, this function should be restricted to this 
        and similar cases.  The custom code command and environment are 
        insufficient for such cases, because the command is at a level above
        that of code and because of the requirement that imports from 
        `__future__` be at the very beginning of a script.
        '''
        # Take care of `--interpreter`
        self.command = self.command.format(**interpreter_dict)
        # Take care of `__future__`
        if self.language.startswith('python'):
            if sys.version_info[0] == 2 and 'pyfuture' in kwargs:
                pyfuture = kwargs['pyfuture']
                future_imports = None
                if pyfuture == 'all':
                    future_imports = '''
                            from __future__ import absolute_import
                            from __future__ import division
                            from __future__ import print_function
                            from __future__ import unicode_literals
                            {future}'''
                elif pyfuture == 'default':
                    future_imports = '''
                            from __future__ import absolute_import
                            from __future__ import division
                            from __future__ import print_function
                            {future}'''
                if future_imports is not None:
                    future_imports = self._dedent(future_imports)
                    self.template = self.template.replace('{future}', future_imports)
            if self.console:
                if sys.version_info[0] == 2 and 'pyconfuture' in kwargs:
                    pyconfuture = kwargs['pyconfuture']
                    future_imports = None
                    if pyconfuture == 'all':
                        future_imports = '''
                                from __future__ import absolute_import
                                from __future__ import division
                                from __future__ import print_function
                                from __future__ import unicode_literals
                                '''
                    elif pyconfuture == 'default':
                        future_imports = '''
                                from __future__ import absolute_import
                                from __future__ import division
                                from __future__ import print_function
                                '''
                    if future_imports is not None:
                        future_imports = self._dedent(future_imports)
                        self.startup = future_imports + self.startup
                if 'pyconbanner' in kwargs:
                    self.banner = kwargs['pyconbanner']
                if 'pyconfilename' in kwargs:
                    self.filename = kwargs['pyconfilename']

    _hash = None
            
    def get_hash(self):
        '''
        Return a hash of all vital type information (template, etc.).  Create
        the hash if it doesn't exist, otherwise return a stored hash.
        '''
        # This file is encoded in UTF-8, so everything can be encoded in UTF-8.
        # It's not important that this encoding be the same as that given by
        # the user, since a unique hash is all that's needed.
        if self._hash is None:
            hasher = sha1()
            hasher.update(self.command.encode('utf8'))
            hasher.update(self.template.encode('utf8'))
            hasher.update(self.wrapper.encode('utf8'))
            hasher.update(self.formatter.encode('utf8'))
            if self.console:
                hasher.update(self.startup.encode('utf8'))
                hasher.update(self.banner.encode('utf8'))
                hasher.update(self.filename.encode('utf8'))
            self._hash = hasher.hexdigest()
        return self._hash
    
    def _process_future(self, code_list):
        '''
        Go through a given list of code and extract all imports from 
        `__future__`, so that they can be relocated to the beginning of the 
        script.
        
        The approach isn't foolproof and doesn't support compound statements.
        '''
        done = False
        future_imports = []
        for n, c in enumerate(code_list):
            in_triplequote = False
            changed = False
            code = c.code.split('\n')
            for l, line in enumerate(code):
                # Detect __future__ imports
                if (line.startswith('from __future__') or 
                        line.startswith('import __future__') and 
                        not in_triplequote):
                    changed = True
                    if ';' in line:
                        raise ValueError('Imports from __future__ should be simple statements; semicolons are not supported')
                    else:
                        future_imports.append(line)
                        code[l] = ''
                # Ignore comments, empty lines, and lines with complete docstrings
                elif (line.startswith('\n') or line.startswith('#') or 
                        line.isspace() or
                        ('"""' in line and line.count('"""')%2 == 0) or 
                        ("'''" in line and line.count("'''")%2 == 0)):
                    pass
                # Detect if entering or leaving a docstring
                elif line.count('"""')%2 == 1 or line.count("'''")%2 == 1:
                    in_triplequote = not in_triplequote
                # Stop looking for future imports as soon as a non-comment, 
                # non-empty, non-docstring, non-future import line is found
                elif not in_triplequote:
                    done = True
                    break
            if changed:
                code_list[n].code = '\n'.join(code)
            if done:
                break
        if future_imports:
            return '\n'.join(future_imports)
        else:
            return ''
            
    def _get_future(self, cc_list_begin, code_list):
        '''
        Process custom code and user code for imports from `__future__`
        '''
        cc_future = self._process_future(cc_list_begin)
        code_future = self._process_future(code_list)
        if cc_future and code_future:
            return cc_future + '\n' + code_future
        else:
            return cc_future + code_future
    
    def get_script(self, encoding, utilspath, workingdir, 
                   cc_list_begin, code_list, cc_list_end):
        '''
        Assemble the script that will be executed.  In the process, assemble
        an index of line numbers that may be used to correlate script line
        numbers with document line numbers and user code line numbers in the 
        event of errors or warnings.
        '''
        lines_total = 0
        script = []
        code_index = OrderedDict()
        
        # Take care of future
        if self.language.startswith('python'):
            future = self._get_future(cc_list_begin, code_list)
        else:
            future = ''
        
        # Split template into beginning and ending segments
        try:
            script_begin, script_end = self.template.split('{body}')
        except:
            raise ValueError('Template for ' + self.name + ' is missing {{body}}')
        
        # Add beginning to script
        script_begin = script_begin.format(encoding=encoding, future=future, 
                                           utilspath=utilspath, workingdir=workingdir,
                                           extend=self.extend,
                                           input_family=code_list[0].input_family,
                                           input_session=code_list[0].input_session,
                                           input_restart=code_list[0].input_restart,
                                           dependencies_delim='=>PYTHONTEX:DEPENDENCIES#',
                                           created_delim='=>PYTHONTEX:CREATED#')
        script.append(script_begin)
        lines_total += script_begin.count('\n')
        
        # Prep wrapper
        try:
            wrapper_begin, wrapper_end = self.wrapper.split('{code}')
        except:
            raise ValueError('Wrapper for ' + self.name + ' is missing {{code}}')
        if not self.language.startswith('python'):
            # In the event of a syntax error at the end of user code, Ruby
            # (and perhaps others) will use the line number from the NEXT
            # line of code that is non-empty, not from the line of code where
            # the error started.  In these cases, it's important
            # to make sure that the line number is triggered immediately 
            # after user code, so that the line number makes sense.  Hence,
            # we need to strip all whitespace from the part of the wrapper
            # that follows user code.  For symetry, we do the same for both
            # parts of the wrapper.
            wrapper_begin = wrapper_begin.rstrip(' \t\n') + '\n'
            wrapper_end = wrapper_end.lstrip(' \t\n')
        stdout_delim = '=>PYTHONTEX:STDOUT#{input_instance}#{input_command}#'
        stderr_delim = '=>PYTHONTEX:STDERR#{input_instance}#{input_command}#'
        wrapper_begin = wrapper_begin.replace('{stdout_delim}', stdout_delim).replace('{stderr_delim}', stderr_delim)
        wrapper_begin_offset = wrapper_begin.count('\n')
        wrapper_end_offset = wrapper_end.count('\n')
        
        # Take care of custom code
        # Line counters must be reset for cc begin, code, and cc end, since 
        # all three are separate
        lines_user = 0
        inline_count = 0
        for c in cc_list_begin:
            # Wrapper before
            lines_total += wrapper_begin_offset
            script.append(wrapper_begin.format(input_command=c.input_command,
                                               input_context=c.input_context,
                                               input_args=c.input_args_run,
                                               input_instance=c.input_instance,
                                               input_line=c.input_line))
            
            # Actual code
            lines_input = c.code.count('\n')
            code_index[c.input_instance] = CodeIndex(c.input_file, c.input_command, c.input_line_int, lines_total, lines_user, lines_input, inline_count)
            script.append(c.code)
            if c.is_inline:
                inline_count += 1
            lines_total += lines_input
            lines_user += lines_input
            
            # Wrapper after
            script.append(wrapper_end)
            lines_total += wrapper_end_offset
        
        # Take care of user code
        lines_user = 0
        inline_count = 0
        for c in code_list:
            # Wrapper before
            lines_total += wrapper_begin_offset
            script.append(wrapper_begin.format(input_command=c.input_command,
                                               input_context=c.input_context,
                                               input_args=c.input_args_run,
                                               input_instance=c.input_instance,
                                               input_line=c.input_line))
            
            # Actual code
            lines_input = c.code.count('\n')
            code_index[c.input_instance] = CodeIndex(c.input_file, c.input_command, c.input_line_int, lines_total, lines_user, lines_input, inline_count)
            if c.input_command == 'i':
                script.append(self.formatter.format(code=c.code.rstrip('\n')))
                inline_count += 1
            else:
                script.append(c.code)
            lines_total += lines_input
            lines_user += lines_input                
            
            # Wrapper after
            script.append(wrapper_end)
            lines_total += wrapper_end_offset
        
        # Take care of custom code
        lines_user = 0
        inline_count = 0
        for c in cc_list_end:
            # Wrapper before
            lines_total += wrapper_begin_offset
            script.append(wrapper_begin.format(input_command=c.input_command,
                                               input_context=c.input_context,
                                               input_args=c.input_args_run,
                                               input_instance=c.input_instance,
                                               input_line=c.input_line))
            
            # Actual code
            lines_input = c.code.count('\n')
            code_index[c.input_instance] = CodeIndex(c.input_file, c.input_command, c.input_line_int, lines_total, lines_user, lines_input, inline_count)
            script.append(c.code)
            if c.is_inline:
                inline_count += 1
            lines_total += lines_input
            lines_user += lines_input
            
            # Wrapper after
            script.append(wrapper_end)
            lines_total += wrapper_end_offset
        
        # Finish script
        script.append(script_end)
        
        return script, code_index


        

class SubCodeEngine(CodeEngine):
    '''
    Create Engine instances that inherit from existing instances.
    '''
    def __init__(self, base, name, language=None, extension=None, command=None, 
                 template=None, wrapper=None, formatter=None, errors=None,
                 warnings=None, linenumbers=None, lookbehind=False,
                 console=None, created=None, startup=None, extend=None):
        
        self._rawargs = (name, language, extension, command, template, wrapper, 
                         formatter, errors, warnings,
                         linenumbers, lookbehind, console, startup, created)
                         
        base_rawargs = engine_dict[base]._rawargs
        args = []
        for n, arg in enumerate(self._rawargs):
            if arg is None:
                args.append(base_rawargs[n])
            else:
                args.append(arg)
        
        CodeEngine.__init__(self, *args)
        
        self.extend = engine_dict[base].extend
        
        if extend is not None:
            if sys.version_info[0] == 2:
                if not isinstance(extend, basestring):
                    raise TypeError('PythonTeXSubtype needs a string for "extend"')
                extend = unicode(extend)
            else:
                if not isinstance(extend, str):
                    raise TypeError('PythonTeXSubtype needs a string for "extend"')
            if not extend.endswith('\n'):
                extend = extend + '\n'
            self.extend += self._dedent(extend)




class PythonConsoleEngine(CodeEngine):
    '''
    This uses the Engine class to store information needed for emulating
    Python interactive consoles.
    
    In the current form, it isn't used as a real engine, but rather as a 
    convenient storage class that keeps the treatment of all languages/code 
    types uniform.
    '''
    def __init__(self, name, startup=None):
        CodeEngine.__init__(self, name=name, language='python', 
                            extension='', command='', template='', 
                            wrapper='', formatter='', errors=None, 
                            warnings=None, linenumbers=None, lookbehind=False,
                            console=True, startup=startup, created=None)




python_template = '''
    # -*- coding: {{encoding}} -*-
    
    {{future}}
    
    import os
    import sys
    import codecs
    
    if sys.version_info[0] == 2:
        sys.stdout = codecs.getwriter('{{encoding}}')(sys.stdout, 'strict')
        sys.stderr = codecs.getwriter('{{encoding}}')(sys.stderr, 'strict')
    else:
        sys.stdout = codecs.getwriter('{{encoding}}')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('{{encoding}}')(sys.stderr.buffer, 'strict')
    
    sys.path.append('{{utilspath}}')    
    from pythontex_utils import PythonTeXUtils
    pytex = PythonTeXUtils()
    
    pytex.docdir = os.getcwd()
    if os.path.isdir('{{workingdir}}'):
        os.chdir('{{workingdir}}')
        if os.getcwd() not in sys.path:
            sys.path.append(os.getcwd())
    else:
        if len(sys.argv) < 2 or sys.argv[1] != '--manual':
            sys.exit('Cannot find directory {{workingdir}}')
    if pytex.docdir not in sys.path:
        sys.path.append(pytex.docdir)
    
    {{extend}}
    
    pytex.input_family = '{{input_family}}'
    pytex.input_session = '{{input_session}}'
    pytex.input_restart = '{{input_restart}}'
    
    {{body}}

    pytex.cleanup()
    '''

python_wrapper = '''
    pytex.input_command = '{{input_command}}'
    pytex.input_context = '{{input_context}}'
    pytex.input_args = '{{input_args}}'
    pytex.input_instance = '{{input_instance}}'
    pytex.input_line = '{{input_line}}'
    
    print('{{stdout_delim}}')
    sys.stderr.write('{{stderr_delim}}\\n')
    pytex.before()
    
    {{code}}
    
    pytex.after()
    '''


CodeEngine('python', 'python', '.py', '{{python}} {{file}}.py',
              python_template, python_wrapper, 'print(pytex.formatter({{code}}))',
              'Error:', 'Warning:', ['line {{number}}', ':{{number}}:'])

SubCodeEngine('python', 'py')

SubCodeEngine('python', 'pylab', extend='from pylab import *')

sympy_extend = '''
    from sympy import *
    pytex.set_formatter('sympy_latex')
    '''

SubCodeEngine('python', 'sympy', extend=sympy_extend)




PythonConsoleEngine('pycon')

PythonConsoleEngine('pylabcon', startup='from pylab import *')

PythonConsoleEngine('sympycon', startup='from sympy import *')




ruby_template = '''
    # -*- coding: {{encoding}} -*-
    
    $stdout.set_encoding('{{encoding}}')
    $stderr.set_encoding('{{encoding}}')
    
    class RubyTeXUtils
        attr_accessor :input_family, :input_session, :input_restart, 
                :input_command, :input_context, :input_args, 
                :input_instance, :input_line, :dependencies, :created, :docdir
        def initialize
            @dependencies = Array.new
            @created = Array.new
        end
        def formatter(expr)
            return expr.to_s
        end
        def before
        end
        def after
        end
        def add_dependencies(*expr)
            self.dependencies.push(*expr)
        end
        def add_created(*expr)
            self.created.push(*expr)
        end
        def cleanup
            puts '{{dependencies_delim}}'
            if @dependencies
                @dependencies.each { |x| puts x }
            end
            puts '{{created_delim}}'
            if @created
                @created.each { |x| puts x }
            end
        end        
    end
            
    rbtex = RubyTeXUtils.new
    
    rbtex.docdir = Dir.pwd
    if File.directory?('{{workingdir}}')
        Dir.chdir('{{workingdir}}')
        $LOAD_PATH.push(Dir.pwd) unless $LOAD_PATH.include?(Dir.pwd)
    elsif ARGV[0] != '--manual'
        abort('Cannot change to directory {{workingdir}}')
    end
    $LOAD_PATH.push(rbtex.docdir) unless $LOAD_PATH.include?(rbtex.docdir)
    
    {{extend}}
    
    rbtex.input_family = '{{input_family}}'
    rbtex.input_session = '{{input_session}}'
    rbtex.input_restart = '{{input_restart}}'
    
    {{body}}

    rbtex.cleanup
    '''

ruby_wrapper = '''
    rbtex.input_command = '{{input_command}}'
    rbtex.input_context = '{{input_context}}'
    rbtex.input_args = '{{input_args}}'
    rbtex.input_instance = '{{input_instance}}'
    rbtex.input_line = '{{input_line}}'
    
    puts '{{stdout_delim}}'
    $stderr.puts '{{stderr_delim}}'
    rbtex.before
    
    {{code}}
    
    rbtex.after
    '''

CodeEngine('ruby', 'ruby', '.rb', '{{ruby}} {{file}}.rb', ruby_template, 
              ruby_wrapper, 'puts rbtex.formatter({{code}})', 
              ['Error)', '(Errno', 'error'], 'warning:', ':{{number}}:')

SubCodeEngine('ruby', 'rb')




julia_template = '''
    # -*- coding: UTF-8 -*-
    
    # Currently, Julia only supports UTF-8
    # So can't set stdout and stderr encoding
    
    type JuliaTeXUtils
        input_family::String
        input_session::String
        input_restart::String
        input_command::String
        input_context::String
        input_args::String
        input_instance::String
        input_line::String
        
        _dependencies::Array{String}
        _created::Array{String}
        docdir::String
        
        formatter::Function
        before::Function
        after::Function
        add_dependencies::Function
        add_created::Function
        cleanup::Function
        
        self::JuliaTeXUtils
        
        function JuliaTeXUtils()
            self = new()
            self.self = self
            self._dependencies = Array(String, 0)
            self._created = Array(String, 0)
            
            function formatter(expr)
                string(expr)
            end
            self.formatter = formatter
            
            function null()
            end
            self.before = null
            self.after = null
            
            function add_dependencies(files...)
                for file in files
                    push!(self._dependencies, file)
                end
            end
            self.add_dependencies = add_dependencies
            function add_created(files...)
                for file in files
                    push!(self._created, file)
                end
            end
            self.add_created = add_created
            
            function cleanup()
                println("{{dependencies_delim}}")
                for f in self._dependencies
                    println(f)
                end
                println("{{created_delim}}")
                for f in self._created
                    println(f)
                end
            end
            self.cleanup = cleanup
            
            return self
        end
    end
    
    jltex = JuliaTeXUtils()
    
    jltex.docdir = pwd()
    try
        cd("{{workingdir}}")
        if !(contains(LOAD_PATH, pwd()))
            push!(LOAD_PATH, pwd())
        end
    catch
        if !(length(ARGS) > 0 && ARGS[1] == "--manual")
            error("Could not find directory {{workingdir}}")
        end
    end
    if !(contains(LOAD_PATH, jltex.docdir))
        push!(LOAD_PATH, jltex.docdir)
    end 
    
    {{extend}}
    
    jltex.input_family = "{{input_family}}"
    jltex.input_session = "{{input_session}}"
    jltex.input_restart = "{{input_restart}}"
    
    {{body}}
    
    jltex.cleanup()
    '''

julia_wrapper = '''
    jltex.input_command = "{{input_command}}"
    jltex.input_context = "{{input_context}}"
    jltex.input_args = "{{input_args}}"
    jltex.input_instance = "{{input_instance}}"   
    jltex.input_line = "{{input_line}}"
    
    println("{{stdout_delim}}")
    write(STDERR, "{{stderr_delim}}\\n")
    jltex.before()   
    
    {{code}}
    
    jltex.after()
    '''

CodeEngine('julia', 'julia', '.jl', '{{julia}} {{file}}.jl', julia_template, 
              julia_wrapper, 'println(jltex.formatter({{code}}))', 
              'ERROR:', 'WARNING:', ':{{number}}', True)

SubCodeEngine('julia', 'jl')

