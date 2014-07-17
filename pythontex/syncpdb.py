#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Synchronized Python Debugger (syncpdb)

Provides a wrapper for pdb that synchronizes code line numbers with the line
numbers of a document from which the code was extracted.  This allows pdb to
be used more effectively with literate programming-type systems.  The wrapper
was initially created to work with PythonTeX, which allows Python code 
entered within a LaTeX document to be executed.  In that case, syncpdb makes 
possible debugging in which both the code line numbers, and the corresponding
line numbers in the LaTeX document, are displayed.

All pdb commands function normally.  In addition, commands that take a line 
number or filename:lineno as an argument will also take these same values 
with a percent symbol (%) prefix.  If the percent symbol is present, then 
syncpdb interprets the filename and line number as referring to the document, 
rather than to the code that is executed.  It will translate the filename and 
line number to the corresponding code equivalents, and then pass these to the 
standard pdb internals.  For example, the pdb command `list 50` would list 
the code that is being executed, centered around line 50.  syncpdb allows the 
command `list %10`, which would list the code that is being executed, 
centered around the code that came from line 10 in the main document.  (If no 
file name is given, then the main document is assumed.)  If the code instead 
came from an inputed file `input.tex`, then `list %input.tex:10` could be 
used.

   *   *   *

The synchronization is accomplished via a synchronization file with
the extension .syncdb.  It should be located in the same directory as the 
code it synchronizes, and should have the same name as the code, with the 
addition of the .syncdb extension.  For example, `code.py` would have
`code.py.syncdb`.  Currently, the .syncdb must be encoded in UTF8.  The file 
has the following format.  For each chunk of code extracted from a document 
for execution, the file contains a line with the following information:
    ```
    <code filename>,<code lineno>,<doc filename>,<doc lineno>,<chunk length>
    ```/
The first line of the file must be
    ```
    <main code filename>,,<main doc filename>,,
    ```/
All code filenames should be given relative to the main code filename.

The .syncdb format is thus a comma-separated value (csv) format.  The 
elements are defined as follows:
  * <code filename>:  The name of the code file in which the current chunk
    of user code is inserted.  This should be double-quoted if it contains 
    commas.
  * <code lineno>:  The line of the executed code on which the current chunk 
    of user code begins.
  * <doc filename>:  The name of the document file from which the current 
    chunk of user code was extracted.  This should be double-quoted if it 
    contains commas.
  * <doc lineno>:  The line number in the document file where the chunk of 
    user code begins.
  * <chunk length>:  The length of the chunk of code (number of lines).
This information is sufficient for calculating the relationship of each line 
in the code that is executed (and that originated in the document, not a
template) with a line in the document from which the code was extracted.

As an example, suppose that a document main.tex contains 10 lines of Python 
code, beginning on line 50, that are to be executed.  When this code is 
inserted into a template for execution, it begins on line 75 of the code that 
is actually executed.  In this case, the .syncdb file would contain the 
following information for this chunk of code.
    ```
    code.py,75,main.tex,50,10
    ```/
  
While the .syncdb format is currently only intended for simple literate 
programming-type systems, in the future it may be extended for more complex 
cases in which a chunk of code may be substituted into another chunk, perhaps 
with variable replacement.  In such cases, the `<doc filename>, <doc lineno>,` 
may be repeated for each location with a connection to a given line of code, 
allowing a complete traceback of the code's origin to be assembled.  The 
rightmost `<doc filename>, <doc lineno>,` should be the most specific of all
such pairs.

   *   *   *
  
This code is based on pdb.py and bdb.py from the Python standard library.
It subclasses Pdb(), overwriting a number of methods to provide 
synchronization between the code that is executed and the file from which it
was extracted.  It also provides a number functions adapted from pdb.py to
govern execution.  Most of the modifications to the pdb and bdb sources are
wrapped in the pair of comments `# SPdb` and `# /SPdb`.

This code is compatible with both Python 2 and Python 3.  It is based on the
pdb.py and bdb.py from Python 2.7.5 and Python 3.3.2.  Several minor 
modifications were required to get the code from both sources to play nicely
within the same file.

Licensed under the BSD 3-Clause License

Copyright (c) 2014, Geoffrey M. Poore
'''

import sys
import os
import pdb
import bdb
import linecache
if sys.version_info.major == 2:
    from io import open
    from repr import Repr
else:
    import inspect
    import dis
import re
from collections import defaultdict, namedtuple
import traceback


__version__ = '0.2'


__all__ = ["run", "pm", "SyncPdb", "runeval", "runctx", "runcall", "set_trace",
           "post_mortem", "help"]


if sys.version_info.major == 2:
    
    class Restart(Exception):
        """Causes a debugger to be restarted for the debugged python program."""
        pass

    _repr = Repr()
    _repr.maxstring = 200
    _saferepr = _repr.repr
    
    def find_function(funcname, filename):
        cre = re.compile(r'def\s+%s\s*[(]' % re.escape(funcname))
        try:
            fp = open(filename)
        except IOError:
            return None
        # consumer of this info expects the first line to be 1
        lineno = 1
        answer = None
        while 1:
            line = fp.readline()
            if line == '':
                break
            if cre.match(line):
                answer = funcname, filename, lineno
                break
            lineno = lineno + 1
        fp.close()
        return answer
        
    line_prefix = '\n-> '
    
else:
    
    class Restart(Exception):
        """Causes a debugger to be restarted for the debugged python program."""
        pass   
    
    def find_function(funcname, filename):
        cre = re.compile(r'def\s+%s\s*[(]' % re.escape(funcname))
        try:
            fp = open(filename)
        except IOError:
            return None
        # consumer of this info expects the first line to be 1
        lineno = 1
        answer = None
        while True:
            line = fp.readline()
            if line == '':
                break
            if cre.match(line):
                answer = funcname, filename, lineno
                break
            lineno += 1
        fp.close()
        return answer
    
    def getsourcelines(obj):
        lines, lineno = inspect.findsource(obj)
        if inspect.isframe(obj) and obj.f_globals is obj.f_locals:
            # must be a module frame: do not try to cut a block out of it
            return lines, 1
        elif inspect.ismodule(obj):
            return lines, 1
        return inspect.getblock(lines[lineno:]), lineno+1
    
    def lasti2lineno(code, lasti):
        linestarts = list(dis.findlinestarts(code))
        linestarts.reverse()
        for i, lineno in linestarts:
            if lasti >= i:
                return lineno
        return 0
       
    class _rstr(str):
        """String that doesn't quote its repr."""
        def __repr__(self):
            return self

    line_prefix = '\n-> '



Sync = namedtuple('Sync', ['file', 'line'])
def defaultsync():
    return Sync(None, None)


class SyncPdb(pdb.Pdb):
    '''
    Methods that need to be redefined from Pdb for Python 2
     + do_list()
     + format_stack_entry() (bdb)
     + do_break()
     x clear_break()  (bdb)
     + bpprint()  (bdb)
     + do_jump()
     + do_clear()
     + format_stack_entry()  (bdb)
     
    Methods that need to be redefined from Pdb for Python 3
     + do_break()
     + _print_lines()
     x clear_break()  (bdb)
     + bpformat()  (bdb)
     + do_jump()
     + do_list()
     + do_long_list()
     + do_source()
     + format_stack_entry()  (bdb)
     + do_clear()
    '''
    def __init__(self, completekey='tab', stdin=None, stdout=None, skip=None,
                 syncdb=None):
        pdb.Pdb.__init__(self, completekey=completekey, stdin=stdin, 
                         stdout=stdout, skip=skip)
        self._load_syncdb()
    
    _code_to_doc_dict = defaultdict(lambda: defaultdict(defaultsync))
    _doc_to_code_dict = defaultdict(lambda: defaultdict(defaultsync))
    
    _syncdb_pattern = re.compile('([^"]*|"[^"]*"),(.*?),([^"]*|"[^"]*"),(.*?),(.*?)\n')
    
    def _load_syncdb(self):
        syncdb_fname = sys.argv[0] + '.syncdb'
        if os.path.isfile(syncdb_fname):
            f = open(syncdb_fname, 'r', encoding='utf8')
            data = f.readlines()
            f.close()
            main_code_fname, main_doc_fname = [x.strip('"') for x in self._syncdb_pattern.match(data[0]).groups()[0:3:2]]
            self.main_code_fname = main_code_fname
            self.main_doc_fname = main_doc_fname
            # If the main code file isn't being executed from its own 
            # directory, then we will need to correct all code file paths 
            # for this.
            self.current_code_path, self.current_code_fname = os.path.split(sys.argv[0])
            # Check to make sure syncdb is compatible. It could have been 
            # copied under another name in an attempt to reuse it with 
            # another, related script. But that doesn't work, at least 
            # currently.
            if self.current_code_fname != self.main_code_fname:
                sys.exit('The synchonization file is only compatible with "{0}", not "{1}"'.format(self.main_code_fname, self.current_code_fname))
            for line in data[1:]:
                code_fname, code_start_lineno, doc_fname, doc_start_lineno, input_length = self._syncdb_pattern.match(line).groups()
                code_fname = os.path.normcase(code_fname.strip('"').replace('\\', '/'))
                doc_fname = doc_fname.strip('"')
                code_start_lineno = int(code_start_lineno)
                doc_start_lineno = int(doc_start_lineno)
                input_length = int(input_length)
                code_fname_key = os.path.join(self.current_code_path, code_fname)
                code_fname_key_full = os.path.normcase(os.path.abspath(code_fname_key))
                is_main_code = code_fname == main_code_fname
                is_main_doc = doc_fname == main_doc_fname
                for n in range(0, input_length):
                    s = Sync(doc_fname, doc_start_lineno + n)
                    self._code_to_doc_dict[code_fname_key][code_start_lineno + n] = s
                    self._code_to_doc_dict[code_fname_key_full][code_start_lineno + n] = s
                    if is_main_code:
                        self._code_to_doc_dict[''][code_start_lineno + n] = s
                    # When there are multiple sources of code in a 
                    # single line of the document, we want to use the
                    # first one
                    if doc_start_lineno + n not in self._doc_to_code_dict[doc_fname]:
                        s = Sync(code_fname_key, code_start_lineno + n)
                        self._doc_to_code_dict[doc_fname][doc_start_lineno + n] = s
                        if is_main_doc:
                            self._doc_to_code_dict[''][doc_start_lineno + n] = s
        else:
            sys.exit('Could not find synchronization file "{0}"'.format(syncdb_fname))
    
    def code_to_doc(self, code_fname, code_lineno):
        if code_fname in self._code_to_doc_dict:
            if self._code_to_doc_dict[code_fname]:
                return self._code_to_doc_dict[code_fname][code_lineno]
            else:
                return defaultsync()
        else:
            if code_fname not in self._code_to_doc_dict:
                self._code_to_doc_dict[code_fname] = None
            return self.code_to_doc(code_fname, code_lineno)
    
    def doc_to_code(self, doc_fname, doc_lineno):
        if doc_fname in self._doc_to_code_dict:
            if self._doc_to_code_dict[doc_fname]:
                return self._doc_to_code_dict[doc_fname][doc_lineno]
            else:
                return defaultsync()
        else:
            if doc_fname not in self._doc_to_code_dict:
                self._doc_to_code_dict[doc_fname] = None
            return self.doc_to_code(doc_fname, doc_lineno)
    
    _line_numbering_offset = 5
    
    def _format_line_main_doc(self, s, l):
        return '{0} '.format(l).rjust(self._line_numbering_offset) + s
    
    def _format_line_other_doc(self, s, l):
        return '{0} '.format(l).rjust(self._line_numbering_offset) + s
    
    def _format_line_no_doc(self, s):
        return ' '*self._line_numbering_offset + s
    
    _eof_template = ' '*(_line_numbering_offset-1) + '[EOF]'
    
    _last_doc_fname = None
    
    _doc_switch_template = ' {0}:'
    
    _doc_command_char = '%'
    _doc_command_char_stripset = ' {0}'.format(_doc_command_char)
    
   
    if sys.version_info.major == 2:
        
        def bpprint(self, bp, out=None):
            '''
            Replacement for Bdb.bpprint()
            '''
            if out is None:
                out = sys.stdout
            if bp.temporary:
                disp = 'del  '
            else:
                disp = 'keep '
            if bp.enabled:
                disp = disp + 'yes  '
            else:
                disp = disp + 'no   '
            if bp.doc_file is None:
                print >>out, '%-4dbreakpoint   %s at %s:%d' % (bp.number, disp,
                                                               bp.file, bp.line)
            else:
                print >>out, '%-4dbreakpoint   %s at %s:%d (%s:%d)' % (bp.number, disp,
                                                                       bp.file, bp.line,
                                                                       bp.doc_file, bp.doc_line)
            if bp.cond:
                print >>out, '\tstop only if %s' % (bp.cond,)
            if bp.ignore:
                print >>out, '\tignore next %d hits' % (bp.ignore)
            if (bp.hits):
                if (bp.hits > 1): ss = 's'
                else: ss = ''
                print >>out, ('\tbreakpoint already hit %d time%s' %
                              (bp.hits, ss))
        
        
        def do_break(self, arg, temporary = 0):
            # break [ ([filename:]lineno | function) [, "condition"] ]
            if not arg:
                if self.breaks:  # There's at least one
                    print >>self.stdout, "Num Type         Disp Enb   Where"
                    for bp in bdb.Breakpoint.bpbynumber:
                        if bp:
                            # SPdb
                            self.bpprint(bp, self.stdout)
                            #bp.bpprint(self.stdout)
                            # /SPdb
                return
            # parse arguments; comma has lowest precedence
            # and cannot occur in filename
            filename = None
            lineno = None
            cond = None
            comma = arg.find(',')
            if comma > 0:
                # parse stuff after comma: "condition"
                cond = arg[comma+1:].lstrip()
                arg = arg[:comma].lstrip()
            # SPdb
            arg = arg.strip()
            if arg.startswith(self._doc_command_char):
                convert = True
                arg2 = arg.lstrip(self._doc_command_char_stripset)
            else:
                convert = False
                arg2 = arg
            # parse stuff before comma: [filename:]lineno | function
            colon = arg2.rfind(':')
            funcname = None
            if colon >= 0:
                filename = arg2[:colon].rstrip()
                arg2 = arg2[colon+1:].lstrip()
                try:
                    lineno = int(arg2)
                except ValueError:
                    print >>self.stdout, '*** Bad lineno:', arg2
                    return
                if convert:
                    filename, lineno = self.doc_to_code(filename, lineno)
                    filename = os.path.split(filename)[1]
                    lineno = int(lineno)
                f = self.lookupmodule(filename)
                if not f:
                    print >>self.stdout, '*** ', repr(filename),
                    print >>self.stdout, 'not found from sys.path'
                    return
                else:
                    filename = f
                # SPdb
                #arg = arg[colon+1:].lstrip()
                #try:
                #    lineno = int(arg)
                #except ValueError, msg:
                #    print >>self.stdout, '*** Bad lineno:', arg
                #    return
                # /SPdb
            else:
                # no colon; can be lineno or function
                try:
                    lineno = int(arg2)
                    if convert:
                        lineno = int(self.doc_to_code('', lineno).line)
                except ValueError:
                    try:
                        func = eval(arg2,
                                    self.curframe.f_globals,
                                    self.curframe_locals)
                    except:
                        func = arg2
                    try:
                        if hasattr(func, 'im_func'):
                            func = func.im_func
                        code = func.func_code
                        #use co_name to identify the bkpt (function names
                        #could be aliased, but co_name is invariant)
                        funcname = code.co_name
                        lineno = code.co_firstlineno
                        filename = code.co_filename
                    except:
                        # last thing to try
                        (ok, filename, ln) = self.lineinfo(arg2)
                        if not ok:
                            print >>self.stdout, '*** The specified object',
                            print >>self.stdout, repr(arg2),
                            print >>self.stdout, 'is not a function'
                            print >>self.stdout, 'or was not found along sys.path.'
                            return
                        funcname = ok # ok contains a function name
                        lineno = int(ln)
            # /SPdb
            if not filename:
                filename = self.defaultFile()
            # Check for reasonable breakpoint
            line = self.checkline(filename, lineno)
            if line:
                # now set the break point
                err = self.set_break(filename, line, temporary, cond, funcname)
                if err: print >>self.stdout, '***', err
                else:
                    bp = self.get_breaks(filename, line)[-1]
                    # SPdb
                    sync = self.code_to_doc(filename, lineno)
                    if sync == (None, None):
                        print >>self.stdout, "Breakpoint %d at %s:%d" % (bp.number,
                                                                         bp.file,
                                                                         bp.line)
                        bp.doc_file = None
                        bp.doc_line = None
                    else:
                        print >>self.stdout, "Breakpoint %d at %s:%d (%s:%d)" % (bp.number,
                                                                         bp.file,
                                                                         bp.line,
                                                                         sync.file,
                                                                         sync.line)
                        bp.doc_file = sync.file
                        bp.doc_line = sync.line
                    # /SPdb
            
        do_b = do_break
        
        
        def do_clear(self, arg):
            """Three possibilities, tried in this order:
            clear -> clear all breaks, ask for confirmation
            clear file:lineno -> clear all breaks at file:lineno
            clear bpno bpno ... -> clear breakpoints by number"""
            if not arg:
                try:
                    reply = raw_input('Clear all breaks? ')
                except EOFError:
                    reply = 'no'
                reply = reply.strip().lower()
                if reply in ('y', 'yes'):
                    self.clear_all_breaks()
                return
            if ':' in arg:
                # Make sure it works for "clear C:\foo\bar.py:12"
                i = arg.rfind(':')
                # SPdb
                filename = arg[:i].strip()
                arg = arg[i+1:]
                if filename.startswith(self._doc_command_char):
                    filename = filename.lstrip(self._doc_command_char_stripset)
                    filename, arg = self.doc_to_code(filename, int(arg))
                # /SPdb
                try:
                    lineno = int(arg)
                except ValueError:
                    err = "Invalid line number (%s)" % arg
                else:
                    err = self.clear_break(filename, lineno)
                if err: print >>self.stdout, '***', err
                return
            numberlist = arg.split()
            for i in numberlist:
                try:
                    i = int(i)
                except ValueError:
                    print >>self.stdout, 'Breakpoint index %r is not a number' % i
                    continue
    
                if not (0 <= i < len(bdb.Breakpoint.bpbynumber)):
                    print >>self.stdout, 'No breakpoint numbered', i
                    continue
                err = self.clear_bpbynumber(i)
                if err:
                    print >>self.stdout, '***', err
                else:
                    print >>self.stdout, 'Deleted breakpoint', i
        
        do_cl = do_clear # 'c' is already an abbreviation for 'continue'
        
        
        def do_jump(self, arg):
            if self.curindex + 1 != len(self.stack):
                print >>self.stdout, "*** You can only jump within the bottom frame"
                return
            # SPdb
            if arg.startswith(self._doc_command_char):
                convert = True
                if ':' in arg:
                    doc_fname, arg = arg.lstrip(self._doc_command_char_stripset).split(':', 1)
                else:
                    doc_fname = ''
                    arg = arg.lstrip(self._doc_command_char_stripset)   
            else:
                convert = False              
            # /SPdb
            try:
                arg = int(arg)
                # SPdb
                if convert:
                    arg = int(self.doc_to_code(doc_fname, arg).line)
                # /SPdb
            except ValueError:
                print >>self.stdout, "*** The 'jump' command requires a line number."
            else:
                try:
                    # Do the jump, fix up our copy of the stack, and display the
                    # new position
                    self.curframe.f_lineno = arg
                    self.stack[self.curindex] = self.stack[self.curindex][0], arg
                    self.print_stack_entry(self.stack[self.curindex])
                # SPdb
                except ValueError as e:
                    print >>self.stdout, '*** Jump failed:', e
                # /SPdb
        
        do_j = do_jump
        
        
        def do_list(self, arg):
            self.lastcmd = 'list'
            last = None
            if arg:
                # SPdb
                arg = arg.strip()
                if arg.startswith(self._doc_command_char):
                    convert = True
                    if ':' in arg:
                        doc_fname, arg2 = arg.lstrip(self._doc_command_char_stripset).split(':', 1)
                    else:
                        doc_fname = ''
                        arg2 = arg.lstrip(self._doc_command_char_stripset)
                else:
                    convert = False
                    arg2 = arg
                # /SPdb
                try:
                    # SPdb
                    x = eval(arg2, {}, {})
                    # /SPdb
                    if type(x) == type(()):
                        first, last = x
                        first = int(first)
                        last = int(last)
                        # SPdb
                        if convert:
                            first = int(self.doc_to_code(doc_fname, first).line)
                            last = int(self.doc_to_code(doc_fname, last).line)
                        # /SPdb
                        if last < first:
                            # Assume it's a count
                            last = first + last
                    else:
                        # SPdb
                        first = int(x)
                        if convert:
                            first = int(self.doc_to_code(doc_fname, first).line)
                        first = max(1, first - 5)
                        # /SPdb
                except:
                    print >>self.stdout, '*** Error in argument:', repr(arg)
                    return
            elif self.lineno is None:
                first = max(1, self.curframe.f_lineno - 5)
            else:
                first = self.lineno + 1
            if last is None:
                last = first + 10
            filename = self.curframe.f_code.co_filename
            breaklist = self.get_file_breaks(filename)
            try:
                # SPdb
                self._last_doc_fname = None
                # /SPdb
                for lineno in range(first, last+1):
                    line = linecache.getline(filename, lineno,
                                             self.curframe.f_globals)
                    if not line:
                        print >>self.stdout, self._eof_template
                        break
                    else:
                        s = repr(lineno).rjust(3)
                        if len(s) < 4: s = s + ' '
                        if lineno in breaklist: s = s + 'B'
                        else: s = s + ' '
                        # SPdb
                        if lineno == self.curframe.f_lineno:
                            s = s + '->'
                        else:
                            s = s + '  '
                        f, l = self.code_to_doc(filename, lineno)
                        if f == self.main_doc_fname:
                            s = self._format_line_main_doc(s, l)
                        elif f:
                            s = self._format_line_other_doc(s, l)
                        else:
                            s = self._format_line_no_doc(s)
                        if f != self._last_doc_fname:
                            self._last_doc_fname = f
                            if f is not None:
                                print(self._doc_switch_template.format(f))
                        print >>self.stdout, s + ' ' + line,
                        # /SPdb
                        self.lineno = lineno
            except KeyboardInterrupt:
                pass
        
        do_l = do_list
        
        
        def format_stack_entry(self, frame_lineno, lprefix=': '):
            import linecache, repr
            frame, lineno = frame_lineno
            filename = self.canonic(frame.f_code.co_filename)
            s = '%s(%r)' % (filename, lineno)
            if frame.f_code.co_name:
                s = s + frame.f_code.co_name
            else:
                s = s + "<lambda>"
            if '__args__' in frame.f_locals:
                args = frame.f_locals['__args__']
            else:
                args = None
            if args:
                s = s + repr.repr(args)
            else:
                s = s + '()'
            if '__return__' in frame.f_locals:
                rv = frame.f_locals['__return__']
                s = s + '->'
                s = s + repr.repr(rv)
            line = linecache.getline(filename, lineno, frame.f_globals)
            # SPdb
            sync = self.code_to_doc(frame.f_code.co_filename, lineno)
            if sync == (None, None):
                sync_info = ''
            else:
                sync_info = ' ({0}:{1})'.format(sync.file, sync.line)
            if line: s = s + sync_info + lprefix + line.strip()        
            # /SPdb
            return s

    
    else:
        
        def bpformat(self, bp):
            if bp.temporary:
                disp = 'del  '
            else:
                disp = 'keep '
            if bp.enabled:
                disp = disp + 'yes  '
            else:
                disp = disp + 'no   '
            # SPdb
            if bp.doc_file is None:
                ret = '%-4dbreakpoint   %s at %s:%d' % (bp.number, disp,
                                                        bp.file, bp.line)
            else:
                ret = '%-4dbreakpoint   %s at %s:%d (%s:%d)' % (bp.number, disp,
                                                                bp.file, bp.line,
                                                                bp.doc_file, bp.doc_line)
            # /SPdb
            if bp.cond:
                ret += '\n\tstop only if %s' % (bp.cond,)
            if bp.ignore:
                ret += '\n\tignore next %d hits' % (bp.ignore,)
            if bp.hits:
                if bp.hits > 1:
                    ss = 's'
                else:
                    ss = ''
                ret += '\n\tbreakpoint already hit %d time%s' % (bp.hits, ss)
            return ret
        
        
        def do_break(self, arg, temporary = 0):
            """b(reak) [ ([filename:]lineno | function) [, condition] ]
            Without argument, list all breaks.
    
            With a line number argument, set a break at this line in the
            current file.  With a function name, set a break at the first
            executable line of that function.  If a second argument is
            present, it is a string specifying an expression which must
            evaluate to true before the breakpoint is honored.
    
            The line number may be prefixed with a filename and a colon,
            to specify a breakpoint in another file (probably one that
            hasn't been loaded yet).  The file is searched for on
            sys.path; the .py suffix may be omitted.
            """
            if not arg:
                if self.breaks:  # There's at least one
                    self.message("Num Type         Disp Enb   Where")
                    for bp in bdb.Breakpoint.bpbynumber:
                        if bp:
                            self.message(self.bpformat(bp))
                return
            # parse arguments; comma has lowest precedence
            # and cannot occur in filename
            filename = None
            lineno = None
            cond = None
            comma = arg.find(',')
            if comma > 0:
                # parse stuff after comma: "condition"
                cond = arg[comma+1:].lstrip()
                arg = arg[:comma].rstrip()
            # SPdb
            arg = arg.strip()
            if arg.startswith(self._doc_command_char):
                convert = True
                arg2 = arg.lstrip(self._doc_command_char_stripset)
            else:
                convert = False
                arg2 = arg
            # parse stuff before comma: [filename:]lineno | function
            colon = arg2.rfind(':')
            funcname = None
            if colon >= 0:
                filename = arg2[:colon].rstrip()
                arg2 = arg2[colon+1:].lstrip()
                try:
                    lineno = int(arg2)
                except ValueError:
                    self.error('Bad lineno: %s' % arg2)
                    return
                if convert:
                    filename, lineno = self.doc_to_code(filename, lineno)
                    filename = os.path.split(filename)[1]
                    lineno = int(lineno)
                f = self.lookupmodule(filename)
                if not f:
                    self.error('%r not found from sys.path' % filename)
                    return
                else:
                    filename = f
                # SPdb
                #arg = arg[colon+1:].lstrip()
                #try:
                #    lineno = int(arg)
                #except ValueError:
                #    self.error('Bad lineno: %s' % arg)
                #    return
                # SPdb
            else:
                # no colon; can be lineno or function
                try:
                    lineno = int(arg2)
                    if convert:
                        lineno = int(self.doc_to_code('', lineno).line)
                except ValueError:
                    try:
                        func = eval(arg2,
                                    self.curframe.f_globals,
                                    self.curframe_locals)
                    except:
                        func = arg2
                    try:
                        if hasattr(func, '__func__'):
                            func = func.__func__
                        code = func.__code__
                        #use co_name to identify the bkpt (function names
                        #could be aliased, but co_name is invariant)
                        funcname = code.co_name
                        lineno = code.co_firstlineno
                        filename = code.co_filename
                    except:
                        # last thing to try
                        (ok, filename, ln) = self.lineinfo(arg2)
                        if not ok:
                            self.error('The specified object %r is not a function '
                                       'or was not found along sys.path.' % arg2)
                            return
                        funcname = ok # ok contains a function name
                        lineno = int(ln)
            # /SPdb
            if not filename:
                filename = self.defaultFile()
            # Check for reasonable breakpoint
            line = self.checkline(filename, lineno)
            if line:
                # now set the break point
                err = self.set_break(filename, line, temporary, cond, funcname)
                if err:
                    self.error(err, file=self.stdout)
                else:
                    bp = self.get_breaks(filename, line)[-1]
                    # SPdb
                    sync = self.code_to_doc(filename, lineno)
                    if sync == (None, None):
                        self.message("Breakpoint %d at %s:%d" %
                                     (bp.number, bp.file, bp.line))
                        bp.doc_file = None
                        bp.doc_line = None
                    else:
                        self.message("Breakpoint %d at %s:%d (%s:%d)" %
                                     (bp.number, bp.file, bp.line, 
                                      sync.file, sync.line))
                        bp.doc_file = sync.file
                        bp.doc_line = sync.line
                    # /SPdb
        
        do_b = do_break
        
        
        def do_clear(self, arg):
            """cl(ear) filename:lineno\ncl(ear) [bpnumber [bpnumber...]]
            With a space separated list of breakpoint numbers, clear
            those breakpoints.  Without argument, clear all breaks (but
            first ask confirmation).  With a filename:lineno argument,
            clear all breaks at that line in that file.
            """
            if not arg:
                try:
                    reply = input('Clear all breaks? ')
                except EOFError:
                    reply = 'no'
                reply = reply.strip().lower()
                if reply in ('y', 'yes'):
                    bplist = [bp for bp in bdb.Breakpoint.bpbynumber if bp]
                    self.clear_all_breaks()
                    for bp in bplist:
                        self.message('Deleted %s' % bp)
                return
            if ':' in arg:
                # Make sure it works for "clear C:\foo\bar.py:12"
                i = arg.rfind(':')
                # SPdb
                filename = arg[:i].strip()
                arg = arg[i+1:]
                if filename.startswith(self._doc_command_char):
                    filename = filename.lstrip(self._doc_command_char_stripset)
                    filename, arg = self.doc_to_code(filename, int(arg))
                # /SPdb
                try:
                    lineno = int(arg)
                except ValueError:
                    err = "Invalid line number (%s)" % arg
                else:
                    bplist = self.get_breaks(filename, lineno)
                    err = self.clear_break(filename, lineno)
                if err:
                    self.error(err)
                else:
                    for bp in bplist:
                        self.message('Deleted %s' % bp)
                return
            numberlist = arg.split()
            for i in numberlist:
                try:
                    bp = self.get_bpbynumber(i)
                except ValueError as err:
                    self.error(err)
                else:
                    self.clear_bpbynumber(i)
                    self.message('Deleted %s' % bp)
        
        do_cl = do_clear # 'c' is already an abbreviation for 'continue'
        
                
        def do_jump(self, arg):
            """j(ump) lineno
            Set the next line that will be executed.  Only available in
            the bottom-most frame.  This lets you jump back and execute
            code again, or jump forward to skip code that you don't want
            to run.
    
            It should be noted that not all jumps are allowed -- for
            instance it is not possible to jump into the middle of a
            for loop or out of a finally clause.
            """
            if self.curindex + 1 != len(self.stack):
                self.error('You can only jump within the bottom frame')
                return
            # SPdb
            if arg.startswith(self._doc_command_char):
                convert = True
                if ':' in arg:
                    doc_fname, arg = arg.lstrip(self._doc_command_char_stripset).split(':', 1)
                else:
                    doc_fname = ''
                    arg = arg.lstrip(self._doc_command_char_stripset)   
            else:
                convert = False              
            # /SPdb
            try:
                arg = int(arg)
                # SPdb
                if convert:
                    arg = int(self.doc_to_code(doc_fname, arg).line)
                # /SPdb
            except ValueError:
                self.error("The 'jump' command requires a line number")
            else:
                try:
                    # Do the jump, fix up our copy of the stack, and display the
                    # new position
                    self.curframe.f_lineno = arg
                    self.stack[self.curindex] = self.stack[self.curindex][0], arg
                    self.print_stack_entry(self.stack[self.curindex])
                except ValueError as e:
                    self.error('Jump failed: %s' % e)
        
        do_j = do_jump
        
        
        def do_list(self, arg):
            """l(ist) [first [,last] | .]
    
            List source code for the current file.  Without arguments,
            list 11 lines around the current line or continue the previous
            listing.  With . as argument, list 11 lines around the current
            line.  With one argument, list 11 lines starting at that line.
            With two arguments, list the given range; if the second
            argument is less than the first, it is a count.
    
            The current line in the current frame is indicated by "->".
            If an exception is being debugged, the line where the
            exception was originally raised or propagated is indicated by
            ">>", if it differs from the current line.
            """
            self.lastcmd = 'list'
            last = None
            if arg and arg != '.':
                try:
                    # SPdb
                    arg = arg.strip()
                    if arg.startswith(self._doc_command_char):
                        convert = True
                        if ':' in arg:
                            doc_fname, arg2 = arg.lstrip(self._doc_command_char_stripset).split(':', 1)
                        else:
                            doc_fname = ''
                            arg2 = arg.lstrip(self._doc_command_char_stripset)
                    else:
                        convert = False
                        arg2 = arg
                    if ',' in arg2:
                        first, last = arg2.split(',')
                        first = int(first.strip())
                        last = int(last.strip())
                        if convert:
                            first = int(self.doc_to_code(doc_fname, first).line)
                            last = int(self.doc_to_code(doc_fname, last).line)
                        if last < first:
                            # assume it's a count
                            last = first + last
                    else:
                        first = int(arg2.strip())
                        if convert:
                            first = int(self.doc_to_code(doc_fname, first).line)
                        first = max(1, first - 5)
                    # /SPdb
                except ValueError:
                    self.error('Error in argument: %r' % arg)
                    return
            elif self.lineno is None or arg == '.':
                first = max(1, self.curframe.f_lineno - 5)
            else:
                first = self.lineno + 1
            if last is None:
                last = first + 10
            filename = self.curframe.f_code.co_filename
            breaklist = self.get_file_breaks(filename)
            try:
                lines = linecache.getlines(filename, self.curframe.f_globals)
                # SPdb
                self._print_lines(filename, lines[first-1:last], first, last, 
                                  breaklist, self.curframe)
                # /SPdb
                self.lineno = min(last, len(lines))
                # SPdb
                #if len(lines) < last:
                #    self.message('[EOF]')
                # /SPdb
            except KeyboardInterrupt:
                pass
       
        do_l = do_list

        
        def do_longlist(self, arg):
            """longlist | ll
            List the whole source code for the current function or frame.
            """
            filename = self.curframe.f_code.co_filename
            breaklist = self.get_file_breaks(filename)
            try:
                lines, lineno = getsourcelines(self.curframe)
            except IOError as err:
                self.error(err)
                return
            # SPdb
            self._print_lines(filename, lines, lineno, lineno + len(lines) - 1,
                              breaklist, self.curframe)
            # /SPdb
        
        do_ll = do_longlist
    
        
        def do_source(self, arg):
            """source expression
            Try to get source code for the given object and display it.
            """
            try:
                obj = self._getval(arg)
            except:
                return
            try:
                lines, lineno = getsourcelines(obj)
            except (IOError, TypeError) as err:
                self.error(err)
                return
            self._print_lines(lines, lineno)
        
        
        # SPdb added filename, last args; renames start -> first  # /SPdb
        def _print_lines(self, filename, lines, first, last, breaks=(), frame=None):
            """Print a range of lines."""
            if frame:
                current_lineno = frame.f_lineno
                exc_lineno = self.tb_lineno.get(frame, -1)
            else:
                current_lineno = exc_lineno = -1
            # SPdb
            self._last_doc_fname = None
            # /Spdb
            for lineno, line in enumerate(lines, first):
                s = str(lineno).rjust(3)
                if len(s) < 4:
                    s += ' '
                if lineno in breaks:
                    s += 'B'
                else:
                    s += ' '
                # SPdb
                if lineno == current_lineno:
                    s += '->'
                elif lineno == exc_lineno:
                    s += '>>'
                else:
                    s += '  '
                f, l = self.code_to_doc(filename, lineno)
                if f == self.main_doc_fname:
                    s = self._format_line_main_doc(s, l)
                elif f:
                    s = self._format_line_other_doc(s, l)
                else:
                    s = self._format_line_no_doc(s)
                if f != self._last_doc_fname:
                    self._last_doc_fname = f
                    if f is not None:
                        self.message(self._doc_switch_template.format(f))
                self.message(s + ' ' + line.rstrip())
                # /SPdb
            # SPdb
            if len(lines) < last - first + 1:
                self.message(self._eof_template)
            # /SPdb
        
        
        def format_stack_entry(self, frame_lineno, lprefix=': '):
            import linecache, reprlib
            frame, lineno = frame_lineno
            filename = self.canonic(frame.f_code.co_filename)
            s = '%s(%r)' % (filename, lineno)
            if frame.f_code.co_name:
                s += frame.f_code.co_name
            else:
                s += "<lambda>"
            if '__args__' in frame.f_locals:
                args = frame.f_locals['__args__']
            else:
                args = None
            if args:
                s += reprlib.repr(args)
            else:
                s += '()'
            if '__return__' in frame.f_locals:
                rv = frame.f_locals['__return__']
                s += '->'
                s += reprlib.repr(rv)
            line = linecache.getline(filename, lineno, frame.f_globals)
            # SPdb
            sync = self.code_to_doc(frame.f_code.co_filename, lineno)
            if sync == (None, None):
                sync_info = ''
            else:
                sync_info = ' ({0}:{1})'.format(sync.file, sync.line)
            # /SPdb
            if line:
                # SPdb
                s += sync_info
                # /Spdb
                s += lprefix + line.strip()
            return s




if sys.version_info.major == 2:
    
    # Simplified interface

    def run(statement, globals=None, locals=None):
        SyncPdb().run(statement, globals, locals)
    
    def runeval(expression, globals=None, locals=None):
        return SyncPdb().runeval(expression, globals, locals)
    
    def runctx(statement, globals, locals):
        # B/W compatibility
        run(statement, globals, locals)
    
    def runcall(*args, **kwds):
        return SyncPdb().runcall(*args, **kwds)
    
    def set_trace():
        SyncPdb().set_trace(sys._getframe().f_back)
    
    # Post-Mortem interface
    
    def post_mortem(t=None):
        # handling the default
        if t is None:
            # sys.exc_info() returns (type, value, traceback) if an exception is
            # being handled, otherwise it returns None
            t = sys.exc_info()[2]
            if t is None:
                raise ValueError("A valid traceback must be passed if no "
                                                   "exception is being handled")
    
        p = SyncPdb()
        p.reset()
        p.interaction(None, t)
    
    def pm():
        post_mortem(sys.last_traceback)
    
    
    # Main program for testing
    
    TESTCMD = 'import x; x.main()'
    
    def test():
        run(TESTCMD)
    
    # print help
    def help():
        for dirname in sys.path:
            fullname = os.path.join(dirname, 'pdb.doc')
            if os.path.exists(fullname):
                sts = os.system('${PAGER-more} '+fullname)
                # SPdb
                if sts: print('*** Pager exit status: {0}'.format(sts))
                # /SPdb
                break
        else:
            # SPdb
            print('Sorry, can\'t find the help file "pdb.doc" along the Python search path')
            # /SPdb
    
else:
    
    # Collect all command help into docstring, if not run with -OO
    
    if __doc__ is not None:
        # unfortunately we can't guess this order from the class definition
        _help_order = [
            'help', 'where', 'down', 'up', 'break', 'tbreak', 'clear', 'disable',
            'enable', 'ignore', 'condition', 'commands', 'step', 'next', 'until',
            'jump', 'return', 'retval', 'run', 'continue', 'list', 'longlist',
            'args', 'print', 'pp', 'whatis', 'source', 'display', 'undisplay',
            'interact', 'alias', 'unalias', 'debug', 'quit',
        ]
    
        for _command in _help_order:
            __doc__ += getattr(SyncPdb, 'do_' + _command).__doc__.strip() + '\n\n'
        __doc__ += SyncPdb.help_exec.__doc__
    
        del _help_order, _command
    
    
    # Simplified interface
    
    def run(statement, globals=None, locals=None):
        SyncPdb().run(statement, globals, locals)
    
    def runeval(expression, globals=None, locals=None):
        return SyncPdb().runeval(expression, globals, locals)
    
    def runctx(statement, globals, locals):
        # B/W compatibility
        run(statement, globals, locals)
    
    def runcall(*args, **kwds):
        return SyncPdb().runcall(*args, **kwds)
    
    def set_trace():
        SyncPdb().set_trace(sys._getframe().f_back)
    
    # Post-Mortem interface
    
    def post_mortem(t=None):
        # handling the default
        if t is None:
            # sys.exc_info() returns (type, value, traceback) if an exception is
            # being handled, otherwise it returns None
            t = sys.exc_info()[2]
        if t is None:
            raise ValueError("A valid traceback must be passed if no "
                             "exception is being handled")
    
        p = SyncPdb()
        p.reset()
        p.interaction(None, t)
    
    def pm():
        post_mortem(sys.last_traceback)
    
    
    # Main program for testing
    
    TESTCMD = 'import x; x.main()'
    
    def test():
        run(TESTCMD)
    
    # print help
    def help():
        import pydoc
        pydoc.pager(__doc__)
    
    _usage = """\
    usage: syncpdb.py [-c command] ... pyfile [arg] ...
    
    Debug the Python program given by pyfile.
    
    Initial commands are read from .pdbrc files in your home directory
    and in the current directory, if they exist.  Commands supplied with
    -c are executed after commands from .pdbrc files.
    
    To let the script run until an exception occurs, use "-c continue".
    To let the script run up to a given line X in the debugged file, use
    "-c 'until X'"."""




if sys.version_info == 2:
    def main():
        if not sys.argv[1:] or sys.argv[1] in ("--help", "-h"):
            # SPdb
            print("usage: syncpdb.py scriptfile [arg] ...")
            # /SPdb
            sys.exit(2)
    
        mainpyfile =  sys.argv[1]     # Get script filename
        if not os.path.exists(mainpyfile):
            # SPdb
            print('Error:', mainpyfile, 'does not exist')
            # /SPdb
            sys.exit(1)
    
        del sys.argv[0]         # Hide "pdb.py" from argument list
    
        # Replace pdb's dir with script's dir in front of module search path.
        sys.path[0] = os.path.dirname(mainpyfile)
    
        # Note on saving/restoring sys.argv: it's a good idea when sys.argv was
        # modified by the script being debugged. It's a bad idea when it was
        # changed by the user from the command line. There is a "restart" command
        # which allows explicit specification of command line arguments.
        syncpdb = SyncPdb()
        while True:
            try:
                syncpdb._runscript(mainpyfile)
                if syncpdb._user_requested_quit:
                    break
                # SPdb
                print("The program finished and will be restarted")
                # /SPdb
            except Restart:
                # SPdb
                print("Restarting", mainpyfile, "with arguments:")
                print("\t" + " ".join(sys.argv[1:]))
                # /SPdb
            except SystemExit:
                # In most cases SystemExit does not warrant a post-mortem session.
                # SPdb
                print("The program exited via sys.exit(). Exit status: {0}".format(sys.exc_info()[1]))
                # /SPdb
            except:
                traceback.print_exc()
                # SPdb
                print("Uncaught exception. Entering post mortem debugging")
                print("Running 'cont' or 'step' will restart the program")
                # /SPdb
                t = sys.exc_info()[2]
                syncpdb.interaction(None, t)
                # SPdb
                print("Post mortem debugger finished. The {0} will be restarted".format(mainpyfile))
                # /SPdb
else:
    def main():
        import getopt
    
        opts, args = getopt.getopt(sys.argv[1:], 'hc:', ['--help', '--command='])
    
        if not args:
            print(_usage)
            sys.exit(2)
    
        commands = []
        for opt, optarg in opts:
            if opt in ['-h', '--help']:
                print(_usage)
                sys.exit()
            elif opt in ['-c', '--command']:
                commands.append(optarg)
    
        mainpyfile = args[0]     # Get script filename
        if not os.path.exists(mainpyfile):
            print('Error:', mainpyfile, 'does not exist')
            sys.exit(1)
    
        sys.argv[:] = args      # Hide "pdb.py" and pdb options from argument list
    
        # Replace pdb's dir with script's dir in front of module search path.
        sys.path[0] = os.path.dirname(mainpyfile)
    
        # Note on saving/restoring sys.argv: it's a good idea when sys.argv was
        # modified by the script being debugged. It's a bad idea when it was
        # changed by the user from the command line. There is a "restart" command
        # which allows explicit specification of command line arguments.
        syncpdb = SyncPdb()
        syncpdb.rcLines.extend(commands)
        while True:
            try:
                syncpdb._runscript(mainpyfile)
                if syncpdb._user_requested_quit:
                    break
                print("The program finished and will be restarted")
            except Restart:
                print("Restarting", mainpyfile, "with arguments:")
                print("\t" + " ".join(args))
            except SystemExit:
                # In most cases SystemExit does not warrant a post-mortem session.
                # SPdb
                print("The program exited via sys.exit(). Exit status: {0}".format(sys.exc_info()[1]))
                # /SPdb
            except:
                traceback.print_exc()
                print("Uncaught exception. Entering post mortem debugging")
                print("Running 'cont' or 'step' will restart the program")
                t = sys.exc_info()[2]
                syncpdb.interaction(None, t)
                print("Post mortem debugger finished. The " + mainpyfile +
                      " will be restarted")


# When invoked as main program, invoke the debugger on a script
if __name__ == '__main__':
    import syncpdb
    syncpdb.main()
