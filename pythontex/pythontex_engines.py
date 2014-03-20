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



Copyright (c) 2012-2014, Geoffrey M. Poore
All rights reserved.
Licensed under the BSD 3-Clause License:
    http://www.opensource.org/licenses/BSD-3-Clause

'''

# Imports
import os
import sys
import textwrap
from hashlib import sha1
from collections import OrderedDict, namedtuple


interpreter_dict = {k:k for k in ('python', 'ruby', 'julia', 'octave')}
# The {file} field needs to be replaced by itself, since the actual 
# substitution of the real file can only be done at runtime, whereas the
# substitution for the interpreter should be done when the engine is 
# initialized.
interpreter_dict['file'] = '{file}'
interpreter_dict['File'] = '{File}'


engine_dict = {}


CodeIndex = namedtuple('CodeIndex', ['input_file', 'command', 
                                     'line_int', 'lines_total', 
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
        # Perform some additional formatting on some strings.
        self.extension = self.extension.lstrip('.')
        self.template = self._dedent(self.template)
        self.wrapper = self._dedent(self.wrapper)
        # Make sure formatter string ends with a newline
        if not self.formatter.endswith('\n'):
            self.formatter = self.formatter + '\n'
        
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
            linenumbers = 'line {number}'
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
        linenumbers = [l.replace('{number}', r'(\d+)') for l in linenumbers]
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
        # The `interpreter_dict` has entries that allow `{file}` and
        # `{outputdir}` fields to be replaced with themselves
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
            raise ValueError('Template for ' + self.name + ' is missing {body}')
        
        # Add beginning to script
        if os.path.isabs(os.path.expanduser(os.path.normcase(workingdir))):
            workingdir_full = workingdir
        else:
            workingdir_full = os.path.join(os.getcwd(), workingdir).replace('\\', '/')
        script_begin = script_begin.format(encoding=encoding, future=future, 
                                           utilspath=utilspath, workingdir=workingdir,
                                           Workingdir=workingdir_full,
                                           extend=self.extend,
                                           family=code_list[0].family,
                                           session=code_list[0].session,
                                           restart=code_list[0].restart,
                                           dependencies_delim='=>PYTHONTEX:DEPENDENCIES#',
                                           created_delim='=>PYTHONTEX:CREATED#')
        script.append(script_begin)
        lines_total += script_begin.count('\n')
        
        # Prep wrapper
        try:
            wrapper_begin, wrapper_end = self.wrapper.split('{code}')
        except:
            raise ValueError('Wrapper for ' + self.name + ' is missing {code}')
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
        stdoutdelim = '=>PYTHONTEX:STDOUT#{instance}#{command}#'
        stderrdelim = '=>PYTHONTEX:STDERR#{instance}#{command}#'
        wrapper_begin = wrapper_begin.replace('{stdoutdelim}', stdoutdelim).replace('{stderrdelim}', stderrdelim)
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
            script.append(wrapper_begin.format(command=c.command,
                                               context=c.context,
                                               args=c.args_run,
                                               instance=c.instance,
                                               line=c.line))
            
            # Actual code
            lines_input = c.code.count('\n')
            code_index[c.instance] = CodeIndex(c.input_file, c.command, c.line_int, lines_total, lines_user, lines_input, inline_count)
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
            script.append(wrapper_begin.format(command=c.command,
                                               context=c.context,
                                               args=c.args_run,
                                               instance=c.instance,
                                               line=c.line))
            
            # Actual code
            lines_input = c.code.count('\n')
            code_index[c.instance] = CodeIndex(c.input_file, c.command, c.line_int, lines_total, lines_user, lines_input, inline_count)
            if c.command == 'i':
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
            script.append(wrapper_begin.format(command=c.command,
                                               context=c.context,
                                               args=c.args_run,
                                               instance=c.instance,
                                               line=c.line))
            
            # Actual code
            lines_input = c.code.count('\n')
            code_index[c.instance] = CodeIndex(c.input_file, c.command, c.line_int, lines_total, lines_user, lines_input, inline_count)
            script.append(c.code)
            if c.is_inline:
                inline_count += 1
            lines_total += lines_input
            lines_user += lines_input
            
            # Wrapper after
            script.append(wrapper_end)
            lines_total += wrapper_end_offset
        
        # Finish script
        script.append(script_end.format(dependencies_delim='=>PYTHONTEX:DEPENDENCIES#', created_delim='=>PYTHONTEX:CREATED#'))
        
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
    # -*- coding: {encoding} -*-
    
    {future}
    
    import os
    import sys
    import codecs
    
    if sys.version_info[0] == 2:
        sys.stdout = codecs.getwriter('{encoding}')(sys.stdout, 'strict')
        sys.stderr = codecs.getwriter('{encoding}')(sys.stderr, 'strict')
    else:
        sys.stdout = codecs.getwriter('{encoding}')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('{encoding}')(sys.stderr.buffer, 'strict')
    
    if '{utilspath}' and '{utilspath}' not in sys.path:
        sys.path.append('{utilspath}')    
    from pythontex_utils import PythonTeXUtils
    pytex = PythonTeXUtils()
    
    pytex.docdir = os.getcwd()
    if os.path.isdir('{workingdir}'):
        os.chdir('{workingdir}')
        if os.getcwd() not in sys.path:
            sys.path.append(os.getcwd())
    else:
        if len(sys.argv) < 2 or sys.argv[1] != '--manual':
            sys.exit('Cannot find directory {workingdir}')
    if pytex.docdir not in sys.path:
        sys.path.append(pytex.docdir)
    
    {extend}
    
    pytex.id = '{family}_{session}_{restart}'
    pytex.family = '{family}'
    pytex.session = '{session}'
    pytex.restart = '{restart}'
    
    {body}

    pytex.cleanup()
    '''

python_wrapper = '''
    pytex.command = '{command}'
    pytex.set_context('{context}')
    pytex.args = '{args}'
    pytex.instance = '{instance}'
    pytex.line = '{line}'
    
    print('{stdoutdelim}')
    sys.stderr.write('{stderrdelim}\\n')
    pytex.before()
    
    {code}
    
    pytex.after()
    '''


CodeEngine('python', 'python', '.py', '{python} {file}.py',
              python_template, python_wrapper, 'print(pytex.formatter({code}))',
              'Error:', 'Warning:', ['line {number}', ':{number}:'])

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
    # -*- coding: {encoding} -*-
    
    $stdout.set_encoding('{encoding}')
    $stderr.set_encoding('{encoding}')
    
    class RubyTeXUtils
        attr_accessor :id, :family, :session, :restart, 
                :command, :context, :args, 
                :instance, :line, :dependencies, :created,
                :docdir, :_context_raw
        def initialize
            @dependencies = Array.new
            @created = Array.new
            @_context_raw = nil
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
        def set_context(expr)
            if expr != "" and expr != @_context_raw
                @context = expr.split(',').map{{|x| x1,x2 = x.split('='); {{x1.strip() => x2.strip()}}}}.reduce(:merge)
                @_context_raw = expr
            end
        end
        def pt_to_in(expr)
            if expr.is_a?String
                if expr.end_with?'pt'
                    expr = expr[0..-3]
                end
                return expr.to_f/72.27
            else
                return expr/72.27
            end
        end
        def pt_to_cm(expr)
            return pt_to_in(expr)*2.54
        end
        def pt_to_mm(expr)
            return pt_to_in(expr)*25.4
        end
        def pt_to_bp(expr)
            return pt_to_in(expr)*72
        end
        def cleanup
            puts '{dependencies_delim}'
            if @dependencies
                @dependencies.each {{ |x| puts x }}
            end
            puts '{created_delim}'
            if @created
                @created.each {{ |x| puts x }}
            end
        end        
    end
            
    rbtex = RubyTeXUtils.new
    
    rbtex.docdir = Dir.pwd
    if File.directory?('{workingdir}')
        Dir.chdir('{workingdir}')
        $LOAD_PATH.push(Dir.pwd) unless $LOAD_PATH.include?(Dir.pwd)
    elsif ARGV[0] != '--manual'
        abort('Cannot change to directory {workingdir}')
    end
    $LOAD_PATH.push(rbtex.docdir) unless $LOAD_PATH.include?(rbtex.docdir)
    
    {extend}
    
    rbtex.id = '{family}_{session}_{restart}'
    rbtex.family = '{family}'
    rbtex.session = '{session}'
    rbtex.restart = '{restart}'
    
    {body}

    rbtex.cleanup
    '''

ruby_wrapper = '''
    rbtex.command = '{command}'
    rbtex.set_context('{context}')
    rbtex.args = '{args}'
    rbtex.instance = '{instance}'
    rbtex.line = '{line}'
    
    puts '{stdoutdelim}'
    $stderr.puts '{stderrdelim}'
    rbtex.before
    
    {code}
    
    rbtex.after
    '''

CodeEngine('ruby', 'ruby', '.rb', '{ruby} {file}.rb', ruby_template, 
              ruby_wrapper, 'puts rbtex.formatter({code})', 
              ['Error)', '(Errno', 'error'], 'warning:', ':{number}:')

SubCodeEngine('ruby', 'rb')




julia_template = '''
    # -*- coding: UTF-8 -*-
    
    # Currently, Julia only supports UTF-8
    # So can't set stdout and stderr encoding
    
    type JuliaTeXUtils
        id::String
        family::String
        session::String
        restart::String
        command::String
        context::Dict
        args::String
        instance::String
        line::String
        
        _dependencies::Array{{String}}
        _created::Array{{String}}
        docdir::String
        _context_raw::String
        
        formatter::Function
        before::Function
        after::Function
        add_dependencies::Function
        add_created::Function
        set_context::Function
        pt_to_in::Function
        pt_to_cm::Function
        pt_to_mm::Function
        pt_to_bp::Function
        cleanup::Function
        
        self::JuliaTeXUtils
        
        function JuliaTeXUtils()
            self = new()
            self.self = self
            self._dependencies = Array(String, 0)
            self._created = Array(String, 0)
            self._context_raw = ""
            
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
            
            function set_context(expr)
                if expr != "" && expr != self._context_raw
                    self.context = {{strip(x[1]) => strip(x[2]) for x in map(x -> split(x, "="), split(expr, ","))}}
                    self._context_raw = expr
                end
            end
            self.set_context = set_context
            
            function pt_to_in(expr)
                if isa(expr, String)
                    if sizeof(expr) > 2 && expr[end-1:end] == "pt"
                        expr = expr[1:end-2]
                    end
                    return float(expr)/72.27
                else
                    return expr/72.27
                end
            end
            self.pt_to_in = pt_to_in
            
            function pt_to_cm(expr)
                return self.pt_to_in(expr)*2.54
            end
            self.pt_to_cm = pt_to_cm
            
            function pt_to_mm(expr)
                return self.pt_to_in(expr)*25.4
            end
            self.pt_to_mm = pt_to_mm
            
            function pt_to_bp(expr)
                return self.pt_to_in(expr)*72
            end
            self.pt_to_bp = pt_to_bp
                        
            function cleanup()
                println("{dependencies_delim}")
                for f in self._dependencies
                    println(f)
                end
                println("{created_delim}")
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
    println(jltex.docdir)
    try
        cd("{workingdir}")
        if !(in(pwd(), LOAD_PATH))
            push!(LOAD_PATH, pwd())
        end
    catch
        if !(length(ARGS) > 0 && ARGS[1] == "--manual")
            error("Could not find directory {workingdir}")
        end
    end
    if !(in(jltex.docdir, LOAD_PATH))
        push!(LOAD_PATH, jltex.docdir)
    end 
    
    {extend}
    
    jltex.id = "{family}_{session}_{restart}"
    jltex.family = "{family}"
    jltex.session = "{session}"
    jltex.restart = "{restart}"
    
    {body}
    
    jltex.cleanup()
    '''

julia_wrapper = '''
    jltex.command = "{command}"
    jltex.set_context("{context}")
    jltex.args = "{args}"
    jltex.instance = "{instance}"   
    jltex.line = "{line}"
    
    println("{stdoutdelim}")
    write(STDERR, "{stderrdelim}\\n")
    jltex.before()   
    
    {code}
    
    jltex.after()
    '''

CodeEngine('julia', 'julia', '.jl', '{julia} "{file}.jl"', julia_template, 
              julia_wrapper, 'println(jltex.formatter({code}))', 
              'ERROR:', 'WARNING:', ':{number}', True)

SubCodeEngine('julia', 'jl')


octave_template = '''
    cd '{Workingdir}';
    
    {extend}
    
    global octavetex = struct();
    octavetex.dependencies = {{}};
    octavetex.created = {{}};
    octavetex._context_raw = '';
    
    function octavetex_formatter(argin)
        disp(argin);
    end
    
    function octavetex_before()
    end
    
    function octavetex_after()
    end
    
    function octavetex_add_dependencies(varargin)
        global octavetex;
        for i = 1:length(varargin)
            octavetex.dependencies{{end+1}} = varargin{{i}};
        end
    end
    
    function octavetex_add_created(varargin)
        global octavetex;
        for i = 1:length(varargin)
            octavetex.created{{end+1}} = varargin{{i}};
        end
    end
    
    function octavetex_set_context(argin)
        global octavetex;
        if ~strcmp(argin, octavetex._context_raw)
            octavetex._context_raw = argin;
            hash = struct;
            argin_kv = strsplit(argin, ',');
            for i = 1:length(argin_kv)
                kv = strsplit(argin_kv{{i}}, '=');
                k = strtrim(kv{{1}});
                v = strtrim(kv{{2}});
                hash = setfield(hash, k, v);
            end
            octavetex.context = hash;
        end
    end
    
    function out = octavetex_pt_to_in(argin)
        if ischar(argin)
            if length(argin) > 2 && argin(end-1:end) == 'pt'
                out = str2num(argin(1:end-2))/72.27;
            else
                out = str2num(argin)/72.27;
            end
        else
            out = argin/72.27;
        end
    end
    
    function out = octavetex_pt_to_cm(argin)
        out = octavetex_pt_to_in(argin)*2.54;
    end
    
    function out = octavetex_pt_to_mm(argin)
        out = octavetex_pt_to_in(argin)*25.4;
    end
    
    function out = octavetex_pt_to_bp(argin)
        out = octavetex_pt_to_in(argin)*72;
    end
    
    function octavetex_cleanup()
        global octavetex;
        fprintf(strcat('{dependencies_delim}', "\\n"));
        for i = 1:length(octavetex.dependencies)
            fprintf(strcat(octavetex.dependencies{{i}}, "\\n"));
        end
        fprintf(strcat('{created_delim}', "\\n"));
        for i = 1:length(octavetex.created)
            fprintf(strcat(octavetex.created{{i}}, "\\n"));
        end        
    end
    
    octavetex.id = '{family}_{session}_{restart}';
    octavetex.family = '{family}';
    octavetex.session = '{session}';
    octavetex.restart = '{restart}';
    
    {body}

    octavetex_cleanup()    
    '''

octave_wrapper = '''
    octavetex.command = '{command}';
    octavetex_set_context('{context}');
    octavetex.args = '{args}';
    octavetex.instance = '{instance}';
    octavetex.line = '{line}';
    
    octavetex_before()   
    
    fprintf(strcat('{stdoutdelim}', "\\n"));
    fprintf(stderr, strcat('{stderrdelim}', "\\n"));
    {code}
    
    octavetex_after()
    '''

CodeEngine('octave', 'octave', '.m',
           '{octave} -q "{File}.m"', 
           octave_template, octave_wrapper, 'disp({code})',
           'error', 'warning', 'line {number}')
