#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
This is the main PythonTeX script.  It should be launched via pythontex.py.

Two versions of this script are provided.  One, with name ending in "2", runs 
under Python 2.7.  The other, with name ending in "3", runs under Python 3.2+.

This script needs to be able to import pythontex_engines.py; in general it 
should be in the same directory.


Licensed under the BSD 3-Clause License:

Copyright (c) 2012-2013, Geoffrey M. Poore

All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of the <organization> nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
'''


# Imports
#// Python 2
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
#\\ End Python 2
import sys
import os
import argparse
import codecs
import time
from hashlib import sha1
from collections import defaultdict, OrderedDict, namedtuple
from re import match, sub, search
import subprocess
import multiprocessing
from pygments.styles import get_all_styles
from pythontex_engines import *
import textwrap

if sys.version_info[0] == 2:
    try:
        import cPickle as pickle
    except:
        import pickle
    from io import open
else:
    import pickle




# Script parameters
# Version
version = 'v0.12'




class Pytxcode(object):
    def __init__(self, data, gobble):
        self.delims, self.code = data.split('#\n', 1)
        self.input_family, self.input_session, self.input_restart, self.input_instance, self.input_command, self.input_context, self.input_args_run, self.input_args_prettyprint, self.input_file, self.input_line = self.delims.split('#')
        self.input_instance_int = int(self.input_instance)        
        self.input_line_int = int(self.input_line)
        self.key_run = self.input_family + '#' + self.input_session + '#' + self.input_restart
        self.key_typeset = self.key_run + '#' + self.input_instance
        self.hashable_delims_run = self.key_typeset + '#' + self.input_command + '#' + self.input_context + '#' + self.input_args_run
        self.hashable_delims_typeset = self.key_typeset + '#' + self.input_command + '#' + self.input_context + '#' + self.input_args_run
        if len(self.input_command) > 1:
            self.is_inline = False
            # Environments start on the next line
            self.input_line_int += 1
            self.input_line = str(self.input_line_int)
        else:
            self.is_inline = True
        self.is_extfile = True if self.input_session.startswith('EXT:') else False
        if self.is_extfile:
            self.extfile = os.path.expanduser(os.path.normcase(self.input_session.replace('EXT:', '', 1)))
        self.is_cc = True if self.input_family.startswith('CC:') else False
        self.is_pyg = True if self.input_family.startswith('PYG') else False
        self.is_verb = True if self.input_restart.endswith('verb') else False
        if self.is_cc:
            self.input_instance += 'CC'
            self.cc_type, self.cc_pos = self.input_family.split(':')[1:]
        if self.is_verb or self.is_pyg or self.is_cc:
            self.is_cons = False
        else:
            self.is_cons = engine_dict[self.input_family].console
        self.is_code = False if self.is_verb or self.is_pyg or self.is_cc or self.is_cons else True
        if self.input_command in ('c', 'code') or (self.input_command == 'i' and not self.is_cons):
            self.is_typeset = False
        else:
            self.is_typeset = True
        
        if gobble == 'auto':
            self.code = textwrap.dedent(self.code)
            



def process_argv(data, temp_data):
    '''
    Process command line options using the argparse module.
    
    Most options are passed via the file of code, rather than via the command
    line.
    '''
    
    # Create a command line argument parser
    parser = argparse.ArgumentParser()
    parser.add_argument('TEXNAME',
                        help='LaTeX file, with or without .tex extension')
    parser.add_argument('--version', action='version', 
                        version='PythonTeX {0}'.format(data['version']))                    
    parser.add_argument('--encoding', default='UTF-8', 
                        help='encoding for all text files (see codecs module for encodings)')
    parser.add_argument('--error-exit-code', default='true', 
                        choices=('true', 'false'),                          
                        help='return exit code of 1 if there are errors (not desirable with some TeX editors and workflows)')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--runall', nargs='?', default='false',
                       const='true', choices=('true', 'false'),
                       help='run ALL code; equivalent to package option')
    group.add_argument('--rerun', default='errors', 
                       choices=('never', 'modified', 'errors', 'warnings', 'always'),
                       help='set conditions for rerunning code; equivalent to package option')
    parser.add_argument('--hashdependencies', nargs='?', default='false', 
                        const='true', choices=('true', 'false'),                          
                        help='hash dependencies (such as external data) to check for modification, rather than using mtime; equivalent to package option')
    parser.add_argument('-v', '--verbose', default=False, action='store_true',
                        help='verbose output')
    parser.add_argument('--interpreter', default=None, help='set a custom interpreter; argument should be in the form "<interpreter>:<command>, <interp>:<cmd>, ..." where <interpreter> is "python", "ruby", etc., and <command> is the command for invoking the interpreter; argument may also be in the form of a Python dictionary')
    args = parser.parse_args()
    
    # Store the parsed argv in data and temp_data          
    data['encoding'] = args.encoding
    if args.error_exit_code == 'true':
        temp_data['error_exit_code'] = True
    else:
        temp_data['error_exit_code'] = False
    # runall can be mapped onto rerun, so both are stored under rerun
    if args.runall == 'true':
        temp_data['rerun'] = 'always'
    else:
        temp_data['rerun'] = args.rerun
    # hashdependencies need only be in temp_data, since changing it would
    # change hashes (hashes of mtime vs. file contents)
    if args.hashdependencies == 'true':
        temp_data['hashdependencies'] = True
    else:
        temp_data['hashdependencies'] = False
    temp_data['verbose'] = args.verbose
    # Update interpreter_dict based on interpreter
    if args.interpreter is not None:
        interp_list = args.interpreter.lstrip('{').rstrip('}').split(',')
        for interp in interp_list:
            if interp:
                try:
                    k, v = interp.split(':')
                    k = k.strip(' \'"')
                    v = v.strip(' \'"')
                    interpreter_dict[k] = v
                except:
                    print('Invalid --interpreter argument')
                    return sys.exit(2)
    
    
    if args.TEXNAME is not None:
        # Determine if we a dealing with just a filename, or a name plus 
        # path.  If there's a path, we need to make the document directory 
        # the current working directory.
        dir, raw_jobname = os.path.split(args.TEXNAME)
        dir = os.path.expanduser(os.path.normcase(dir))
        if dir:
            os.chdir(dir)
            sys.path.append(dir)
        # If necessary, strip off an extension to find the raw jobname that
        # corresponds to the .pytxcode.
        if not os.path.exists(raw_jobname + '.pytxcode'):
            raw_jobname = raw_jobname.rsplit('.', 1)[0]
            if not os.path.exists(raw_jobname + '.pytxcode'):
                print('* PythonTeX error')
                print('    Code file ' + raw_jobname + '.pytxcode does not exist.')
                print('    Run LaTeX to create it.')
                return sys.exit(1)
        
        # We need a "sanitized" version of the jobname, with spaces and 
        # asterisks replaced with hyphens.  This is done to avoid TeX issues 
        # with spaces in file names, paralleling the approach taken in 
        # pythontex.sty.  From now on, we will use the sanitized version every 
        # time we create a file that contains the jobname string.  The raw 
        # version will only be used in reference to pre-existing files created 
        # on the TeX side, such as the .pytxcode file.
        jobname = raw_jobname.replace(' ', '-').replace('"', '').replace('*', '-')
        # Store the results in data
        data['raw_jobname'] = raw_jobname
        data['jobname'] = jobname
        
        # We need to check to make sure that the "sanitized" jobname doesn't 
        # lead to a collision with a file that already has that name, so that 
        # two files attempt to use the same PythonTeX folder.
        # 
        # If <jobname>.<ext> and <raw_jobname>.<ext> both exist, where <ext>
        # is a common LaTeX extension, we exit.  We operate under the 
        # assumption that there should be only a single file <jobname> in the 
        # document root directory that has a common LaTeX extension.  That 
        # could be false, but if so, the user probably has worse things to 
        # worry about than a potential PythonTeX output collision.
        # If <jobname>* and <raw_jobname>* both exist, we issue a warning but 
        # attempt to proceed.
        if jobname != raw_jobname:
            resolved = False
            for ext in ('.tex', '.ltx', '.dtx'):
                if os.path.isfile(raw_jobname + ext):
                    if os.path.isfile(jobname + ext):
                        print('* PythonTeX error')
                        print('    Directory naming collision between the following files:')
                        print('      ' + raw_jobname + ext)
                        print('      ' + jobname + ext)
                        return sys.exit(1)
                    else:
                        resolved = True
                        break
            if not resolved:
                ls = os.listdir('.')
                for file in ls:
                    if file.startswith(jobname):
                        print('* PythonTeX warning')
                        print('    Potential directory naming collision between the following names:')
                        print('      ' + raw_jobname)
                        print('      ' + jobname + '*')
                        print('    Attempting to proceed.')
                        temp_data['warnings'] += 1
                        break            
        
        


def load_code_get_settings(data, temp_data):
    '''
    Load the code file, preprocess the code, and extract the settings.
    '''
    # Bring in the .pytxcode file as a single string
    raw_jobname = data['raw_jobname']
    encoding = data['encoding']
    # The error checking here is a little redundant
    if os.path.isfile(raw_jobname + '.pytxcode'):
        f = open(raw_jobname + '.pytxcode', 'r', encoding=encoding)
        pytxcode = f.read()
        f.close()
    else:
        print('* PythonTeX error')
        print('    Code file ' + raw_jobname + '.pytxcode does not exist.')
        print('    Run LaTeX to create it.')
        return sys.exit(1)
    
    # Split code and settings
    try:
        pytxcode, pytxsettings = pytxcode.rsplit('=>PYTHONTEX:SETTINGS#', 1)
    except:
        print('The .pytxcode file appears to have an outdated format or be invalid')
        print('Run LaTeX to make sure the file is current')
        return sys.exit(1)
    
    
    # Prepare to process settings
    #
    # Create a dict for storing settings.
    settings = {}
    # Create a dict for storing Pygments settings.
    # Each dict entry will itself be a dict.
    pygments_settings = defaultdict(dict)
    
    # Create a dict of processing functions, and generic processing functions
    settings_func = dict()
    def set_kv_data(k, v):
        if v == 'true':
            settings[k] = True
        elif v == 'false':
            settings[k] = False
        else:
            settings[k] = v
    # Need a function for when assignment is only needed if not default value
    def set_kv_temp_data_if_not_default(k, v):
        if v != 'default':
            if v == 'true':
                temp_data[k] = True
            elif v == 'false':
                temp_data[k] = False
            else:
                temp_data[k] = v
    def set_kv_data_fvextfile(k, v):
        # Error checking on TeX side should be enough, but be careful anyway
        try:
            v = int(v)                    
        except ValueError:
            print('* PythonTeX error')
            print('    Unable to parse package option fvextfile.')
            return sys.exit(1)
        if v < 0:
            settings[k] = sys.maxsize
        elif v == 0:
            settings[k] = 1
            print('* PythonTeX warning')
            print('    Invalid value for package option fvextfile.')
            temp_data['warnings'] += 1
        else:
            settings[k] = v
    def set_kv_pygments(k, v):
        input_family, lexer_opts, options = v.replace(' ','').split('|')
        lexer = None
        lex_dict = {}
        opt_dict = {}
        if lexer_opts:
            for l in lexer_opts.split(','):
                if '=' in l:
                    k, v = l.split('=', 1)
                    if k == 'lexer':
                        lexer = l
                    else:
                        lex_dict[k] = v
                else:
                    lexer = l
        if options:
            for o in options.split(','):
                if '=' in o:
                    k, v = o.split('=', 1)
                    if v in ('true', 'True'):
                        v = True
                    elif v in ('false', 'False'):
                        v = False
                else:
                    k = option
                    v = True
                opt_dict[k] = v
        if input_family != ':GLOBAL':
            if 'lexer' in pygments_settings[':GLOBAL']:
                lexer = pygments_settings[':GLOBAL']['lexer']
            lex_dict.update(pygments_settings[':GLOBAL']['lexer_options'])
            opt_dict.update(pygments_settings[':GLOBAL']['formatter_options'])
            if 'style' not in opt_dict:
                opt_dict['style'] = 'default'
            opt_dict['commandprefix'] = 'PYG' + opt_dict['style']
        if lexer is not None:
            pygments_settings[input_family]['lexer'] = lexer
        pygments_settings[input_family]['lexer_options'] = lex_dict
        pygments_settings[input_family]['formatter_options'] = opt_dict
    settings_func['version'] = set_kv_data
    settings_func['outputdir'] = set_kv_data
    settings_func['workingdir'] = set_kv_data
    settings_func['gobble'] = set_kv_data
    settings_func['rerun'] = set_kv_temp_data_if_not_default
    settings_func['hashdependencies'] = set_kv_temp_data_if_not_default
    settings_func['makestderr'] = set_kv_data
    settings_func['stderrfilename'] = set_kv_data
    settings_func['keeptemps'] = set_kv_data
    settings_func['pyfuture'] = set_kv_data
    settings_func['pyconfuture'] = set_kv_data
    settings_func['pygments'] = set_kv_data
    settings_func['fvextfile'] = set_kv_data_fvextfile
    settings_func['pygglobal'] = set_kv_pygments
    settings_func['pygfamily'] = set_kv_pygments
    settings_func['pyconbanner'] = set_kv_data
    settings_func['pyconfilename'] = set_kv_data
    settings_func['depythontex'] = set_kv_data
    
    # Process settings
    for line in pytxsettings.split('\n'):
        if line:
            key, val = line.split('=', 1)
            try:
                settings_func[key](key, val)
            except KeyError:
                print('* PythonTeX warning')
                print('    Unknown option "' + key + '"')
                temp_data['warnings'] += 1

    # Check for compatility between the .pytxcode and the script
    if 'version' not in settings or settings['version'] != data['version']:
        print('* PythonTeX warning')
        print('    The version of the PythonTeX scripts does not match')
        print('    the last code saved by the document--run LaTeX to create')
        print('    an updated version.  Attempting to proceed.')
        sys.stdout.flush()
    
    # Store all results that haven't already been stored.
    data['settings'] = settings
    data['pygments_settings'] = pygments_settings
    
    # Create a tuple of vital quantities that invalidate old saved data
    # Don't need to include outputdir, because if that changes, no old output
    # fvextfile could be checked on a case-by-case basis, which would result
    # in faster output, but that would involve a good bit of additional 
    # logic, which probably isn't worth it for a feature that will rarely be
    # changed.
    data['vitals'] = (data['version'], data['encoding'], 
                      settings['gobble'], settings['fvextfile'])
    
    # Create tuples of vital quantities
    data['code_vitals'] = (settings['workingdir'], settings['keeptemps'],
                           settings['makestderr'], settings['stderrfilename'])
    data['cons_vitals'] = (settings['workingdir'])
    data['typeset_vitals'] = ()
    
    # Pass any customizations to types
    for k in engine_dict:
        engine_dict[k].customize(pyfuture=settings['pyfuture'],
                                 pyconfuture=settings['pyconfuture'],
                                 pyconbanner=settings['pyconbanner'],
                                 pyconfilename=settings['pyconfilename'])
    
    # Store code
    # Do this last, so that Pygments settings are available
    if pytxcode.startswith('=>PYTHONTEX#'):
        gobble = settings['gobble']
        temp_data['pytxcode'] = [Pytxcode(c, gobble) for c in pytxcode.split('=>PYTHONTEX#')[1:]]
    else:
        temp_data['pytxcode'] = []




def get_old_data(data, old_data, temp_data):
    '''
    Load data from the last run, if it exists, into the dict old_data.  
    Determine the path to the PythonTeX scripts, either by using a previously 
    found, saved path or via kpsewhich.
    
    The old data is used for determining when PythonTeX has been upgraded, 
    when any settings have changed, when code has changed (via hashes), and 
    what files may need to be cleaned up.  The location of the PythonTeX 
    scripts is needed so that they can be imported by the scripts created by 
    PythonTeX.  The location of the scripts is confirmed even if they were 
    previously located, to make sure that the path is still valid.  Finding 
    the scripts depends on having a TeX installation that includes the 
    Kpathsea library (TeX Live and MiKTeX, possibly others).
    
    All code that relies on old_data is written based on the assumption that
    if old_data exists and has the current PythonTeX version, then it 
    contains all needed information.  Thus, all code relying on old_data must
    check that it was loaded and that it has the current version.  If not, 
    code should adapt gracefully.
    '''

    # Create a string containing the name of the data file
    pythontex_data_file = os.path.join(data['settings']['outputdir'], 'pythontex_data.pkl')
    
    # Load the old data if it exists (read as binary pickle)
    if os.path.isfile(pythontex_data_file):
        f = open(pythontex_data_file, 'rb')
        old = pickle.load(f)
        f.close()
        # Check for compabilility
        if 'vitals' in old and data['vitals'] == old['vitals']:
            temp_data['loaded_old_data'] = True
            old_data.update(old)
        else:
            temp_data['loaded_old_data'] = False
            # Clean up all old files
            if 'files' in old:
                for key in old['files']:
                    for f in old['files'][key]:
                        f = os.path.expanduser(os.path.normcase(f))
                        if os.path.isfile(f):
                            os.remove(f)
            if 'pygments_files' in old:
                for key in old['pygments_files']:
                    for f in old['pygments_files'][key]:
                        f = os.path.expanduser(os.path.normcase(f))
                        if os.path.isfile(f):
                            os.remove(f)
    else:
        temp_data['loaded_old_data'] = False
    
    # Need the path with forward slashes, so escaping isn't necessary
    data['utilspath'] = sys.path[0].replace('\\', '/')




def modified_dependencies(key, data, old_data, temp_data):
    hashdependencies = temp_data['hashdependencies']
    if key not in old_data['dependencies']:
        return False
    else:
        old_dep_hash_dict = old_data['dependencies'][key]
        workingdir = data['settings']['workingdir']
        for dep in old_dep_hash_dict.keys():
            # We need to know if the path is relative (based off the 
            # working directory) or absolute.  We can't use 
            # os.path.isabs() alone for determining the distinction, 
            # because we must take into account the possibility of an
            # initial ~ (tilde) standing for the home directory.
            dep_file = os.path.expanduser(os.path.normcase(dep))
            if not os.path.isabs(dep_file):
                dep_file = os.path.join(workingdir, dep_file)
            if not os.path.isfile(dep_file):
                print('* PythonTeX error')
                print('    Cannot find dependency "' + dep + '"')
                print('    It belongs to ' + key.replace('#', ':'))
                print('    Relative paths to dependencies must be specified from the working directory.')
                temp_data['errors'] += 1
                # A removed dependency should trigger an error, but it 
                # shouldn't cause code to execute.  Running the code 
                # again would just give more errors when it can't find 
                # the dependency.  (There won't be issues when a 
                # dependency is added or removed, because that would 
                # involve modifying code, which would trigger 
                # re-execution.)
            elif hashdependencies:
                # Read and hash the file in binary.  Opening in text mode 
                # would require an unnecessary decoding and encoding cycle.
                f = open(dep_file, 'rb')
                hasher = sha1()
                hash = hasher(f.read()).hexdigest()
                f.close()
                if hash != old_dep_hash_dict[dep][1]:
                    return True
            else:
                mtime = os.path.getmtime(dep_file)
                if mtime != old_dep_hash_dict[dep][0]:
                    return True
        return False

def should_rerun(hash, old_hash, old_exit_status, key, rerun, data, old_data, temp_data):
    # #### Need to clean up arg passing here
    if rerun == 'never':
        if (hash != old_hash or modified_dependencies(key, data, old_data, temp_data)):
            print('* PythonTeX warning')
            print('    Session ' + key.replace('#', ':') + ' has rerun=never')
            print('    But its code or dependencies have been modified')
            temp_data['warnings'] += 1
        return False
    elif rerun == 'modified':
        if (hash != old_hash or modified_dependencies(key, data, old_data, temp_data)):
            return True
        else:
            return False
    elif rerun == 'errors':
        if (hash != old_hash or modified_dependencies(key, data, old_data, temp_data) or
                old_exit_status[0] != 0):
            return True
        else:
            return False
    elif rerun == 'warnings':
        if (hash != old_hash or modified_dependencies(key, data, old_data, temp_data) or
                old_exit_status != (0, 0)):
            return True
        else:
            return False
    elif rerun == 'always':
        return True




def hash_all(data, temp_data, old_data, engine_dict):
    '''
    Hash the code to see what has changed and needs to be updated.
    
    Save the hashes in hashdict.  Create update_code, a list of bools 
    regarding whether code should be executed.  Create update_pygments, a 
    list of bools determining what needs updated Pygments highlighting.  
    Update pygments_settings to account for Pygments (as opposed to PythonTeX) 
    commands and environments.
    '''

    # Note that the PythonTeX information that accompanies code must be 
    # hashed in addition to the code itself; the code could stay the same, 
    # but its context or args could change, which might require that code be 
    # executed.  All of the PythonTeX information is hashed except for the 
    # input line number.  Context-dependent code is going too far if 
    # it depends on that.
    
    # Create variables to more easily access parts of data
    pytxcode = temp_data['pytxcode']
    encoding = data['encoding']
    loaded_old_data = temp_data['loaded_old_data']
    rerun = temp_data['rerun']
    pygments_settings = data['pygments_settings']
    
    # Calculate cumulative hashes for all code that is executed
    # Calculate individual hashes for all code that will be typeset
    code_hasher = defaultdict(sha1)
    cons_hasher = defaultdict(sha1)
    cc_hasher = defaultdict(sha1)
    typeset_hasher = defaultdict(sha1)
    for c in pytxcode:
        if c.is_code:
            code_hasher[c.key_run].update(c.hashable_delims_run.encode(encoding))
            code_encoded = c.code.encode(encoding)
            code_hasher[c.key_run].update(code_encoded)
            if c.is_typeset:
                typeset_hasher[c.key_typeset].update(c.hashable_delims_typeset.encode(encoding))
                typeset_hasher[c.key_typeset].update(code_encoded)
        elif c.is_cons:
            cons_hasher[c.key_run].update(c.hashable_delims_run.encode(encoding))
            code_encoded = c.code.encode(encoding)
            cons_hasher[c.key_run].update(code_encoded)
            if c.is_typeset:
                typeset_hasher[c.key_typeset].update(c.hashable_delims_typeset.encode(encoding))
                typeset_hasher[c.key_typeset].update(code_encoded)
        elif c.is_cc:
            cc_hasher[c.cc_type].update(c.hashable_delims_run.encode(encoding))
            cc_hasher[c.cc_type].update(c.code.encode(encoding))
        elif c.is_typeset:
            typeset_hasher[c.key_typeset].update(c.hashable_delims_typeset.encode(encoding))
            typeset_hasher[c.key_typeset].update(c.code.encode(encoding))
        

    # Store hashes
    code_hash_dict = {}
    for key in code_hasher:
        input_family = key.split('#', 1)[0]
        code_hash_dict[key] = (code_hasher[key].hexdigest(), 
                               cc_hasher[input_family].hexdigest(),
                               engine_dict[input_family].get_hash())
    data['code_hash_dict'] = code_hash_dict
    
    cons_hash_dict = {}
    for key in cons_hasher:
        input_family = key.split('#', 1)[0]
        cons_hash_dict[key] = (cons_hasher[key].hexdigest(), 
                               cc_hasher[input_family].hexdigest(),
                               engine_dict[input_family].get_hash())
    data['cons_hash_dict'] = cons_hash_dict
    
    typeset_hash_dict = {}
    for key in typeset_hasher:
        typeset_hash_dict[key] = typeset_hasher[key].hexdigest()
    data['typeset_hash_dict'] = typeset_hash_dict
    
    
    # See what needs to be updated.
    # In the process, copy over macros and files that may be reused.
    code_update = {}
    cons_update = {}
    pygments_update = {}
    macros = defaultdict(list)
    files = defaultdict(list)
    pygments_macros = {}
    pygments_files = {}
    typeset_cache = {}
    dependencies = defaultdict(dict)
    exit_status = {}
    pygments_settings_changed = {}
    if loaded_old_data:
        old_macros = old_data['macros']
        old_files = old_data['files']
        old_pygments_macros = old_data['pygments_macros']
        old_pygments_files = old_data['pygments_files']
        old_typeset_cache = old_data['typeset_cache']
        old_dependencies = old_data['dependencies']
        old_exit_status = old_data['exit_status']
        old_code_hash_dict = old_data['code_hash_dict']
        old_cons_hash_dict = old_data['cons_hash_dict']
        old_typeset_hash_dict = old_data['typeset_hash_dict']
        old_pygments_settings = old_data['pygments_settings']
        for s in pygments_settings:
            if (s in old_pygments_settings and 
                    pygments_settings[s] == old_pygments_settings[s]):
                pygments_settings_changed[s] = False
            else:
                pygments_settings_changed[s] = True

    # If old data was loaded (and thus is compatible) determine what has 
    # changed so that only 
    # modified code may be executed.  Otherwise, execute everything.
    # We don't have to worry about checking for changes in pyfuture, because
    # custom code and default code are hashed.  The treatment of keeptemps
    # could be made more efficient (if changed to 'none', just delete old temp
    # files rather than running everything again), but given that it is 
    # intended as a debugging aid, that probable isn't worth it.
    # We don't have to worry about hashdependencies changing, because if it 
    # does the hashes won't match (file contents vs. mtime) and thus code will
    # be re-executed.
    if loaded_old_data and data['code_vitals'] == old_data['code_vitals']:
        # Compare the hash values, and set which code needs to be run
        for key in code_hash_dict:
            if (key in old_code_hash_dict and 
                    not should_rerun(code_hash_dict[key], old_code_hash_dict[key], old_exit_status[key], key, rerun, data, old_data, temp_data)):
                code_update[key] = False
                macros[key] = old_macros[key]
                files[key] = old_files[key]
                dependencies[key] = old_dependencies[key]
                exit_status[key] = old_exit_status[key]
            else:
                code_update[key] = True        
    else:        
        for key in code_hash_dict:
            code_update[key] = True
    
    if loaded_old_data and data['cons_vitals'] == old_data['cons_vitals']:
        # Compare the hash values, and set which code needs to be run
        for key in cons_hash_dict:
            if (key in old_cons_hash_dict and 
                    not should_rerun(cons_hash_dict[key], old_cons_hash_dict[key], old_exit_status[key], key, rerun, data, old_data, temp_data)):
                cons_update[key] = False
                macros[key] = old_macros[key]
                files[key] = old_files[key]
                typeset_cache[key] = old_typeset_cache[key]
                dependencies[key] = old_dependencies[key]
                exit_status[key] = old_exit_status[key]
            else:
                cons_update[key] = True        
    else:        
        for key in cons_hash_dict:
            cons_update[key] = True
    
    if loaded_old_data and data['typeset_vitals'] == old_data['typeset_vitals']:
        for key in typeset_hash_dict:
            input_family = key.split('#', 1)[0]
            if input_family in pygments_settings:
                if (not pygments_settings_changed[input_family] and
                        key in old_typeset_hash_dict and 
                        typeset_hash_dict[key] == old_typeset_hash_dict[key]):
                    pygments_update[key] = False
                    if key in old_pygments_macros:
                        pygments_macros[key] = old_pygments_macros[key]
                    if key in old_pygments_files:
                        pygments_files[key] = old_pygments_files[key]
                else:
                    pygments_update[key] = True
            else:
                pygments_update[key] = False
        # Make sure Pygments styles are up-to-date
        pygments_style_list = list(get_all_styles())
        if pygments_style_list != old_data['pygments_style_list']:
            pygments_style_defs = {}
            # Lazy import
            from pygments.formatters import LatexFormatter
            for s in pygments_style_list:
                formatter = LatexFormatter(style=s, commandprefix='PYG'+s)
                pygments_style_defs[s] = formatter.get_style_defs()
        else:
            pygments_style_defs = old_data['pygments_style_defs']
    else:
        for key in typeset_hash_dict:
            input_family = key.split('#', 1)[0]
            if input_family in pygments_settings:
                pygments_update[key] = True
            else:
                pygments_update[key] = False
        # Create Pygments styles
        pygments_style_list = list(get_all_styles())
        pygments_style_defs = {}
        # Lazy import
        from pygments.formatters import LatexFormatter
        for s in pygments_style_list:
            formatter = LatexFormatter(style=s, commandprefix='PYG'+s)
            pygments_style_defs[s] = formatter.get_style_defs()
    
    # Save to data
    temp_data['code_update'] = code_update
    temp_data['cons_update'] = cons_update
    temp_data['pygments_update'] = pygments_update
    data['macros'] = macros
    data['files'] = files
    data['pygments_macros'] = pygments_macros
    data['pygments_style_list'] = pygments_style_list
    data['pygments_style_defs'] = pygments_style_defs
    data['pygments_files'] = pygments_files
    data['typeset_cache'] = typeset_cache
    data['dependencies'] = dependencies
    data['exit_status'] = exit_status
    
    
    # Clean up for code that will be run again, and for code that no longer 
    # exists.
    if loaded_old_data:
        # Take care of code files
        for key in code_hash_dict:
            if code_update[key] and key in old_files:
                for f in old_files[key]:
                    f = os.path.expanduser(os.path.normcase(f))
                    if os.path.isfile(f):
                        os.remove(f)
        for key in old_code_hash_dict:
            if key not in code_hash_dict:
                for f in old_files[key]:
                    f = os.path.expanduser(os.path.normcase(f))
                    if os.path.isfile(f):
                        os.remove(f)
        # Take care of old console files
        for key in cons_hash_dict:
            if cons_update[key] and key in old_files:
                for f in old_files[key]:
                    f = os.path.expanduser(os.path.normcase(f))
                    if os.path.isfile(f):
                        os.remove(f)
        for key in old_cons_hash_dict:
            if key not in cons_hash_dict:
                for f in old_files[key]:
                    f = os.path.expanduser(os.path.normcase(f))
                    if os.path.isfile(f):
                        os.remove(f)
        # Take care of old Pygments files
        # The approach here is a little different since there isn't a 
        # Pygments-specific hash dict, but there is a Pygments-specific 
        # dict of lists of files.
        for key in pygments_update:
            if pygments_update[key] and key in old_pygments_files:
                for f in old_pygments_files[key]:
                    f = os.path.expanduser(os.path.normcase(f))
                    if os.path.isfile(f):
                        os.remove(f)
        for key in old_pygments_files:
            if key not in pygments_update:
                for f in old_pygments_files[key]:
                    f = os.path.expanduser(os.path.normcase(f))
                    if os.path.isfile(f):
                        os.remove(f)





def parse_code_write_scripts(data, temp_data, engine_dict):
    '''
    Parse the code file into separate scripts, and write them to file.
    '''
    code_dict = defaultdict(list)
    cc_dict_begin = defaultdict(list)
    cc_dict_end = defaultdict(list)
    cons_dict = defaultdict(list)
    pygments_list = []
    # Create variables to ease data access
    encoding = data['encoding']
    utilspath = data['utilspath']
    outputdir = data['settings']['outputdir']
    workingdir = data['settings']['workingdir']
    pytxcode = temp_data['pytxcode']
    code_update = temp_data['code_update']
    cons_update = temp_data['cons_update']
    pygments_update = temp_data['pygments_update']
    files = data['files']
    # We need to keep track of the last instance for each session, so 
    # that duplicates can be eliminated.  Some LaTeX environments process 
    # their content multiple times and thus will create duplicates.  We 
    # need to initialize everything at -1, since instances begin at zero.
    def negative_one():
        return -1
    last_instance = defaultdict(negative_one)
    for c in pytxcode:
        if c.input_instance_int > last_instance[c.key_run]:
            last_instance[c.key_run] = c.input_instance_int
            if c.is_code:
                if code_update[c.key_run]:
                    code_dict[c.key_run].append(c)
                if c.is_typeset and pygments_update[c.key_typeset]:
                    pygments_list.append(c)
            elif c.is_cons:
                # Only append to Pygments if not run, since Pygments is 
                # automatically taken care of during run for console content
                if cons_update[c.key_run]:
                    cons_dict[c.key_run].append(c)
                elif c.is_typeset and pygments_update[c.key_typeset]:
                    pygments_list.append(c)
            elif (c.is_pyg or c.is_verb) and pygments_update[c.key_typeset]:
                pygments_list.append(c)
            elif c.is_cc:
                if c.cc_pos == 'begin':
                    cc_dict_begin[c.cc_type].append(c)
                else:
                    cc_dict_end[c.cc_type].append(c)
    
    # Save
    temp_data['code_dict'] = code_dict
    temp_data['cc_dict_begin'] = cc_dict_begin
    temp_data['cc_dict_end'] = cc_dict_end
    temp_data['cons_dict'] = cons_dict
    temp_data['pygments_list'] = pygments_list

    # Save the code sessions that need to be updated
    # Keep track of the files that are created
    # Also accumulate error indices for handling stderr
    code_index_dict = {}
    for key in code_dict:
        input_family, input_session, input_restart = key.split('#')
        fname = os.path.join(outputdir, input_family + '_' + input_session + '_' + input_restart + '.' + engine_dict[input_family].extension)
        files[key].append(fname)
        sessionfile = open(fname, 'w', encoding=encoding)
        script, code_index = engine_dict[input_family].get_script(encoding,
                                                              utilspath,
                                                              workingdir,
                                                              cc_dict_begin[input_family],
                                                              code_dict[key],
                                                              cc_dict_end[input_family])
        for lines in script:
            sessionfile.write(lines)
        sessionfile.close()
        code_index_dict[key] = code_index
    temp_data['code_index_dict'] = code_index_dict




def do_multiprocessing(data, temp_data, old_data, engine_dict):
    jobname = data['jobname']
    encoding = data['encoding']
    outputdir = data['settings']['outputdir']
    workingdir = data['settings']['workingdir']
    keeptemps = data['settings']['keeptemps']
    fvextfile = data['settings']['fvextfile']
    pygments_settings = data['pygments_settings']
    verbose = temp_data['verbose']
    
    code_dict = temp_data['code_dict']
    cons_dict = temp_data['cons_dict']
    cc_dict_begin = temp_data['cc_dict_begin']
    cc_dict_end = temp_data['cc_dict_end']
    pygments_list = temp_data['pygments_list']
    pygments_style_defs = data['pygments_style_defs']

    files = data['files']
    macros = data['macros']
    pygments_files = data['pygments_files']
    pygments_macros = data['pygments_macros']
    typeset_cache = data['typeset_cache']
    
    errors = temp_data['errors']
    warnings = temp_data['warnings']
    
    makestderr = data['settings']['makestderr']
    stderrfilename = data['settings']['stderrfilename']
    code_index_dict = temp_data['code_index_dict']
    
    hashdependencies = temp_data['hashdependencies']
    dependencies = data['dependencies']
    exit_status = data['exit_status']
    start_time = data['start_time']
    
    
    # Set maximum number of concurrent processes for multiprocessing
    # Accoding to the docs, cpu_count() may raise an error
    try:
        max_processes = multiprocessing.cpu_count()
    except NotImplementedError:
        max_processes = 1
    pool = multiprocessing.Pool(max_processes)
    tasks = []
    
    # If verbose, print a list of processes
    if verbose:
        print('\n* PythonTeX will run the following processes:')
    
    # Add code processes.  Note that everything placed in the codedict 
    # needs to be executed, based on previous testing, except for custom code.
    for key in code_dict:
        input_family = key.split('#')[0]
        # Uncomment the following for debugging, and comment out what follows
        '''run_code(encoding, outputdir, workingdir, code_dict[key],
                                                 engine_dict[input_family].language,
                                                 engine_dict[input_family].command,
                                                 engine_dict[input_family].created,
                                                 engine_dict[input_family].extension,
                                                 makestderr, stderrfilename,
                                                 code_index_dict[key],
                                                 engine_dict[input_family].errors,
                                                 engine_dict[input_family].warnings,
                                                 engine_dict[input_family].linenumbers,
                                                 engine_dict[input_family].lookbehind,
                                                 keeptemps, hashdependencies)'''
        tasks.append(pool.apply_async(run_code, [encoding, outputdir, 
                                                 workingdir, code_dict[key],
                                                 engine_dict[input_family].language,
                                                 engine_dict[input_family].command,
                                                 engine_dict[input_family].created,
                                                 engine_dict[input_family].extension,
                                                 makestderr, stderrfilename,
                                                 code_index_dict[key],
                                                 engine_dict[input_family].errors,
                                                 engine_dict[input_family].warnings,
                                                 engine_dict[input_family].linenumbers,
                                                 engine_dict[input_family].lookbehind,
                                                 keeptemps, hashdependencies]))
        if verbose:
            print('    - Code process ' + key.replace('#', ':'))
    
    # Add console processes
    for key in cons_dict:
        input_family = key.split('#')[0]
        if engine_dict[input_family].language.startswith('python'):
            if input_family in pygments_settings:
                # Uncomment the following for debugging
                '''python_console(jobname, encoding, outputdir, workingdir, 
                               fvextfile, pygments_settings[input_family],
                               cc_dict_begin[input_family], cons_dict[key],
                               cc_dict_end[input_family], engine_dict[input_family].startup,
                               engine_dict[input_family].banner, 
                               engine_dict[input_family].filename)'''
                tasks.append(pool.apply_async(python_console, [jobname, encoding,
                                                               outputdir, workingdir,
                                                               fvextfile,
                                                               pygments_settings[input_family],
                                                               cc_dict_begin[input_family],
                                                               cons_dict[key],
                                                               cc_dict_end[input_family],
                                                               engine_dict[input_family].startup,
                                                               engine_dict[input_family].banner,
                                                               engine_dict[input_family].filename]))
            else:
                tasks.append(pool.apply_async(python_console, [jobname, encoding,
                                                               outputdir, workingdir,
                                                               fvextfile,
                                                               None,
                                                               cc_dict_begin[input_family],
                                                               cons_dict[key],
                                                               cc_dict_end[input_family],
                                                               engine_dict[input_family].startup,
                                                               engine_dict[input_family].banner,
                                                               engine_dict[input_family].filename]))  
        else:
            print('* PythonTeX error')
            print('    Currently, non-Python consoles are not supported')
            errors += 1
        if verbose:
            print('    - Console process ' + key.replace('#', ':'))
    
    # Add a Pygments process
    if pygments_list:
        tasks.append(pool.apply_async(do_pygments, [encoding, outputdir, 
                                                    fvextfile,
                                                    pygments_list,
                                                    pygments_settings,
                                                    typeset_cache]))
        if verbose:
            print('    - Pygments process')
    
    # Execute the processes
    pool.close()
    pool.join()
    
    # Get the outputs of processes
    # Get the files and macros created.  Get the number of errors and warnings
    # produced.  Get any messages returned.  Get the exit_status, which is a 
    # dictionary of code that failed and thus must be run again (its hash is
    # set to a null string).  Keep track of whether there were any new files,
    # so that the last time of file creation in .pytxmcr can be updated.
    new_files = False
    messages = []
    for task in tasks:
        result = task.get()
        if result['process'] == 'code':
            key = result['key']
            files[key].extend(result['files'])
            if result['files']:
                new_files = True
            macros[key].extend(result['macros'])
            dependencies[key] = result['dependencies']
            errors += result['errors']
            warnings += result['warnings']
            exit_status[key] = (result['errors'], result['warnings'])
            messages.extend(result['messages'])            
        elif result['process'] == 'console':
            key = result['key']
            files[key].extend(result['files'])
            if result['files']:
                new_files = True
            macros[key].extend(result['macros'])
            pygments_files.update(result['pygments_files'])
            pygments_macros.update(result['pygments_macros'])
            dependencies[key] = result['dependencies']
            typeset_cache[key] = result['typeset_cache']
            errors += result['errors']
            warnings += result['warnings']
            exit_status[key] = (result['errors'], result['warnings'])
            messages.extend(result['messages'])
        elif result['process'] == 'pygments':
            pygments_files.update(result['pygments_files'])
            for k in result['pygments_files']:
                if result['pygments_files'][k]:
                    new_files = True
                    break
            pygments_macros.update(result['pygments_macros'])
            errors += result['errors']
            warnings += result['warnings']
            messages.extend(result['messages'])        
    
    # Do a quick check to see if any dependencies were modified since the
    # beginning of the run.  If so, reset them so they will run next time and
    # issue a warning
    unresolved_dependencies = False
    unresolved_sessions= []
    for key in dependencies:
        for dep, val in dependencies[key].items():
            if val[0] > start_time:
                unresolved_dependencies = True
                dependencies[key][dep] = (None, None)
                unresolved_sessions.append(key.replace('#', ':'))
    if unresolved_dependencies:
        print('* PythonTeX warning')
        print('    The following have dependencies that have been modified')
        print('    Run PythonTeX again to resolve dependencies')
        for s in set(unresolved_sessions):
            print('    - ' + s)
        warnings += 1
    
    
    # Save all content (only needs to be done if code was indeed run).
    # Save a commented-out time corresponding to the last time PythonTeX ran
    # and created files, so that tools like latexmk can easily detect when 
    # another run is needed.
    if tasks:
        if new_files or not temp_data['loaded_old_data']:
            last_new_file_time = start_time
        else:
            last_new_file_time = old_data['last_new_file_time']
        data['last_new_file_time'] = last_new_file_time
        
        macro_file = open(os.path.join(outputdir, jobname + '.pytxmcr'), 'w', encoding=encoding)
        macro_file.write('%Last time of file creation:  ' + str(last_new_file_time) + '\n\n')
        for key in macros:
            macro_file.write(''.join(macros[key]))
        macro_file.close()
        
        pygments_macro_file = open(os.path.join(outputdir, jobname + '.pytxpyg'), 'w', encoding=encoding)
        # Only save Pygments styles that are used
        style_set = set([pygments_settings[k]['formatter_options']['style'] for k in pygments_settings if k != ':GLOBAL'])
        for key in pygments_style_defs:
            if key in style_set:
                pygments_macro_file.write(''.join(pygments_style_defs[key]))
        for key in pygments_macros:
            pygments_macro_file.write(''.join(pygments_macros[key]))
        pygments_macro_file.close()
        
        pythontex_data_file = os.path.join(outputdir, 'pythontex_data.pkl')
        f = open(pythontex_data_file, 'wb')
        pickle.dump(data, f, -1)
        f.close()
    
    # Print any errors and warnings.
    if messages:
        print('\n'.join(messages))
    sys.stdout.flush()
    # Store errors and warnings back into temp_data
    # This is needed because they are ints and thus immutable
    temp_data['errors'] = errors
    temp_data['warnings'] = warnings




def run_code(encoding, outputdir, workingdir, code_list, language, command, 
             command_created, extension, makestderr, stderrfilename, 
             code_index, errorsig, warningsig, linesig, stderrlookbehind, 
             keeptemps, hashdependencies):
    '''
    Function for multiprocessing code files
    '''
    import shlex
    
    # Create what's needed for storing results
    input_family = code_list[0].input_family
    input_session = code_list[0].input_session
    key_run = code_list[0].key_run
    files = []
    macros = []
    dependencies = {}
    errors = 0
    warnings = 0
    unknowns = 0
    messages = []
    
    # Create message lists only for stderr, one for undelimited stderr and 
    # one for delimited, so it's easy to keep track of if there is any 
    # stderr.  These are added onto messages at the end.
    err_messages_ud = []
    err_messages_d = []
    
    # We need to let the user know we are switching code files
    # We check at the end to see if there were indeed any errors and warnings
    # and if not, clear messages.
    messages.append('\n----  Messages for ' + key_run.replace('#', ':') + '  ----')
    
    # Open files for stdout and stderr, run the code, then close the files
    basename = key_run.replace('#', '_')
    out_file_name = os.path.join(outputdir, basename + '.out')
    err_file_name = os.path.join(outputdir, basename + '.err')
    out_file = open(out_file_name, 'w', encoding=encoding)
    err_file = open(err_file_name, 'w', encoding=encoding)
    # Note that command is a string, which must be converted to list
    # Must double-escape any backslashes so that they survive `shlex.split()`
    script = os.path.join(outputdir, basename)
    # `shlex.split()` only works with Unicode after 2.7.2
    if (sys.version_info.major == 2 and sys.version_info.micro < 3):
        exec_cmd = shlex.split(bytes(command.format(file=script.replace('\\', '\\\\'))))
        exec_cmd = [unicode(elem) for elem in exec_cmd]
    else:
        exec_cmd = shlex.split(command.format(file=script.replace('\\', '\\\\')))
    # Add any created files due to the command
    # This needs to be done before attempts to execute, to prevent orphans
    for f in command_created:
        files.append(f.format(file=script))
    try:
        proc = subprocess.Popen(exec_cmd, stdout=out_file, stderr=err_file)
    except WindowsError as e:
        if e.errno == 2:
            # Batch files won't be found when called without extension. They
            # would be found if `shell=True`, but then getting the right
            # exit code is tricky.  So we perform some `cmd` trickery that
            # is essentially equivalent to `shell=True`, but gives correct 
            # exit codes.  Note that `subprocess.Popen()` works with strings
            # under Windows; a list is not required.
            exec_cmd_string = ' '.join(exec_cmd)
            exec_cmd_string = 'cmd /C "@echo off & call {0} & if errorlevel 1 exit 1"'.format(exec_cmd_string)
            proc = subprocess.Popen(exec_cmd_string, stdout=out_file, stderr=err_file)
        else:
            raise
        
    proc.wait()        
    out_file.close()
    err_file.close()
    
    # Process saved stdout into file(s) that are included in the TeX document.
    #
    # Go through the saved output line by line, and save any printed content 
    # to its own file, named based on instance.
    #
    # The very end of the stdout lists dependencies, if any, so we start by
    # removing and processing those.
    if not os.path.isfile(out_file_name):
        messages.append('* PythonTeX error')
        messages.append('    Missing output file for ' + key_run.replace('#', ':'))
        errors += 1
    else:
        f = open(out_file_name, 'r', encoding=encoding)
        out = f.read()
        f.close()
        try:
            out, created = out.rsplit('=>PYTHONTEX:CREATED#\n', 1)
            out, deps = out.rsplit('=>PYTHONTEX:DEPENDENCIES#\n', 1)
            valid_stdout = True
        except:
            valid_stdout = False
            if proc.returncode == 0:
                raise ValueError('Missing "created" and/or "dependencies" delims in stdout; invalid template?')
                    
        if valid_stdout:
            # Add created files to created list
            for c in created.splitlines():
                files.append(c)
            
            # Create a set of dependencies, to eliminate duplicates in the event
            # that there are any.  This is mainly useful when dependencies are
            # automatically determined (for example, through redefining open()), 
            # may be specified multiple times as a result, and are hashed (and 
            # of a large enough size that hashing time is non-negligible).
            deps = set([dep for dep in deps.splitlines()])
            # Process dependencies; get mtimes and (if specified) hashes
            for dep in deps:
                dep_file = os.path.expanduser(os.path.normcase(dep))
                if not os.path.isabs(dep_file):
                    dep_file = os.path.join(workingdir, dep_file)
                if not os.path.isfile(dep_file):
                    # If we can't find the file, we return a null hash and issue 
                    # an error.  We don't need to change the exit status.  If the 
                    # code does depend on the file, there will be a separate 
                    # error when the code attempts to use the file.  If the code 
                    # doesn't really depend on the file, then the error will be 
                    # raised again anyway the next time PythonTeX runs when the 
                    # dependency is listed but not found.
                    dependencies[dep] = (None, None)
                    messages.append('* PythonTeX error')
                    messages.append('    Cannot find dependency "' + dep + '"')
                    messages.append('    It belongs to ' + key_run.replace('#', ':'))
                    messages.append('    Relative paths to dependencies must be specified from the working directory.')
                    errors += 1                
                elif hashdependencies:
                    # Read and hash the file in binary.  Opening in text mode 
                    # would require an unnecessary decoding and encoding cycle.
                    hasher = sha1()
                    f = open(dep_file, 'rb')
                    hasher.update(f.read())
                    f.close()
                    dependencies[dep] = (os.path.getmtime(dep_file), hasher.hexdigest())
                else:
                    dependencies[dep] = (os.path.getmtime(dep_file), '')
            
            for block in out.split('=>PYTHONTEX:STDOUT#')[1:]:
                if block:
                    delims, content = block.split('#\n', 1)
                    if content:
                        input_instance, input_command = delims.split('#')
                        if input_instance.endswith('CC'):
                            messages.append('* PythonTeX warning')
                            messages.append('    Custom code for "' + input_family + '" attempted to print or write to stdout')
                            messages.append('    This is not supported; use a normal code command or environment')
                            messages.append('    The following content was written:')
                            messages.append('')
                            messages.extend(['    ' + l for l in content.splitlines()])
                            warnings += 1
                        elif input_command == 'i':
                            content = r'\pytx@SVMCR{pytx@MCR@' + key_run.replace('#', '@') + '@' + input_instance + '}\n' + content.rstrip('\n') + '\\endpytx@SVMCR\n\n'
                            macros.append(content)
                        else:
                            fname = os.path.join(outputdir, basename + '_' + input_instance + '.stdout')
                            f = open(fname, 'w', encoding=encoding)
                            f.write(content)
                            f.close()
                            files.append(fname)

    # Process stderr
    if not os.path.isfile(err_file_name):
        messages.append('* PythonTeX error')
        messages.append('    Missing stderr file for ' + key_run.replace('#', ':'))
        errors += 1
    else:
        # Open error and code files.
        f = open(err_file_name, encoding=encoding)
        err = f.readlines()
        f.close()
        # Divide stderr into an undelimited and a delimited portion
        found = False
        for n, line in enumerate(err):
            if line.startswith('=>PYTHONTEX:STDERR#'):
                found = True
                err_ud = err[:n]
                err_d = err[n:]
                break
        if not found:
            err_ud = err
            err_d = []
        # Create a dict for storing any stderr content that will be saved
        err_dict = defaultdict(list)
        # Create the full basename that will be replaced in stderr
        # We need two versions, one with the correct slashes for the OS,
        # and one with the opposite slashes.  This is needed when a language
        # doesn't obey the OS's slash convention in paths given in stderr.  
        # For example, Windows uses backslashes, but Ruby under Windows uses 
        # forward in paths given in stderr.
        fullbasename_correct = os.path.join(outputdir, basename)
        if '\\' in fullbasename_correct:
            fullbasename_reslashed = fullbasename_correct.replace('\\', '/')
        else:
            fullbasename_reslashed = fullbasename_correct.replace('/', '\\')
        
        if err_ud:
            it = iter(code_index.items())
            index_now = next(it)
            index_next = index_now
            start_errgobble = None
            for n, line in enumerate(err_ud):
                if basename in line:
                    # Get the gobbleation.  This is used to determine if 
                    # other lines containing the basename are a continuation,
                    # or separate messages.
                    errgobble = match('(\s*)', line).groups()[0]
                    if start_errgobble is None:
                        start_errgobble = errgobble
                    # Only issue a message and track down the line numer if
                    # this is indeed the start of a new message, rather than
                    # a continuation of an old message that happens to 
                    # contain the basename
                    if errgobble == start_errgobble:
                        # Determine the corresponding line number in the document
                        found = False
                        for pattern in linesig:
                            try:
                                errlinenum = int(search(pattern, line).groups()[0])
                                found = True
                                break
                            except:
                                pass
                        if found:
                            while index_next[1].lines_total < errlinenum:
                                try:
                                    index_now, index_next = index_next, next(it)
                                except:
                                    break
                            if errlinenum > index_now[1].lines_total + index_now[1].lines_input:
                                doclinenum = str(index_now[1].input_line_int + index_now[1].lines_input)
                            else:
                                doclinenum = str(index_now[1].input_line_int + errlinenum - index_now[1].lines_total - 1)
                            input_file = index_now[1].input_file
                        else:
                            doclinenum = '??'
                            input_file = '??'
                        
                        # Try to determine if we are dealing with an error or a 
                        # warning.
                        found = False
                        index = n
                        if stderrlookbehind:
                            while index >= 0:
                                # The order here is important.  If a line matches 
                                # both the error and warning patterns, default to 
                                # error.
                                past_line = err_ud[index]
                                if (index < n and basename in past_line):
                                    break
                                for pattern in warningsig:
                                    if pattern in past_line:
                                        warnings += 1
                                        alert_type = 'warning'
                                        found = True
                                        break
                                for pattern in errorsig:
                                    if pattern in past_line:
                                        errors += 1
                                        alert_type = 'error'
                                        found = True
                                        break
                                if found:
                                    break
                                index -= 1
                        else:
                            while index < len(err_ud):
                                # The order here is important.  If a line matches 
                                # both the error and warning patterns, default to 
                                # error.
                                future_line = err_ud[index]
                                if (index > n and basename in future_line and 
                                        future_line.startswith(start_errgobble)):
                                    break
                                for pattern in warningsig:
                                    if pattern in future_line:
                                        warnings += 1
                                        alert_type = 'warning'
                                        found = True
                                        break
                                for pattern in errorsig:
                                    if pattern in future_line:
                                        errors += 1
                                        alert_type = 'error'
                                        found = True
                                        break
                                if found:
                                    break
                                index += 1
                        # If an error or warning wasn't positively identified,
                        # increment unknowns.
                        if not found:
                            unknowns += 1
                            alert_type = 'unknown'
                        if input_file:
                            err_messages_ud.append('* PythonTeX stderr - {0} on line {1} in "{2}":'.format(alert_type, doclinenum, input_file))
                        else:
                            err_messages_ud.append('* PythonTeX stderr - {0} on line {1}:'.format(alert_type, doclinenum))
                    err_messages_ud.append('  ' + line.replace(outputdir, '<outputdir>').rstrip('\n'))
                else:
                    err_messages_ud.append('  ' + line.rstrip('\n'))
            
            # Create .stderr
            if makestderr and err_messages_ud:
                process = False
                it = iter(code_index.items())
                index_now = next(it)
                index_next = index_now
                it_last = it
                index_now_last = index_now
                index_next_last = index_next
                err_key_last_int = -1
                for n, line in enumerate(err_ud):
                    if basename in line:
                        # Determine the corresponding line number in the document
                        found = False
                        for pattern in linesig:
                            try:
                                errlinenum = int(search(pattern, line).groups()[0])
                                found = True
                                break
                            except:
                                pass
                        if found:
                            if index_next[1].lines_total >= errlinenum:
                                it = it_last
                                index_now = index_now_last
                                index_next = index_next_last
                            else:
                                it_last = it
                                index_now_last = index_now
                                index_next_last = index_next
                            while index_next[1].lines_total < errlinenum:
                                try:
                                    index_now, index_next = index_next, next(it)
                                except:
                                    index_now = index_next
                                    break
                            if index_now[0].endswith('CC'):
                                process = False
                            else:
                                process = True
                                if len(index_now[1].input_command) > 1:
                                    if errlinenum > index_now[1].lines_total + index_now[1].lines_input:
                                        codelinenum = str(index_now[1].lines_user + index_now[1].lines_input + 1)
                                    else:
                                        codelinenum = str(index_now[1].lines_user + errlinenum - index_now[1].lines_total - index_now[1].inline_count)
                                else:
                                    codelinenum = '1'
                        else:
                            codelinenum = '??'
                            messages.append('* PythonTeX error')
                            messages.append('    Line number ' + str(errlinenum) + ' could not be synced with the document')
                            messages.append('    Content from stderr is not delimited, and cannot be resolved')
                            errors += 1
                            process = False
                        
                        if process:
                            if int(index_now[0]) > err_key_last_int:
                                err_key = basename + '_' + index_now[0]
                                err_key_last_int = int(index_now[0])
                            line = line.replace(str(errlinenum), str(codelinenum), 1)
                            if fullbasename_correct in line:
                                fullbasename = fullbasename_correct
                            else:
                                fullbasename = fullbasename_reslashed
                            if stderrfilename == 'full':
                                line = line.replace(fullbasename, basename)
                            elif stderrfilename == 'session':
                                line = line.replace(fullbasename, input_session)
                            elif stderrfilename == 'genericfile':
                                line = line.replace(fullbasename + '.' + extension, '<file>')
                            elif stderrfilename == 'genericscript':
                                line = line.replace(fullbasename + '.' + extension, '<script>')
                            err_dict[err_key].append(line)
                    elif process:
                        err_dict[err_key].append(line)
        
        if err_d:
            start_errgobble = None
            msg = []
            found_basename = False
            for n, line in enumerate(err_d):
                if line.startswith('=>PYTHONTEX:STDERR#'):
                    # Store the last group of messages.  Messages
                    # can't be directly appended to the main list, because
                    # a PythonTeX message must be inserted at the beginning 
                    # of each chunk of stderr that never references
                    # the script that was executed.  If the script is never
                    # referenced, then line numbers aren't automatically 
                    # synced.  These types of situations are created by 
                    # warnings.warn() etc.
                    if msg:
                        if not found_basename:
                            # Get line number for command or beginning of
                            # environment
                            input_instance = last_delim.split('#')[1]
                            doclinenum = str(code_index[input_instance].input_line_int)
                            input_file = code_index[input_instance].input_file
                            # Try to identify alert.  We have to parse all
                            # lines for signs of errors and warnings.  This 
                            # may result in overcounting, but it's the best
                            # we can do--otherwise, we could easily 
                            # undercount, or, finding a warning, miss a 
                            # subsequent error.  When this code is actually
                            # used, it's already a sign that normal parsing
                            # has failed.
                            found_error = False
                            found_warning = False
                            for l in msg:
                                for pattern in warningsig:
                                    if pattern in l:
                                        warnings += 1
                                        found_warning = True
                                for pattern in errorsig:
                                    if pattern in l:
                                        errors += 1
                                        found_warning = True
                            if found_error:
                                alert_type = 'error'
                            elif found_warning:
                                alert_type = 'warning'
                            else:
                                unknowns += 1
                                alert_type = 'unknown'
                            if input_file:
                                err_messages_d.append('* PythonTeX stderr - {0} near line {1} in "{2}":'.format(alert_type, doclinenum, input_file))
                            else:
                                err_messages_d.append('* PythonTeX stderr - {0} near line {1}:'.format(alert_type, doclinenum))
                        err_messages_d.extend(msg)
                    msg = []
                    found_basename = False
                    # Never process delimiting info until it is used
                    # Rather, store the index of the last delimiter
                    last_delim = line
                elif basename in line:
                    found_basename = True
                    # Get the gobbleation.  This is used to determine if 
                    # other lines containing the basename are a continuation,
                    # or separate messages.
                    errgobble = match('(\s*)', line).groups()[0]
                    if start_errgobble is None:
                        start_errgobble = errgobble
                    # Only issue a message and track down the line numer if
                    # this is indeed the start of a new message, rather than
                    # a continuation of an old message that happens to 
                    # contain the basename
                    if errgobble == start_errgobble:
                        # Determine the corresponding line number in the document
                        found = False
                        for pattern in linesig:
                            try:
                                errlinenum = int(search(pattern, line).groups()[0])
                                found = True
                                break
                            except:
                                pass
                        if found:
                            # Get info from last delim
                            input_instance, input_command = last_delim.split('#')[1:-1]
                            # Calculate the line number in the document
                            ei = code_index[input_instance]
                            if errlinenum > ei.lines_total + ei.lines_input:
                                doclinenum = str(ei.input_line_int + ei.lines_input)
                            else:
                                doclinenum = str(ei.input_line_int + errlinenum - ei.lines_total - 1)
                            input_file = ei.input_file
                        else:
                            doclinenum = '??'
                            input_file = '??'
                        
                        # Try to determine if we are dealing with an error or a 
                        # warning.
                        found = False
                        index = n
                        if stderrlookbehind:
                            while index >= 0:
                                # The order here is important.  If a line matches 
                                # both the error and warning patterns, default to 
                                # error.
                                past_line = err_d[index]
                                if (past_line.startswith('=>PYTHONTEX:STDERR#') or 
                                        (index < n and basename in past_line)):
                                    break
                                for pattern in warningsig:
                                    if pattern in past_line:
                                        warnings += 1
                                        alert_type = 'warning'
                                        found = True
                                        break
                                for pattern in errorsig:
                                    if pattern in past_line:
                                        errors += 1
                                        alert_type = 'error'
                                        found = True
                                        break
                                if found:
                                    break
                                index -= 1
                        else:
                            while index < len(err_d):
                                # The order here is important.  If a line matches 
                                # both the error and warning patterns, default to 
                                # error.
                                future_line = err_d[index]
                                if (future_line.startswith('=>PYTHONTEX:STDERR#') or 
                                        (index > n and basename in future_line and future_line.startswith(start_errgobble))):
                                    break
                                for pattern in warningsig:
                                    if pattern in future_line:
                                        warnings += 1
                                        alert_type = 'warning'
                                        found = True
                                        break
                                for pattern in errorsig:
                                    if pattern in future_line:
                                        errors += 1
                                        alert_type = 'error'
                                        found = True
                                        break
                                if found:
                                    break
                                index += 1
                        # If an error or warning wasn't positively identified,
                        # assume error for safety but indicate uncertainty.
                        if not found:
                            unknowns += 1
                            alert_type = 'unknown'
                        if input_file:
                            msg.append('* PythonTeX stderr - {0} on line {1} in "{2}":'.format(alert_type, doclinenum, input_file))
                        else:
                            msg.append('* PythonTeX stderr - {0} on line {1}:'.format(alert_type, doclinenum))
                    # Clean up the stderr format a little, to keep it compact
                    line = line.replace(outputdir, '<outputdir>').rstrip('\n')
                    if '/<outputdir>' in line or '\\<outputdir>' in line:
                        line = sub(r'(?:(?:[A-Z]:\\)|(?:~?/)).*<outputdir>', '<outputdir>', line)
                    msg.append('  ' + line)
                else:
                    msg.append('  ' + line.rstrip('\n'))
            # Deal with any leftover messages
            if msg:
                if not found_basename:
                    # Get line number for command or beginning of
                    # environment
                    input_instance = last_delim.split('#')[1]
                    doclinenum = str(code_index[input_instance].input_line_int)
                    input_file = code_index[input_instance].input_file
                    # Try to identify alert.  We have to parse all
                    # lines for signs of errors and warnings.  This 
                    # may result in overcounting, but it's the best
                    # we can do--otherwise, we could easily 
                    # undercount, or, finding a warning, miss a 
                    # subsequent error.  When this code is actually
                    # used, it's already a sign that normal parsing
                    # has failed.
                    found_error = False
                    found_warning = False
                    for l in msg:
                        for pattern in warningsig:
                            if pattern in l:
                                warnings += 1
                                found_warning = True
                        for pattern in errorsig:
                            if pattern in l:
                                errors += 1
                                found_warning = True
                    if found_error:
                        alert_type = 'error'
                    elif found_warning:
                        alert_type = 'warning'
                    else:
                        unknowns += 1
                        alert_type = 'unknown'
                    if input_file:
                        err_messages_d.append('* PythonTeX stderr - {0} near line {1} in "{2}":'.format(alert_type, doclinenum, input_file))
                    else:
                        err_messages_d.append('* PythonTeX stderr - {0} near line {1}:'.format(alert_type, doclinenum))
                err_messages_d.extend(msg)
            
            # Create .stderr
            if makestderr and err_messages_d:
                process = False
                for n, line in enumerate(err_d):
                    if line.startswith('=>PYTHONTEX:STDERR#'):
                        input_instance, input_command = line.split('#')[1:-1]
                        if input_instance.endswith('CC'):
                            process = False
                        else:
                            process = True
                            err_key = basename + '_' + input_instance
                    elif process and basename in line:
                        found = False
                        for pattern in linesig:
                            try:
                                errlinenum = int(search(pattern, line).groups()[0])
                                found = True
                                break
                            except:
                                pass
                        if found:
                            # Calculate the line number in the document
                            # Account for inline
                            ei = code_index[input_instance]
                            # Store the `input_instance` in case it's 
                            # incremented later
                            last_input_instance = input_instance
                            # If the error or warning was actually triggered
                            # later on (for example, multiline string with
                            # missing final delimiter), look ahead and 
                            # determine the correct input_instance, so that
                            # we get the correct line number.  We don't
                            # associate the created stderr with this later
                            # instance, however, but rather with the instance
                            # in which the error began.  Doing that might 
                            # possibly be preferable in some cases, but would
                            # also require that the current stderr be split
                            # between multiple instances, requiring extra
                            # parsing.
                            while errlinenum > ei.lines_total + ei.lines_input:
                                next_input_instance = str(int(input_instance) + 1)
                                if next_input_instance in code_index:
                                    next_ei = code_index[next_input_instance]
                                    if errlinenum > next_ei.lines_total:
                                        input_instance = next_input_instance
                                        ei = next_ei
                                    else:
                                        break
                                else:
                                    break
                            if len(input_command) > 1:
                                if errlinenum > ei.lines_total + ei.lines_input:
                                    codelinenum = str(ei.lines_user + ei.lines_input + 1)
                                else:
                                    codelinenum = str(ei.lines_user + errlinenum - ei.lines_total - ei.inline_count)
                            else:
                                codelinenum = '1'
                            # Reset `input_instance`, in case incremented
                            input_instance = last_input_instance
                        else:
                            codelinenum = '??'
                            messages.append('* PythonTeX notice')
                            messages.append('    Line number ' + str(errlinenum) + ' could not be synced with the document')
                        
                        line = line.replace(str(errlinenum), str(codelinenum), 1)
                        if fullbasename_correct in line:
                            fullbasename = fullbasename_correct
                        else:
                            fullbasename = fullbasename_reslashed
                        if stderrfilename == 'full':
                            line = line.replace(fullbasename, basename)
                        elif stderrfilename == 'session':
                            line = line.replace(fullbasename, input_session)
                        elif stderrfilename == 'genericfile':
                            line = line.replace(fullbasename + '.' + extension, '<file>')
                        elif stderrfilename == 'genericscript':
                            line = line.replace(fullbasename + '.' + extension, '<script>')
                        err_dict[err_key].append(line)
                    elif process:
                        err_dict[err_key].append(line)
        if err_dict:
            for err_key in err_dict:
                stderr_file_name = os.path.join(outputdir, err_key + '.stderr')
                f = open(stderr_file_name, 'w', encoding=encoding)
                f.write(''.join(err_dict[err_key]))
                f.close()
                files.append(stderr_file_name)
    
    # Clean up temp files, and update the list of existing files
    if keeptemps == 'none':
        for ext in [extension, 'pytxmcr', 'out', 'err']:
            fname = os.path.join(outputdir, basename + '.' + ext)
            if os.path.isfile(fname):
                os.remove(fname)
    elif keeptemps == 'code':
        for ext in ['pytxmcr', 'out', 'err']:
            fname = os.path.join(outputdir, basename + '.' + ext)
            if os.path.isfile(fname):
                os.remove(fname)
        files.append(os.path.join(outputdir, basename + '.' + extension))
    elif keeptemps == 'all':
        for ext in [extension, 'pytxmcr', 'out', 'err']:
            files.append(os.path.join(outputdir, basename + '.' + ext))

    # Take care of any unknowns, based on exit code
    # Interpret the exit code as an indicator of whether there were errors,
    # and treat unknowns accordingly.  This will cause all warnings to be 
    # misinterpreted as errors if warnings trigger a nonzero exit code.
    # It will also cause all warnings to be misinterpreted as errors if there
    # is a single error that causes a nonzero exit code.  That isn't ideal,
    # but shouldn't be a problem, because as soon as the error(s) are fixed,
    # the exit code will be zero, and then all unknowns will be interpreted
    # as warnings.
    if unknowns:
        if proc.returncode == 0:
            unknowns_type = 'warnings'
            warnings += unknowns
        else:
            unknowns_type = 'errors'
            errors += unknowns
        unknowns_message = '''
                * PythonTeX notice
                    {0} message(s) could not be classified
                    Based on the return code, they were interpreted as {1}'''
        messages[0] += textwrap.dedent(unknowns_message.format(unknowns, unknowns_type))
    
    # Take care of anything that has escaped detection thus far.
    if proc.returncode == 1 and not errors:
        errors += 1
        command_message = '''
                * PythonTeX error
                    An error occurred but no error messages were identified.
                    This may indicate a bad command or missing program.
                    The following command was executed:
                        "{0}"'''
        messages[0] += textwrap.dedent(command_message.format(' '.join(exec_cmd)))
    
    # Add any stderr messages; otherwise, clear the default message header
    if err_messages_ud:
        messages.extend(err_messages_ud)
    if err_messages_d:
        messages.extend(err_messages_d)
    if len(messages) == 1:
        messages = []
    
    # Return a dict of dicts of results
    return {'process': 'code',
            'key': key_run,
            'files': files,
            'macros': macros,
            'dependencies': dependencies,
            'errors': errors,
            'warnings': warnings,
            'messages': messages}




def do_pygments(encoding, outputdir, fvextfile, pygments_list, 
                pygments_settings, typeset_cache):
    '''
    Create Pygments content.
    
    To be run during multiprocessing.
    '''
    # Lazy import
    from pygments import highlight
    from pygments.lexers import get_lexer_by_name
    from pygments.formatters import LatexFormatter
    
    # Create what's needed for storing results
    pygments_files = defaultdict(list)
    pygments_macros = defaultdict(list)
    errors = 0
    warnings = 0
    messages = []
    messages.append('\n----  Messages for Pygments  ----')
    
    # Create dicts of formatters and lexers.
    formatter = dict()
    lexer = dict()
    for codetype in pygments_settings:
        if codetype != ':GLOBAL':
            formatter[codetype] = LatexFormatter(**pygments_settings[codetype]['formatter_options'])
            lexer[codetype] = get_lexer_by_name(pygments_settings[codetype]['lexer'], 
                                                **pygments_settings[codetype]['lexer_options'])
    
    # Actually parse and highlight the code.
    for c in pygments_list:
        if c.is_cons:
            content = typeset_cache[c.key_run][c.input_instance]
        elif c.is_extfile:
            if os.path.isfile(c.extfile):
                f = open(c.extfile, encoding=encoding)
                content = f.read()
                f.close()
            else:
                content = None
                messages.append('* PythonTeX error')
                messages.append('    Could not find external file ' + c.extfile)
                messages.append('    The file was not pygmentized')
        else:
            content = c.code
        processed = highlight(content, lexer[c.input_family], formatter[c.input_family])
        if c.is_inline or content.count('\n') < fvextfile:
            # Highlighted code brought in via macros needs SaveVerbatim
            processed = sub(r'\\begin{Verbatim}\[(.+)\]', 
                            r'\\begin{{SaveVerbatim}}[\1]{{pytx@{0}@{1}@{2}@{3}}}'.format(c.input_family, c.input_session, c.input_restart, c.input_instance), processed, count=1)
            processed = processed.rsplit('\\', 1)[0] + '\\end{SaveVerbatim}\n\n'                    
            pygments_macros[c.key_typeset].append(processed)
        else:
            fname = os.path.join(outputdir, c.key_typeset.replace('#', '_') + '.pygtex')
            f = open(fname, 'w', encoding=encoding)
            f.write(processed)
            f.close()
            pygments_files[c.key_typeset].append(fname)
    
    if len(messages) == 1:
        messages = []
    # Return a dict of dicts of results
    return {'process': 'pygments',
            'pygments_files': pygments_files,
            'pygments_macros': pygments_macros,
            'errors': errors,
            'warnings': warnings,
            'messages': messages} 




def python_console(jobname, encoding, outputdir, workingdir, fvextfile,
                   pygments_settings, cc_begin_list, cons_list, cc_end_list,
                   startup, banner, filename):
    '''
    Use Python's ``code`` module to typeset emulated Python interactive 
    sessions, optionally highlighting with Pygments.
    '''
    # Create what's needed for storing results
    key_run = cons_list[0].key_run
    files = []
    macros = []
    pygments_files = defaultdict(list)
    pygments_macros = defaultdict(list)
    typeset_cache = {}
    dependencies = {}
    errors = 0
    warnings = 0
    messages = []
    messages.append('\n----  Messages for ' + key_run.replace('#', ':') + '  ----')
    
    # Lazy import what's needed
    import code
    from collections import deque
    if sys.version_info[0] == 2:
        # Need a Python 2 interface to io.StringIO that can accept bytes
        import io
        class StringIO(io.StringIO):
            _orig_write = io.StringIO.write
            def write(self, s):
                self._orig_write(unicode(s))
    else:
        from io import StringIO
    
    # Create a custom console class
    class Console(code.InteractiveConsole):
        '''
        A subclass of code.InteractiveConsole that takes a list and treats it
        as a series of console input.
        '''
        
        def __init__(self, banner, filename):
            if banner == 'none':
                self.banner = 'NULL BANNER'
            elif banner == 'standard':
                cprt = 'Type "help", "copyright", "credits" or "license" for more information.'
                self.banner = 'Python {0} on {1}\n{2}'.format(sys.version, sys.platform, cprt)
            elif banner == 'pyversion':
                self.banner = 'Python ' + '.'.join(str(sys.version_info[n]) for n in (0, 1, 2))
            else:
                self.banner = None
            if filename == 'console':
                self.filename = '<console>'
            elif filename == 'stdin':
                self.filename = '<stdin>'
            else:
                self.filename = None
            code.InteractiveConsole.__init__(self, filename=self.filename)
            self.iostdout = StringIO()
    
        def consolize(self, startup, cons_list):
            self.console_code = deque()
            # Delimiters are passed straight through and need newlines
            self.console_code.append('=>PYTHONTEX#STARTUP##\n')
            cons_config = '''
                    import os
                    import sys
                    docdir = os.getcwd()
                    if os.path.isdir('{workingdir}'):
                        os.chdir('{workingdir}')
                        if os.getcwd() not in sys.path:
                            sys.path.append(os.getcwd())
                    else:
                        sys.exit('Cannot find directory {workingdir}')
                    
                    if docdir not in sys.path:
                        sys.path.append(docdir)
                    
                    del docdir
                    '''
            cons_config = cons_config.format(workingdir=workingdir)[1:]
            self.console_code.extend(textwrap.dedent(cons_config).splitlines())
            # Code is processed and doesn't need newlines
            self.console_code.extend(startup.splitlines())
            for c in cons_list:
                self.console_code.append('=>PYTHONTEX#{0}#{1}#\n'.format(c.input_instance, c.input_command))
                self.console_code.extend(c.code.splitlines())
            old_stdout = sys.stdout
            sys.stdout = self.iostdout
            self.interact(self.banner)
            sys.stdout = old_stdout
            self.session_log = self.iostdout.getvalue()
    
        def raw_input(self, prompt):
            # Have to do a lot of looping and trying to make sure we get 
            # something valid to execute
            try:
                line = self.console_code.popleft()
            except IndexError:
                raise EOFError
            while line.startswith('=>PYTHONTEX#'):
                # Get new lines until we get one that doesn't begin with a 
                # delimiter.  Then write the last delimited line.
                old_line = line
                try:
                    line = self.console_code.popleft()
                    self.write(old_line)
                except IndexError:
                    raise EOFError
            if line or prompt == sys.ps2:
                self.write('{0}{1}\n'.format(prompt, line))
            else:
                self.write('\n')
            return line
        
        def write(self, data):
            self.iostdout.write(data)
    
    # Need to combine all custom code and user code to pass to consolize
    cons_list = cc_begin_list + cons_list + cc_end_list
    # Create a dict for looking up exceptions.  This is needed for startup 
    # commands and for code commands and environments, since their output
    # isn't typeset
    cons_index = {}
    for c in cons_list:
        cons_index[c.input_instance] = c.input_line    
    
    # Consolize the code
    con = Console(banner, filename)
    con.consolize(startup, cons_list)
    
    # Set up Pygments, if applicable
    if pygments_settings is not None:
        pygmentize = True
        # Lazy import
        from pygments import highlight
        from pygments.lexers import get_lexer_by_name
        from pygments.formatters import LatexFormatter
        formatter = LatexFormatter(**pygments_settings['formatter_options'])
        lexer = get_lexer_by_name(pygments_settings['lexer'], 
                                  **pygments_settings['lexer_options'])
    else:
        pygmentize = False
    
    # Process the console output
    output = con.session_log.split('=>PYTHONTEX#')
    # Extract banner
    if banner == 'none':
        banner_text = ''
    else:
        banner_text = output[0]
    # Ignore the beginning, because it's the banner
    for block in output[1:]:
        delims, console_content = block.split('#\n', 1)
        if console_content:
            input_instance, input_command = delims.split('#')
            if input_instance == 'STARTUP':
                exception = False
                console_content_lines = console_content.splitlines()
                for line in console_content_lines:
                    if (not line.startswith(sys.ps1) and 
                            not line.startswith(sys.ps2) and 
                            line and not line.isspace()):
                        exception = True
                        break
                if exception:
                    if 'Error:' in console_content:
                        errors += 1
                        alert_type = 'error'
                    elif 'Warning:' in console_content:
                        warnings += 1
                        alert_type = 'warning'
                    else:
                        errors += 1
                        alert_type = 'error (?)'
                    messages.append('* PythonTeX stderr - {0} in console startup code:'.format(alert_type))
                    for line in console_content_lines:
                        messages.append('  ' + line)
            elif input_command in ('c', 'code'):
                exception = False
                console_content_lines = console_content.splitlines()
                for line in console_content_lines:
                    if (line and not line.startswith(sys.ps1) and 
                            not line.startswith(sys.ps2) and 
                            not line.isspace()):
                        print('X' + line + 'X')
                        exception = True
                        break
                if exception:
                    if 'Error:' in console_content:
                        errors += 1
                        alert_type = 'error'
                    elif 'Warning:' in console_content:
                        warnings += 1
                        alert_type = 'warning'
                    else:
                        errors += 1
                        alert_type = 'error (?)'
                    if input_instance.endswith('CC'):
                        messages.append('* PythonTeX stderr - {0} near line {1} in custom code for console:'.format(alert_type, cons_index[input_instance]))
                    else:
                        messages.append('* PythonTeX stderr - {0} near line {1} in console code:'.format(alert_type, cons_index[input_instance]))
                    messages.append('    Console code is not typeset, and should have no output')
                    for line in console_content_lines:
                        messages.append('  ' + line)
            else:
                if input_command == 'i':
                    # Currently, there isn't any error checking for invalid
                    # content; it is assumed that a single line of commands 
                    # was entered, producing one or more lines of output.
                    # Given that the current ``\pycon`` command doesn't
                    # allow line breaks to be written to the .pytxcode, that
                    # should be a reasonable assumption.
                    console_content = console_content.split('\n', 1)[1]
                if banner_text is not None and input_command == 'console':
                    # Append banner to first appropriate environment
                    console_content = banner_text + console_content
                    banner_text = None
                # Cache
                key_typeset = key_run + '#' + input_instance
                typeset_cache[input_instance] = console_content
                # Process for LaTeX
                if pygmentize:
                    processed = highlight(console_content, lexer, formatter)
                    if console_content.count('\n') < fvextfile:                            
                        processed = sub(r'\\begin{Verbatim}\[(.+)\]', 
                                        r'\\begin{{SaveVerbatim}}[\1]{{pytx@{0}}}'.format(key_typeset.replace('#', '@')),
                                        processed, count=1)
                        processed = processed.rsplit('\\', 1)[0] + '\\end{SaveVerbatim}\n\n'
                        pygments_macros[key_typeset].append(processed)
                    else:
                        fname = os.path.join(outputdir, key_typeset.replace('#', '_') + '.pygtex')
                        f = open(fname, 'w', encoding=encoding)
                        f.write(processed)
                        f.close()
                        pygments_files[key_typeset].append(fname)  
                else:
                    if console_content.count('\n') < fvextfile:
                        processed = ('\\begin{{SaveVerbatim}}{{pytx@{0}}}\n'.format(key_typeset.replace('#', '@')) + 
                                     console_content + '\\end{SaveVerbatim}\n\n')
                        macros.append(processed)
                    else:
                        processed = ('\\begin{Verbatim}\n' + console_content +
                                     '\\end{Verbatim}\n\n')
                        fname = os.path.join(outputdir, key_typeset.replace('#', '_') + '.tex')
                        f = open(fname, 'w', encoding=encoding)
                        f.write(processed)
                        f.close()
                        files.append(fname)
    
    if len(messages) == 1:
        messages = []
    
    # Return a dict of dicts of results
    return {'process': 'console',
            'key': key_run,
            'files': files,
            'macros': macros,
            'pygments_files': pygments_files,
            'pygments_macros': pygments_macros,
            'typeset_cache': typeset_cache,
            'dependencies': dependencies,
            'errors': errors,
            'warnings': warnings,
            'messages': messages} 




def main():
    # Create dictionaries for storing data.
    #
    # All data that must be saved for subsequent runs is stored in "data".
    # (We start off by saving the script version, a global var, in this dict.)
    # All data that is only created for this run is stored in "temp_data".
    # (We start off by creating keys for keeping track of errors and warnings.)
    # All old data will eventually be loaded into "old_data".
    # Since dicts are mutable data types, these dicts can be modified
    # from within functions, as long as the dicts are passed to the functions.
    # For simplicity, variables will often be created within functions to
    # refer to dictionary values.
    data = {'version': version, 'start_time': time.time()}
    temp_data = {'errors': 0, 'warnings': 0}
    old_data = dict()    
    
    
    # Process command-line options.
    #
    # This gets the raw_jobname (actual job name), jobname (a sanitized job 
    # name, used for creating files named after the jobname), and any options.
    process_argv(data, temp_data)
    # If there aren't errors in argv, and the program is going to run 
    # (rather than just exit due to --version or --help command-line options), 
    # print PythonTeX version.  Flush to make the message go out immediately,  
    # so that the user knows PythonTeX has started.
    print('This is PythonTeX ' + version)
    sys.stdout.flush()
    # Once we have the encoding (from argv), we set stdout and stderr to use 
    # this encoding.  Later, we will parse the saved stderr of scripts 
    # executed via multiprocessing subprocesses, and print the parsed results 
    # to stdout.  The saved stderr uses the same encoding that was used 
    # for the files that created it (this is important for code containing 
    # unicode characters), so we also need stdout for the main PythonTeX
    # script to support this encoding.  Setting stderr encoding is primarily 
    # a matter of symmetry.  Ideally, pythontex*.py will be bug-free,
    # and stderr won't be needed!
    if sys.version_info[0] == 2:
        sys.stdout = codecs.getwriter(data['encoding'])(sys.stdout, 'strict')
        sys.stderr = codecs.getwriter(data['encoding'])(sys.stderr, 'strict')
    else:
        sys.stdout = codecs.getwriter(data['encoding'])(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter(data['encoding'])(sys.stderr.buffer, 'strict')


    # Load the code and process the settings it passes from the TeX side.
    #
    # This gets a list containing the code (the part of the code file 
    # containing the settings is removed) and the processed settings.
    load_code_get_settings(data, temp_data)
    # Now that the settings are loaded, check if outputdir exits.
    # If not, create it.
    if not os.path.isdir(data['settings']['outputdir']):
        os.mkdir(data['settings']['outputdir'])


    # Load/create old_data
    get_old_data(data, old_data, temp_data)
    
    
    # Hash the code.  Determine what needs to be executed.  Determine whether
    # Pygments should be used.  Update pygments_settings to account for 
    # Pygments commands and environments (as opposed to PythonTeX commands 
    # and environments).
    hash_all(data, temp_data, old_data, engine_dict)
    
    
    # Parse the code and write scripts for execution.
    parse_code_write_scripts(data, temp_data, engine_dict)
    
    
    # Execute the code and perform Pygments highlighting via multiprocessing.
    do_multiprocessing(data, temp_data, old_data, engine_dict)

        
    # Print exit message
    print('\n--------------------------------------------------')
    # If some rerun settings are used, there may be unresolved errors or 
    # warnings; if so, print a summary of those along with the current 
    # error and warning summary
    unresolved_errors = 0
    unresolved_warnings = 0
    if temp_data['rerun'] in ('errors', 'modified', 'never'):
        global_update = {}
        global_update.update(temp_data['code_update'])
        global_update.update(temp_data['cons_update'])
        for key in data['exit_status']:
            if not global_update[key]:
                unresolved_errors += data['exit_status'][key][0]
                unresolved_warnings += data['exit_status'][key][1]
    if unresolved_warnings != 0 or unresolved_errors != 0:
        print('PythonTeX:  {0}'.format(data['raw_jobname']))
        print('    - Old:      {0} error(s), {1} warnings(s)'.format(unresolved_errors, unresolved_warnings))
        print('    - Current:  {0} error(s), {1} warnings(s)'.format(temp_data['errors'], temp_data['warnings']))        
    else:
        print('PythonTeX:  {0} - {1} error(s), {2} warning(s)\n'.format(data['raw_jobname'], temp_data['errors'], temp_data['warnings']))

    # Exit with appropriate exit code based on user settings.
    if temp_data['error_exit_code'] and temp_data['errors'] > 0:
        sys.exit(1)
    else:
        sys.exit()



# The "if" statement is needed for multiprocessing under Windows; see the 
# multiprocessing documentation.  It is also needed in this case when the 
# script is invoked via the wrapper.
if __name__ == '__main__':
    main()
