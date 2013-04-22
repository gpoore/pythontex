#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
This is the main PythonTeX script.

Two versions of this script and the other PythonTeX scripts are provided.  
One set of scripts, with names ending in "2", runs under Python 2.7.  The 
other set of scripts, with names ending in "3", runs under Python 3.1 or 
later.

This script needs to be able to import pythontex_types*.py; in general it 
should be in the same directory.  This script creates scripts that need to 
be able to import pythontex_utils*.py.  The location of that file is 
determined via the kpsewhich command, which is part of the Kpathsea library 
included with some TeX distributions, including TeX Live and MiKTeX.


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
#from __future__ import absolute_import
#from __future__ import division
#from __future__ import print_function
#from __future__ import unicode_literals
#\\ End Python 2
import sys
import os
import copy
import argparse
import codecs
from hashlib import sha1
from collections import defaultdict
from re import match, sub, search
import subprocess
import multiprocessing
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import LatexFormatter
#// Python 2
#from pythontex_types2 import *
#try:
#    import cPickle as pickle
#except:
#    import pickle
#from io import open
#\\ End Python 2
#// Python 3
from pythontex_types3 import *
import pickle
#\\ End Python 3


# Script parameters
# Version
version = 'v0.11'




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
    parser.add_argument('--encoding', default='utf-8', 
                        help='encoding for all text files (see codecs module for encodings)')
    parser.add_argument('--error-exit-code', default='true', 
                        choices=('true', 'false'),                          
                        help='return exit code of 1 if there are errors (not desirable with some TeX editors and workflows)')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--runall', nargs='?', default='false',
                       const='true', choices=('true', 'false'),
                       help='run all code, regardless of whether it has been modified; equivalent to package option')
    group.add_argument('--rerun', default='errors', 
                       choices=('modified', 'errors', 'warnings', 'always'),
                       help='set conditions for rerunning code; equivalent to package option')
    parser.add_argument('--hashdependencies', nargs='?', default='false', 
                        const='true', choices=('true', 'false'),                          
                        help='hash dependencies (such as external data) to check for modification, rather than using mtime; equivalent to package option')
    parser.add_argument('-v', '--verbose', default=False, action='store_true',
                       help='verbose output')
    args = parser.parse_args()
    
    # Store the parsed argv in data and temp_data          
    data['encoding'] = args.encoding
    if args.error_exit_code == 'true':
        temp_data['error_exit_code'] = True
    else:
        temp_data['error_exit_code'] = False
    # runall is a subset of rerun, so both are stored under rerun
    if args.runall == 'true':
        temp_data['rerun'] = 'always'
    else:
        temp_data['rerun'] = args.rerun
    if args.hashdependencies == 'true':
        temp_data['hashdependencies'] = True
    else:
        temp_data['hashdependencies'] = False
    temp_data['verbose'] = args.verbose
    
    if args.TEXNAME is not None:
        # Determine if we a dealing with a raw basename or filename, or a
        # path to it.  If there's a path, we need to make the document 
        # directory the current working directory.
        dir, raw_jobname = os.path.split(args.TEXNAME)
        dir = os.path.expanduser(os.path.normcase(dir))
        if len(dir) > 0:
            os.chdir(dir)
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
        # assumption that there should only be a single file <jobname> in the 
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
    Load the code file, process the settings its contains, and remove the 
    settings lines so that the remainder is ready for code processing.
    '''
    
    # Bring in the .pytxcode file as a list
    raw_jobname = data['raw_jobname']
    encoding = data['encoding']
    if os.path.isfile(raw_jobname + '.pytxcode'):
        f = open(raw_jobname + '.pytxcode', 'r', encoding=encoding)
        pytxcode = f.readlines()
        f.close()
    else:
        print('* PythonTeX error')
        print('    Code file ' + raw_jobname + '.pytxcode does not exist.')
        print('    Run LaTeX to create it.')
        return sys.exit(1)
    
    # Determine the number of settings lines in the code file.
    # Create a list of settings, and save the code for later processing.
    n = len(pytxcode) - 1
    while n >= 0 and pytxcode[n].startswith('=>PYTHONTEX:SETTINGS#'):
        n -= 1
    pytxsettings = pytxcode[n+1:]
    temp_data['pytxcode'] = pytxcode[:n+1]

    # Prepare to process settings
    #
    # Create a dict for storing settings.
    settings = dict()
    # Create a dict for storing Pygments settings.
    # Each dict entry will itself be a dict.
    pygments_settings = defaultdict(dict)
    
    # Create a dict of processing functions, and generic processing functions
    settingsfunc = dict()
    def set_kv_data(k, v):
        if v == 'true':
            settings[k] = True
        elif v == 'false':
            settings[k] = False
        else:
            settings[k] = v
    # Need a function for when assignment is only needed if not default value
    def set_kv_temp_data_if_not_default():
        def f(k, v):
            if v != 'default':
                if v == 'true':
                    temp_data[k] = True
                elif v == 'false':
                    temp_data[k] = False
                else:
                    temp_data[k] = v
        return f
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
    def set_kv_pygments_global(k, v):
        # Global pygments optins use a key that can't conflict with anything 
        # (inputtype can't ever contain a hash symbol).  This key is deleted 
        # later, as soon as it is no longer needed.  Note that no global 
        # lexer can be specified via pygopt; pyglexer is needed for that.
        if k == 'pyglexer':
            if v != '':
                pygments_settings['#GLOBAL']['lexer'] = v
        elif k == 'pygopt':
            options = v.strip('{}').replace(' ', '').split(',')
            # Set default values, modify based on settings
            style = None
            texcomments = None
            mathescape = None
            for option in options:
                if option.startswith('style='):
                    style = option.split('=', 1)[1]
                elif option == 'texcomments':
                    texcomments = True
                elif option.startswith('texcomments='):
                    option = option.split('=', 1)[1]
                    if option in ('true', 'True'):
                        texcomments = True
                elif option == 'mathescape':
                    mathescape = True
                elif option.startswith('mathescape='):
                    option = option.split('=', 1)[1]
                    if option in ('true', 'True'):
                        mathescape = True
                elif option != '':
                    print('* PythonTeX warning')
                    print('    Unknown global Pygments option:  ' + option)
                    temp_data['warnings'] += 1
            if style is not None:
                pygments_settings['#GLOBAL']['style'] = style
                pygments_settings['#GLOBAL']['commandprefix'] = 'PYG' + style
            if texcomments is not None:
                pygments_settings['#GLOBAL']['texcomments'] = texcomments
            if mathescape is not None:
                pygments_settings['#GLOBAL']['mathescape'] = mathescape
    def set_kv_pygments_family(k, v):
        inputtype, lexer, options = v.replace(' ','').split(',', 2)
        options = options.strip('{}').split(',')
        # Set default values, modify based on settings
        style = 'default'
        texcomments = False
        mathescape = False
        for option in options:
            if option.startswith('style='):
                style = option.split('=', 1)[1]
            elif option == 'texcomments':
                texcomments = True
            elif option.startswith('texcomments='):
                option = option.split('=', 1)[1]
                if option in ('true', 'True'):
                    texcomments = True
            elif option == 'mathescape':
                mathescape = True
            elif option.startswith('mathescape='):
                option = option.split('=', 1)[1]
                if option in ('true', 'True'):
                    mathescape = True
            elif option != '':
                print('* PythonTeX warning')
                print('    Unknown Pygments option for ' + inputtype + ':  ' + '"' + option + '"')
        pygments_settings[inputtype] = {'lexer': lexer,
                                        'style': style,
                                        'texcomments': texcomments,
                                        'mathescape': mathescape,
                                        'commandprefix': 'PYG' + style} 
    settingsfunc['version'] = set_kv_data
    settingsfunc['outputdir'] = set_kv_data
    settingsfunc['workingdir'] = set_kv_data
    settingsfunc['rerun'] = set_kv_temp_data_if_not_default()
    settingsfunc['hashdependencies'] = set_kv_temp_data_if_not_default()
    settingsfunc['stderr'] = set_kv_data
    settingsfunc['stderrfilename'] = set_kv_data
    settingsfunc['keeptemps'] = set_kv_data
    settingsfunc['pyfuture'] = set_kv_data
    settingsfunc['pygments'] = set_kv_data
    settingsfunc['fvextfile'] = set_kv_data_fvextfile
    settingsfunc['pyglexer'] = set_kv_pygments_global
    settingsfunc['pygopt'] = set_kv_pygments_global
    settingsfunc['pygfamily'] = set_kv_pygments_family
    settingsfunc['pyconbanner'] = set_kv_data
    settingsfunc['pyconfilename'] = set_kv_data
    settingsfunc['depythontex'] = set_kv_data
    
    # Process settings
    for line in pytxsettings:
        # A hash symbol "#" should never be within content, but be 
        # careful just in case by using rsplit('#', 1)[0]
        content = line.replace('=>PYTHONTEX:SETTINGS#', '', 1).rsplit('#', 1)[0]
        key, val = content.split('=', 1)
        try:
            settingsfunc[key](key, val)
        except KeyError:
            print('* PythonTeX warning')
            print('    Unknown option "' + content + '"')
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
    # #### Is there a more logical place for this?
    #// Python 2
    ## We save the pyfuture option regardless of the Python version,
    ## but we only use it under Python 2.
    #update_default_code2(data['settings']['pyfuture'])
    #\\ End Python 2




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
    outputdir = data['settings']['outputdir']
    pythontex_data_file = os.path.join(outputdir, 'pythontex_data.pkl')
    # Create a string containing the name of the pythontex_utils.py file
    pythontex_utils_file = 'pythontex_utils.py'
    
    # Load the old data if it exists (read as binary pickle)
    if os.path.isfile(pythontex_data_file):
        f = open(pythontex_data_file, 'rb')
        old_data.update(pickle.load(f))
        f.close()
        temp_data['loaded_old_data'] = True
    else:
        temp_data['loaded_old_data'] = False
    # Set the scriptpath in the current data
    if temp_data['loaded_old_data'] and os.path.isfile(os.path.join(old_data['scriptpath'], pythontex_utils_file)):
        data['scriptpath'] = old_data['scriptpath']
    else:
        exec_cmd = ['kpsewhich', '--format', 'texmfscripts', pythontex_utils_file]
        try:
            # Get path, convert from bytes to unicode, and strip off eol 
            # characters
            # #### Is there a better approach for decoding, in case of non utf-8?
            scriptpath_full = subprocess.check_output(exec_cmd).decode('utf-8').rstrip('\r\n')
        except OSError:
            print('* PythonTeX error')
            print('    Your system appears to lack kpsewhich.')
            return sys.exit(1)
        except subprocess.CalledProcessError:
            print('* PythonTeX error')
            print('    kpsewhich is not happy with its arguments.')
            print('    This command was attempted:')
            print('      ' + ' '.join(exec_cmd))
            return sys.exit(1)
        # Split off the end of the path ("/pythontex_utils*.py")
        scriptpath = os.path.split(scriptpath_full)[0]
        data['scriptpath'] = scriptpath
    
    # Set path for scripts, via the function from pythontex_types*.py
    # #### More logical location?
    set_utils_location(data['scriptpath'])




def hash_code(data, temp_data, old_data, typedict):
    '''
    Hash the code to see what has changed and needs to be updated.
    
    Save the hashes in hashdict.  Create update_code, a list of bools 
    regarding whether code should be executed.  Create update_pygments, a 
    list of bools determining what needs updated Pygments highlighting.  
    Update pygments_settings to account for Pygments (as opposed to PythonTeX) 
    commands and environments.
    '''
    # Technically, the code could be simultaneously hashed and divided into 
    # lists according to (type, session, group).  That approach would involve
    # some unnecessary list creation and text parsing, but would also have 
    # the advantage of only handling everything once.  The current approach 
    # is based on simplicity.  No speed tests have been performed, but any 
    # difference between the two approaches should generally be negligible.
    #
    # Note that the PythonTeX information that accompanies code must be 
    # hashed in addition to the code itself; the code could stay the same, 
    # but its context could change, which might require that context-dependent
    # code be executed.  All of the PythonTeX information is hashed except 
    # for the input line number.  Context-dependent code is going too far if 
    # it depends on that.
    
    # Create variables to more easily access parts of data
    pytxcode = temp_data['pytxcode']
    encoding = data['encoding']
    loaded_old_data = temp_data['loaded_old_data']
    rerun = temp_data['rerun']
    hashdependencies = temp_data['hashdependencies']
    # Calculate hashes for each set of code (type, session, group).
    # We don't have to skip the lines of settings in the code file, because
    # they have already been removed.
    hasher = defaultdict(sha1)
    for codeline in pytxcode:
        # Detect the start of a new command/environment
        # Switch variables if so
        if codeline.startswith('=>PYTHONTEX#'):
            inputtype, inputsession, inputgroup = codeline.split('#', 4)[1:4]
            currentkey = inputtype + '#' + inputsession + '#' + inputgroup
            # If dealing with an external file
            if inputsession.startswith('EXT:'):
                # We use os.path.normcase to make sure slashes are 
                # appropriate, thus allowing code in subdirectories to be 
                # specified
                extfile = os.path.normcase(inputsession.replace('EXT:', '', 1))
                if not os.path.isfile(extfile):
                    print('* PythonTeX error')
                    print('    Cannot find external file ' + extfile)
                    return sys.exit(1)
                # Hash either file contents or mtime
                if hashdependencies:
                    # Read and hash the file in binary.  Opening in text mode 
                    # would require an unnecessary decoding and encoding cycle.
                    f = open(extfile, 'rb')
                    hasher[currentkey].update(f.read())
                    f.close()
                else:
                    hasher[currentkey].update(str(os.path.getmtime(extfile)).encode(encoding))
            # If not dealing with an external file, hash part of code info
            else:
                # We need to hash most of the code info, because code needs 
                # to be executed again if anything but the line number changes.
                # The text must be encoded to bytes for hashing.
                hasher[currentkey].update(codeline.rsplit('#', 2)[0].encode(encoding))
        else:
            # The text must be encoded to bytes for hashing
            hasher[currentkey].update(codeline.encode(encoding))
    # Create a dictionary of hashes, in string form    
    # For PythonTeX (as opposed to Pygments) content, the hashes should 
    # include the default code, just in case it is ever changed for any reason.
    # Based on the order in which the code will be executed, default code 
    # should technically be hashed first.  But we don't know ahead of time 
    # what entries will be in the hashdict, so we hash it afterward.  The 
    # result is the same, since we get a unique hash.  We must also account 
    # for custom code.  This is more awkward, since we don't yet have it in
    # a centralized location where we can just add it to the hash.  But we do
    # have a hash of the custom code, so we just store that with the main hash.
    hashdict = dict()
    for key in hasher:
        inputtype = key.split('#', 1)[0]
        if inputtype.startswith('PYG') or inputtype.startswith('CC:'):
            hashdict[key] = hasher[key].hexdigest()
        else:
            hasher[key].update(''.join(typedict[inputtype].default_code).encode(encoding))
    for key in hasher:
        if not key.startswith('PYG') and not key.startswith('CC:'):
            inputtype = key.split('#', 1)[0]
            cc_begin_key = 'CC:' + inputtype + ':begin#none#none'
            if cc_begin_key in hashdict:
                cc_begin_hash = hashdict[cc_begin_key]
            else:
                cc_begin_hash = ''
            cc_end_key = 'CC:' + inputtype + ':end#none#none'
            if cc_end_key in hashdict:
                cc_end_hash = hashdict[cc_end_key]
            else:
                cc_end_hash = '' 
            hashdict[key] = ':'.join([hasher[key].hexdigest(), cc_begin_hash, cc_end_hash])
    # Delete the hasher so it can't be accidentally used instead of hashdict
    del hasher
    # Save the hashdict into data.
    data['hashdict'] = hashdict    
    
    # See what needs to be updated.
    # In the process, copy over macros and files that may be reused.
    update_code = dict()
    macros = defaultdict(list)
    files = defaultdict(list)
    dependencies = defaultdict(list)
    exit_status = dict()
    # We need a function for checking if dependencies have changed.
    # We could just always create an updated dict of dependency hashes/mtimes,
    # but that's a waste if the code itself has been changed, particularly if
    # we are hashing code rather than just using mtimes.
    def unchanged_dependencies(key, data, temp_data, old_data):
        if key in old_data['dependencies']:
            old_dependencies_hashdict = old_data['dependencies'][key]
            dependencies_hasher = defaultdict(sha1)
            workingdir = data['settings']['workingdir']
            missing = False
            for dep in old_dependencies_hashdict:
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
                    print('    It belongs to ' + ':'.join(key.split('#')))
                    print('    Relative paths to dependencies must be specified from the working directory.')
                    temp_data['errors'] += 1
                    missing = True
                elif hashdependencies:
                    # Read and hash the file in binary.  Opening in text mode 
                    # would require an unnecessary decoding and encoding cycle.
                    f = open(dep_file, 'rb')
                    dependencies_hasher[dep].update(f.read())
                    f.close()
                else:
                    dependencies_hasher[dep].update(str(os.path.getmtime(dep_file)).encode(encoding))
            dependencies_hashdict = dict()
            for dep in dependencies_hasher:
                dependencies_hashdict[dep] = dependencies_hasher[dep].hexdigest()
            if missing:
                # Return True so that code doesn't run again; there's no
                # point in running it, because we would just get the same
                # error back in a different form.
                return True
            else:
                return dependencies_hashdict == old_dependencies_hashdict
        else:
            return True
    # We need a function for determining if exit status requires rerun
    # The 'all' and 'modified' cases are technically resolved without actually
    # using the function.  We also rerun all sessions that produced errors or
    # warnings the last time if the stderrfilename has changed.
    # #### There is probably a better way to handlestderrfilename, perhaps by 
    # modifying rerun based on it.
    def make_do_not_rerun():
        if (loaded_old_data and 
                data['settings']['stderrfilename'] != old_data['settings']['stderrfilename']):
            def func(status):
                if status[0] != 0 or status[1] != 0:
                    return False
                else:
                    return True     
        elif rerun == 'modified':
            def func(status):
                return True
        elif rerun == 'errors':
            def func(status):
                if status[0] != 0:
                    return False
                else:
                    return True
        elif rerun == 'warnings':
            def func(status):
                if status[0] != 0 or status[1] != 0:
                    return False
                else:
                    return True
        elif rerun == 'always':
            def func(status):
                return False
        return func
    do_not_rerun = make_do_not_rerun()
    
    # If old data was loaded, and it contained sufficient information, and 
    # settings are compatible, determine what has changed so that only 
    # modified code may be executed.  Otherwise, execute everything.
    # We don't have to worry about checking for changes in pyfuture, because
    # custom code and default code are hashed.  The treatment of keeptemps
    # could be made more efficient (if changed to 'none', just delete old temp
    # files rather than running everything again), but given that it is 
    # intended as a debugging aid, that probable isn't worth it.
    # We don't have to worry about hashdependencies changing, because if it 
    # does the hashes won't match (file contents vs. mtime) and thus code will
    # be re-executed.
    if (rerun != 'all' and loaded_old_data and
            'version' in old_data and
            data['version'] == old_data['version'] and
            data['encoding'] == old_data['encoding'] and
            data['settings']['workingdir'] == old_data['settings']['workingdir'] and
            data['settings']['keeptemps'] == old_data['settings']['keeptemps']):
        old_hashdict = old_data['hashdict']
        old_macros = old_data['macros']
        old_files = old_data['files']
        old_dependencies = old_data['dependencies']
        old_exit_status = old_data['exit_status']        
        # Compare the hash values, and set which code needs to be run
        for key in hashdict:
            if key.startswith('CC:'):
                pass
            elif ((key.startswith('PYG') or key.endswith('verb')) and 
                    key in old_hashdict and 
                    hashdict[key] == old_hashdict[key]):
                update_code[key] = False
            elif (key in old_hashdict and hashdict[key] == old_hashdict[key] and
                    do_not_rerun(old_exit_status[key]) and 
                    unchanged_dependencies(key, data, temp_data, old_data)):
                update_code[key] = False
                exit_status[key] = old_exit_status[key]
                if key in old_macros:
                    macros[key] = old_macros[key]
                if key in old_files:
                    files[key] = old_files[key]
                if key in old_dependencies:
                    dependencies[key] = old_dependencies[key]
            else:
                update_code[key] = True        
    else:        
        for key in hashdict:
            if not key.startswith('CC:'):
                update_code[key] = True
    # Save to data
    temp_data['update_code'] = update_code
    data['macros'] = macros
    data['files'] = files
    data['dependencies'] = dependencies
    data['exit_status'] = exit_status
    
    # Now that the code that needs updating has been determined, figure out
    # what Pygments content needs updating.  These are two separate tasks,
    # because the code may stay the same but may still need to be highlighted
    # if the Pygments settings have changed.
    #
    # Before determining what Pygments content needs updating, we must check 
    # for the use of the Pygments commands and environment (as opposed to 
    # PythonTeX ones), and assign proper Pygments settings if necessary.
    # Unlike regular PythonTeX commands and environments, the Pygments 
    # commands and environment don't automatically create their own Pygments 
    # settings in the code file.  This is because we can't know ahead of time 
    # which lexers will be needed; these commands and environments take a 
    # lexer name as an argument.  We can only do this now, since we need the 
    # set of unique (type, session, group).
    #
    # Any Pygments inputtype that appears will be pygments_macros; otherwise, it
    # wouldn't have ever been written to the code file.
    # #### Now that settings are at the end of .pytxcode, this could be 
    # shifted back to the TeX side. It probably should be made uniform, one 
    # way or another, for the case where pygopt is not used.
    pygments_settings = data['pygments_settings']
    for key in hashdict:
        inputtype = key.split('#', 1)[0]
        if inputtype.startswith('PYG') and inputtype not in pygments_settings:
            lexer = inputtype.replace('PYG', '', 1)
            style = 'default'
            texcomments = False
            mathescape = False
            pygments_settings[inputtype] = {'lexer': lexer,
                                            'style': style, 
                                            'texcomments': texcomments,
                                            'mathescape': mathescape,
                                            'commandprefix': 'PYG' + style}
    # Add settings for console, based on type, if these settings haven't 
    # already been created by passing explicit console settings from the TeX 
    # side.
    # #### 'cons' issues?
    for key in hashdict:
        if key.endswith('cons'):
            inputtype = key.split('#', 1)[0]
            inputtypecons = inputtype + '_cons'
            # Create console settings based on the type, if console settings 
            # don't exist.  We go ahead and define default console lexers for 
            # many languages, even though only Python is currently supported.
            # If a compatible console lexer can't be found, default to the 
            # text lexer (null lexer, does nothing).
            if inputtype in pygments_settings and inputtypecons not in pygments_settings:
                pygments_settings[inputtypecons] = copy.deepcopy(pygments_settings[inputtype])
                lexer = pygments_settings[inputtype]['lexer']
                if lexer in ('Python3Lexer', 'python3', 'py3'):
                    pygments_settings[inputtypecons]['lexer'] = 'pycon'
                    pygments_settings[inputtypecons]['python3'] = True
                elif lexer in ('PythonLexer', 'python', 'py'):
                    pygments_settings[inputtypecons]['lexer'] = 'pycon'
                    pygments_settings[inputtypecons]['python3'] = False
                elif lexer in ('RubyLexer', 'rb', 'ruby', 'duby'):
                    pygments_settings[inputtypecons]['lexer'] = 'rbcon'
                elif lexer in ('MatlabLexer', 'matlab'):
                    pygments_settings[inputtypecons]['lexer'] = 'matlabsession'
                elif lexer in ('SLexer', 'splus', 's', 'r'):
                    pygments_settings[inputtypecons]['lexer'] = 'rconsole'
                elif lexer in ('BashLexer', 'bash', 'sh', 'ksh'):
                    pygments_settings[inputtypecons]['lexer'] = 'console'
                else:
                    pygments_settings[inputtypecons]['lexer'] = 'text'
            # Since console content can't be typeset without the Python side
            # we need to detect whether Pygments was used previously but is
            # used no longer, so that we can generate a non-Pygments version.
            # We need to update code and Pygments to make sure all old content
            # is properly cleaned up.  Also, we need to see if console 
            # settings have changed.
            # #### All of this should possibly be done elsewhere; there may 
            # be a more logical location.
            if loaded_old_data:
                old_pygments_settings = old_data['pygments_settings']                
                if ((inputtypecons in old_pygments_settings and 
                        inputtypecons not in pygments_settings) or
                        data['settings']['pyconbanner'] != old_data['settings']['pyconbanner'] or
                        data['settings']['pyconfilename'] != old_data['settings']['pyconfilename']):
                    update_code[key] = True
    # The global Pygments settings are no longer needed, so we delete them.
    # #### Might be a better place to do this, if things earlier are rearranged
    # #### Also, this needs list due to Python 3 ... may be a better approach
    k = list(pygments_settings.keys())
    for s in k:
        if s != '#GLOBAL':
            pygments_settings[s].update(pygments_settings['#GLOBAL'])
    if '#GLOBAL' in pygments_settings:
        del pygments_settings['#GLOBAL']
    
    # Now we create a dictionary of whether pygments content needs updating.
    # The first set of conditions is identical to that for update_code,
    # except that workingdir and keeptemps don't have an effect on 
    # highlighting.  We also create the TeX style defitions for different 
    # Pygments styles.
    update_pygments = dict()
    pygments_macros = defaultdict(list)
    pygments_files = defaultdict(list)
    pygments_style_defs = dict()
    fvextfile = data['settings']['fvextfile']
    if (loaded_old_data and 'version' in old_data and
            data['version'] == old_data['version'] and
            data['encoding'] == old_data['encoding']):
        old_hashdict = old_data['hashdict']   
        old_pygments_settings = old_data['pygments_settings']
        old_pygments_macros = old_data['pygments_macros']
        old_pygments_files = old_data['pygments_files']
        old_fvextfile = old_data['settings']['fvextfile']
        old_pygments_style_defs = old_data['pygments_style_defs']
        for key in hashdict:
            if not key.startswith('CC:'):
                inputtype = key.split('#', 1)[0]
                if key.endswith('cons'):
                    inputtype += '_cons'
                # Pygments may not apply to content
                if inputtype not in pygments_settings:
                    update_pygments[key] = False
                # Pygments may apply, but have been done before for identical code
                # using identical settings
                elif (update_code[key] == False and 
                        inputtype in old_pygments_settings and 
                        pygments_settings[inputtype] == old_pygments_settings[inputtype] and 
                        fvextfile == old_fvextfile):
                    update_pygments[key] = False
                    if key in old_pygments_macros:
                        pygments_macros[key] = old_pygments_macros[key]
                    if key in old_pygments_files:
                        pygments_files[key] = old_pygments_files[key]
                else:
                    update_pygments[key] = True
        for codetype in pygments_settings:
            pygstyle = pygments_settings[codetype]['style']
            if pygstyle not in pygments_style_defs:
                if pygstyle in old_pygments_style_defs:
                    pygments_style_defs[pygstyle] = old_pygments_style_defs[pygstyle]
                else:
                    commandprefix = pygments_settings[codetype]['commandprefix']
                    formatter = LatexFormatter(style=pygstyle, commandprefix=commandprefix)
                    pygments_style_defs[pygstyle] = formatter.get_style_defs()
    else:    
        for key in hashdict:
            if not key.startswith('CC:'):
                inputtype = key.split('#', 1)[0]
                if key.endswith('cons'):
                    inputtype += '_cons'
                if inputtype in pygments_settings:
                    update_pygments[key] = True
                else:
                    update_pygments[key] = False
        for codetype in pygments_settings:
            pygstyle = pygments_settings[codetype]['style']
            if pygstyle not in pygments_style_defs:
                commandprefix = pygments_settings[codetype]['commandprefix']
                formatter = LatexFormatter(style=pygstyle, commandprefix=commandprefix)
                pygments_style_defs[pygstyle] = formatter.get_style_defs()       
    # Save to data
    temp_data['update_pygments'] = update_pygments
    data['pygments_macros'] = pygments_macros
    data['pygments_files'] = pygments_files
    data['pygments_style_defs'] = pygments_style_defs

    # Clean up old files, if possible
    # Check for 'files' and 'pygments_files' keys, for upgrade purposes
    # #### Might be able to clean this up a bit, especially if redo some Pygments
    if (loaded_old_data and
            'files' in old_data and 
            'pygments_files' in old_data):
        # Clean up for code that will be run again, and for code that no 
        # longer exists.  We use os.path.normcase() to fix slashes in the path
        # name, in an attempt to make saved paths platform-independent.
        old_hashdict = old_data['hashdict']
        old_files = old_data['files']
        old_pygments_files = old_data['pygments_files']
        for key in hashdict:
            if not key.startswith('CC:'):
                if update_code[key]:
                    if key in old_files:
                        for f in old_files[key]:
                            f = os.path.expanduser(os.path.normcase(f))
                            if os.path.isfile(f):
                                os.remove(f)
                    if key in old_pygments_files:
                        for f in old_pygments_files[key]:
                            f = os.path.expanduser(os.path.normcase(f))
                            if os.path.isfile(f):
                                os.remove(f)
                elif update_pygments[key] and key in old_pygments_files:
                    for f in old_pygments_files[key]:
                        f = os.path.expanduser(os.path.normcase(f))
                        if os.path.isfile(f):
                            os.remove(f)
        for key in old_hashdict:
            if key not in hashdict:
                for f in old_files[key]:
                    f = os.path.expanduser(os.path.normcase(f))
                    if os.path.isfile(f):
                        os.remove(f)
                for f in old_pygments_files[key]:
                    f = os.path.expanduser(os.path.normcase(f))
                    if os.path.isfile(f):
                        os.remove(f)
    elif loaded_old_data:
        print('* PythonTeX warning')
        print('    PythonTeX may not have been able to clean up old files.')
        print('    This should not cause problems.')
        print('    Delete the PythonTeX directory and run again to remove any unused files.')
        temp_data['warnings'] += 1




def parse_code_write_scripts(data, temp_data, typedict):
    '''
    Parse the code file into separate scripts, based on 
    (type, session, groups).  Write the script files.
    '''
    codedict = defaultdict(list)
    consoledict = defaultdict(list)
    # Create variables to ease data access
    hashdict = data['hashdict']
    outputdir = data['settings']['outputdir']
    workingdir = data['settings']['workingdir']
    encoding = data['encoding']
    pytxcode = temp_data['pytxcode']
    update_code = temp_data['update_code']
    update_pygments = temp_data['update_pygments']
    files = data['files']
    # We need to keep track of the last instance for each session, so 
    # that duplicates can be eliminated.  Some LaTeX environments process 
    # their contents multiple times and thus will create duplicates.  We 
    # need to initialize everything at -1, since instances begin at zero.
    def negonefactory():
        return -1
    lastinstance = defaultdict(negonefactory)
    for codeline in pytxcode:
        # Detect if start of new command/environment; if so, get new variables
        if codeline.startswith('=>PYTHONTEX#'):
            [inputtype, inputsession, inputgroup, inputinstance, inputcommand, inputcontext, inputline] = codeline.split('#')[1:8]
            currentkey = inputtype + '#' + inputsession + '#' + inputgroup
            currentinstance = int(inputinstance)
            # We need to determine whether code needs to be placed in the 
            # consoledict or the codedict.  In the process, we need to make 
            # sure that code that appears multiple times in the .pytxcode is
            # only actually copied once.
            addcode = False
            addconsole = False            
            if not inputgroup.endswith('verb') and lastinstance[currentkey] < currentinstance:
                lastinstance[currentkey] = currentinstance
                if (inputgroup.endswith('cons') and 
                        (update_code[currentkey] or update_pygments[currentkey])):
                    addconsole = True
                    consoledict[currentkey].append(codeline)
                elif currentkey.startswith('CC:') or update_code[currentkey]:    
                    switched = True
                    addcode = True
                    if inputcommand == 'inline':
                        inline = True
                    else:
                        inline = False
                        # Correct for line numbering in environments; content 
                        # doesn't really start till the line after the "\begin"
                        inputline = str(int(inputline)+1)
                if currentkey.startswith('CC:'):
                    inputinstance = 'customcode'
                    inputline += ' (in custom code)'
        # Only collect for a session (and later write it to a file) if it needs to be updated
        elif addconsole:
            consoledict[currentkey].append(codeline)
        elif addcode:
            # If just switched commands/environments, associate with the input 
            # line and check for indentation errors
            if switched:
                switched = False
                if inputtype.startswith('CC:'):
                    codedict[currentkey].append(typedict[inputtype.split(':')[1]].set_inputs_var(inputinstance, inputcommand, inputcontext, inputline))
                else:
                    codedict[currentkey].append(typedict[inputtype].set_inputs_var(inputinstance, inputcommand, inputcontext, inputline))
                # We need to make sure that each time we switch, we are 
                # starting out with no indentation.  Technically, we could 
                # allow indentation to continue between commands and 
                # environments, but that seems like a recipe for disaster.
                if codeline.startswith(' ') or codeline.startswith('\t'):
                    print('* PythonTeX error')
                    print('    Command/environment cannot begin with indentation (space or tab) near line ' + inputline)
                    sys.exit(1)
            if inline:
                codedict[currentkey].append(typedict[inputtype].inline(codeline))
            else:
                codedict[currentkey].append(codeline)
    # Save codedict and consoledict
    temp_data['codedict'] = codedict
    temp_data['consoledict'] = consoledict
    # Update custom code
    for codetype in typedict:
        cc_begin_key = 'CC:' + codetype + ':begin#none#none'
        if cc_begin_key in codedict:
            typedict[codetype].custom_code_begin.extend(codedict[cc_begin_key])
        cc_end_key = 'CC:' + codetype + ':end#none#none'
        if cc_end_key in codedict:
            typedict[codetype].custom_code_end.extend(codedict[cc_end_key])

    # Save the code sessions that need to be updated
    # Keep track of the files that are created
    for key in codedict:
        if not key.startswith('CC:'):
            [inputtype, inputsession, inputgroup] = key.split('#')
            fname = os.path.join(outputdir, inputtype + '_' + inputsession + '_' + inputgroup + '.' + typedict[inputtype].extension)
            files[key].append(fname)
            sessionfile = open(fname, 'w', encoding=encoding)
            sessionfile.write(typedict[inputtype].shebang)
            if hasattr(typedict[inputtype], 'encoding_string'):
                sessionfile.write('\n')
                sessionfile.write(typedict[inputtype].set_encoding_string(encoding))
            sessionfile.write('\n')
            # Write all future imports.  The approach here should be modified if 
            # languages other than Python are ever supported.
            in_docstring = False 
            default_code = copy.copy(typedict[inputtype].default_code)
            for n, line in enumerate(default_code):
                # Detect __future__ imports
                if (line.startswith('from __future__') or 
                        line.startswith('import __future__') and 
                        not in_docstring):
                    sessionfile.write(line)
                    sessionfile.write('\n')
                    default_code[n] = ''
                # Ignore comments, empty lines, and lines with complete docstrings
                elif (line.startswith('\n') or line.startswith('#') or 
                        line.isspace() or
                        (line.count('"""') > 0 and line.count('"""')%2 == 0) or 
                        (line.count("'''") > 0 and line.count("'''")%2 == 0)):
                    pass
                # Detect if entering or leaving a docstring
                elif line.count('"""')%2 == 1 or line.count("'''")%2 == 1:
                    in_docstring = not in_docstring
                # Stop looking for future imports as soon as a non-comment, 
                # non-empty, non-docstring, non-future import line is found
                elif not in_docstring:
                    break
            in_docstring = False
            custom_code_begin = copy.copy(typedict[inputtype].custom_code_begin)
            for n, line in enumerate(custom_code_begin):
                # Detect __future__ imports
                if (line.startswith('from __future__') or 
                        line.startswith('import __future__') and 
                        not in_docstring):
                    sessionfile.write(line)
                    sessionfile.write('\n')
                    custom_code_begin[n] = ''
                # Ignore comments, empty lines, and lines with complete docstrings
                elif (line.startswith('\n') or line.startswith('#') or 
                        line.isspace() or
                        (line.count('"""') > 0 and line.count('"""')%2 == 0) or 
                        (line.count("'''") > 0 and line.count("'''")%2 == 0)):
                    pass
                # Detect if entering or leaving a docstring
                elif line.count('"""')%2 == 1 or line.count("'''")%2 == 1:
                    in_docstring = not in_docstring
                # Stop looking for future imports as soon as a non-comment, 
                # non-empty, non-docstring, non-future import line is found
                elif not in_docstring:
                    break
            # Check for __future__ in the actual code.  We only check the first 
            # four content-containing lines.  Note that line 0 of codedict[key]
            # sets PythonTeX variables.
            in_docstring = False
            for (n, line) in enumerate(codedict[key]):
                # Detect __future__ imports
                if (line.startswith('from __future__') or 
                        line.startswith('import __future__') and 
                        not in_docstring):
                    sessionfile.write(line)
                    codedict[key][n] = ''
                # Ignore comments, empty lines, and lines with complete docstrings
                elif (line.startswith('\n') or line.startswith('#') or 
                        line.isspace() or
                        (line.count('"""') > 0 and line.count('"""')%2 == 0) or 
                        (line.count("'''") > 0 and line.count("'''")%2 == 0)):
                    pass
                # Detect if entering or leaving a docstring
                elif line.count('"""')%2 == 1 or line.count("'''")%2 == 1:
                    in_docstring = not in_docstring
                # Stop looking for future imports as soon as a non-comment, 
                # non-empty, non-docstring, non-future import line is found
                elif not in_docstring:
                    break
            # Write the remainder of the default code
            for code in default_code:
                sessionfile.write(code)
                sessionfile.write('\n')
            sessionfile.write(typedict[inputtype].set_stdout_encoding(encoding))
            sessionfile.write('\n'.join(typedict[inputtype].utils_code))
            sessionfile.write('\n')
            
            sessionfile.write(typedict[inputtype].open_macrofile(outputdir,
                    inputtype + '_' + inputsession + '_' + inputgroup, encoding))
            sessionfile.write(typedict[inputtype].set_workingdir(workingdir))
            sessionfile.write(typedict[inputtype].set_inputs_const(inputtype, inputsession, inputgroup))
            sessionfile.write('\n')        
            # Write all custom code not involving __future__
            for code in custom_code_begin:
                sessionfile.write(code)
            sessionfile.write(''.join(codedict[key]))
            sessionfile.write('\n')
            sessionfile.write(''.join(typedict[inputtype].custom_code_end))
            sessionfile.write('\n\n\n')   
            sessionfile.write(typedict[inputtype].close_macrofile())
            sessionfile.write(typedict[inputtype].cleanup())
            sessionfile.close()




def do_multiprocessing(data, temp_data, old_data, typedict):
    outputdir = data['settings']['outputdir']
    jobname = data['jobname']
    fvextfile = data['settings']['fvextfile']
    hashdict = data['hashdict']
    encoding = data['encoding']
    update_code = temp_data['update_code']
    update_pygments = temp_data['update_pygments']
    pygments_settings = data['pygments_settings']
    update_pygments = temp_data['update_pygments']
    codedict = temp_data['codedict']
    consoledict = temp_data['consoledict']
    pytxcode = temp_data['pytxcode']
    keeptemps = data['settings']['keeptemps']
    files = data['files']
    macros = data['macros']
    pygments_files = data['pygments_files']
    pygments_macros = data['pygments_macros']
    pygments_style_defs = data['pygments_style_defs']
    errors = temp_data['errors']
    warnings = temp_data['warnings']
    stderr = data['settings']['stderr']
    stderrfilename = data['settings']['stderrfilename']
    dependencies = data['dependencies']
    exit_status = data['exit_status']
    workingdir = data['settings']['workingdir']
    verbose = temp_data['verbose']
    
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
    
    # Add in a Pygments process if applicable
    for key in update_pygments:
        if update_pygments[key] and not key.endswith('cons'):
            tasks.append(pool.apply_async(do_pygments, [outputdir,
                                                        jobname,
                                                        fvextfile,
                                                        pygments_settings,
                                                        update_pygments,
                                                        pytxcode,
                                                        encoding]))
            if verbose:
                print('    - Pygments process')
            break

    # Add console processes
    for key in consoledict:
        if update_code[key] or update_pygments[key]:
            tasks.append(pool.apply_async(run_console, [outputdir,
                                                        jobname,
                                                        fvextfile,
                                                        pygments_settings,
                                                        update_code,
                                                        update_pygments,
                                                        consoledict,
                                                        data['settings']['pyconbanner'],
                                                        data['settings']['pyconfilename'],
                                                        encoding]))
            if verbose:
                print('    - Console process')
            break
    
    # Add code processes.  Note that everything placed in the codedict 
    # needs to be executed, based on previous testing, except for custom code.
    for key in codedict:
        if not key.startswith('CC:'):
            [inputtype, inputsession, inputgroup] = key.split('#')
            tasks.append(pool.apply_async(run_code, [inputtype,
                                                     inputsession,
                                                     inputgroup,
                                                     outputdir,
                                                     typedict[inputtype].command,
                                                     typedict[inputtype].command_options,
                                                     typedict[inputtype].extension,
                                                     stderr,
                                                     stderrfilename,
                                                     keeptemps,
                                                     encoding,
                                                     temp_data['hashdependencies'],
                                                     workingdir]))
            if verbose:
                print('    - Code process ' + ':'.join([inputtype, inputsession, inputgroup]))
    
    # Execute the processes
    pool.close()
    pool.join()
    
    # Get the outputs of processes
    # Get the files and macros created.  Get the number of errors and warnings
    # produced.  Get any messages returned.  Get the exit_status, which is a 
    # dictionary of code that failed and thus must be run again (its hash is
    # set to a null string).
    messages = []
    for task in tasks:
        result = task.get()
        if result['process'] == 'code':
            key = result['key']
            files[key].extend(result['files'])
            macros[key].extend(result['macros'])
            errors += result['errors']
            warnings += result['warnings']
            exit_status[key] = (result['errors'], result['warnings'])
            messages.extend(result['messages'])        
            dependencies[key] = result['dependencies']            
        elif result['process'] == 'pygments':
            pygments_files.update(result['pygments_files'])
            pygments_macros.update(result['pygments_macros'])
            errors += result['errors']
            warnings += result['warnings']
            messages.extend(result['messages'])        
        elif result['process'] == 'console':
            files.update(result['files'])
            macros.update(result['macros'])
            pygments_files.update(result['pygments_files'])
            pygments_macros.update(result['pygments_macros'])
            for key in consoledict:
                errors += result['errors'][key]
                warnings += result['warnings'][key]
                exit_status[key] = (result['errors'][key], result['warnings'][key])
            messages.extend(result['messages'])
            dependencies.update(result['dependencies'])
    
    # Save all content
    # #### Should optimize to avoid saving if nothing changed
    macro_file = open(os.path.join(outputdir, jobname + '.pytxmcr'), 'w', encoding=encoding)
    for key in macros:
        macro_file.write(''.join(macros[key]))
    macro_file.close()
    pygments_macro_file = open(os.path.join(outputdir, jobname + '.pytxpyg'), 'w', encoding=encoding)
    for key in pygments_style_defs:
        pygments_macro_file.write(''.join(pygments_style_defs[key]))
    for key in pygments_macros:
        pygments_macro_file.write(''.join(pygments_macros[key]))
    pygments_macro_file.close()
    
    # Print any errors and warnings.
    if messages:
        print('\n'.join(messages))
    sys.stdout.flush()
    # Store errors and warnings back into temp_data
    # This is needed because they are ints and thus immutable
    temp_data['errors'] = errors
    temp_data['warnings'] = warnings




def run_code(inputtype, inputsession, inputgroup, outputdir, command, 
             command_options, extension, stderr, stderrfilename, keeptemps,
             encoding, hashdependencies, workingdir):
    '''
    Function for multiprocessing code files
    '''
    # Create what's needed for storing results
    currentkey = inputtype + '#' + inputsession + '#' + inputgroup
    files = []
    macros = []
    errors = 0
    warnings = 0
    messages = []
    dependencies = dict()
    
    # We need to let the user know we are switching code files
    # We check at the end to see if there were indeed any errors and warnings
    # and if not, clear messages.
    messages.append('\n----  Errors and Warnings for ' + ':'.join([inputtype, inputsession, inputgroup]) + '  ----')
    
    # Open files for stdout and stderr, run the code, then close the files
    basename = inputtype + '_' + inputsession + '_' + inputgroup
    outfile = open(os.path.join(outputdir, basename + '.out'), 'w', encoding=encoding)
    errfile = open(os.path.join(outputdir, basename + '.err'), 'w', encoding=encoding)
    # Note that command is a string, but command_options is a list (defaults to [])
    exec_cmd = [command] + command_options + [os.path.join(outputdir, basename + '.' + extension)]
    # Use .wait() so that code execution finishes before the next process is started
    subprocess.Popen(exec_cmd, stdout=outfile, stderr=errfile).wait()
    outfile.close()
    errfile.close()
    
    # Process saved stdout into file(s) that are included in the TeX document.
    #
    # Go through the saved output line by line, and save any printed content 
    # to its own file, named based on instance.
    # 
    # The end result could also be achieved (perhaps more efficiently in some 
    # cases) by redefining the print function or by redirecting stdout to 
    # StringIO within each individual script.  Redefining the print function
    # would miss any content sent to stdout directly, without the print 
    # function as intermediary.  StringIO could be nice, but is problematic.  
    # Under Python 2, StringIO can be slow, so we have cStringIO, but it 
    # can't accept unicode.  Using io.StringIO doesn't work either, because 
    # it requires unicode and would thus require either unicode_literals or a 
    # unicode prefix or function.  So saving stdout to a file is just much 
    # simpler.  It also has the advantage of being the most general solution; 
    # it could be applied to additional languages without modification.
    #
    # The very end of the stdout lists dependencies, if any, so we start by
    # removing and processing those.
    out_file_name = os.path.join(outputdir, basename + '.out')
    if os.path.isfile(out_file_name):
        f = open(out_file_name, 'r', encoding=encoding)
        outfile = f.readlines()
        f.close()
        # Start by getting and processing any dependencies and any specified
        # created files
        n = len(outfile) - 1
        while n >= 0 and not outfile[n].startswith('=>PYTHONTEX'):
            n -= 1
        if n >= 0 and outfile[n].startswith('=>PYTHONTEX:CREATED#'):
            for created in outfile[n+1:]:
                created = os.path.normcase(created.rstrip('\r\n'))
                if not os.path.isabs(created) and created == os.path.expanduser(created):
                    created = os.path.join(workingdir, created)
                files.append(created)
            outfile = outfile[:n]
            files.extend(created)
        n = len(outfile) - 1
        while n >= 0 and not outfile[n].startswith('=>PYTHONTEX'):
            n -= 1
        if n >= 0 and outfile[n].startswith('=>PYTHONTEX:DEPENDENCIES#'):
            # Create a set of dependencies, to eliminate duplicates in the event
            # that there are any.  This is mainly useful when dependencies are
            # automatically determined (for example, through redefining open()), 
            # may be specified multiple times as a result, and are hashed (and 
            # of a large enough size that hashing time is non-negligible.)
            deps = set([dep.rstrip('\r\n') for dep in outfile[n+1:]])
            outfile = outfile[:n]
            dependencies_hasher = defaultdict(sha1)
            for dep in deps:
                # We need to know if the path is relative (based off the 
                # working directory) or absolute.  We can't use 
                # os.path.isabs() alone for determining the distinction, 
                # because we must take into account the possibility of an
                # initial ~ (tilde) standing for the home directory.
                dep_file = os.path.expanduser(os.path.normcase(dep))
                if not os.path.isabs(dep_file):
                    dep_file = os.path.join(workingdir, dep_file)
                if not os.path.isfile(dep_file):
                    # If we can't find the file, we hash a null string and issue 
                    # an error.  We don't need to change the exit status.  If the 
                    # code does depend on the file, there will be a separate 
                    # error when the code attempts to use the file.  If the code 
                    # doesn't really depend on the file, then the error will be 
                    # raised again anyway the next time PythonTeX runs when the 
                    # dependency is listed but not found.
                    dependencies_hasher[dep].update(''.encode(encoding))
                    messages.append('* PythonTeX error')
                    messages.append('    Cannot find dependency "' + dep + '"')
                    messages.append('    It belongs to ' + ':'.join([inputtype, inputsession, inputgroup]))
                    messages.append('    Relative paths to dependencies must be specified from the working directory.')
                    errors += 1                
                elif hashdependencies:
                    # Read and hash the file in binary.  Opening in text mode 
                    # would require an unnecessary decoding and encoding cycle.
                    f = open(dep_file, 'rb')
                    dependencies_hasher[dep].update(f.read())
                    f.close()
                else:
                    dependencies_hasher[dep].update(str(os.path.getmtime(dep_file)).encode(encoding))
            for dep in dependencies_hasher:
                dependencies[dep] = dependencies_hasher[dep].hexdigest()
        
        inputinstance = ''
        printfile = []    
        for line in outfile:
            # If the line contains the text '=>PYTHONTEX:PRINT#', we are 
            # switching between instances; if so, we need to save any printed 
            # content from the last session and get the inputinstance for the 
            # current session.
            if line.startswith('=>PYTHONTEX:PRINT#'):
                # Take care of any printed content from the last block
                if printfile:
                    if inputinstance == 'customcode':
                        messages.append('* PythonTeX warning:')
                        messages.append('    Custom code for "' + inputtype + '" attempted to print or write to stdout')
                        messages.append('    This is not supported; use a normal code command or environment')
                        messages.append('    The following content was written:')
                        messages.append('')
                        messages.extend(['    ' + printline.rstrip('\r\n') for printline in printfile])
                        warnings += 1
                    else:
                        fname = os.path.join(outputdir, basename + '_' + inputinstance + '.stdout')
                        files.append(fname)
                        f = open(fname, 'w', encoding=encoding)
                        f.write(''.join(printfile))
                        f.close()
                    printfile = []
                inputinstance = line.split('#', 2)[1]
            else:
                printfile.append(line)
        # After the last line of output is processed, there may be content in 
        # the printfile list that has not yet been saved, so we take care of that.
        if printfile:
            if inputinstance == 'customcode':
                messages.append('* PythonTeX warning:')
                messages.append('    Custom code for "' + inputtype + '" attempted to print or write to stdout')
                messages.append('    This is not supported; use a normal code command or environment')
                messages.append('    The following content was written:')
                messages.append('')
                messages.extend(['    ' + printline.rstrip('\r\n') for printline in printfile])
                warnings += 1
            else:
                fname = os.path.join(outputdir, basename + '_' + inputinstance + '.stdout')
                files.append(fname)
                f = open(fname, 'w', encoding=encoding)
                f.write(''.join(printfile))
                f.close()
            printfile = []
    
    # Load the macros
    macrofile = os.path.join(outputdir, basename + '.pytxmcr')
    if os.path.isfile(macrofile):
        f = open(macrofile, 'r', encoding=encoding)
        macros = f.readlines()
        f.close()

    # Process error messages
    # Store 
    err_file_name = os.path.join(outputdir, basename + '.err')
    code_file_name = os.path.join(outputdir, basename + '.' + typedict[inputtype].extension)
    # Only work with files that have a nonzero size 
    if os.path.isfile(err_file_name) and os.stat(err_file_name).st_size != 0:
        # Open error and code files.
        # We can't just use the code in memory, because the full script 
        # file was written but never fully assembled in memory.
        f = open(err_file_name, encoding=encoding)
        err_file = f.readlines()
        f.close()
        f = open(code_file_name, encoding=encoding)
        code_file = f.readlines()
        f.close()
        
        for n, errline in enumerate(err_file):
            if (basename in errline and 
                    (search('line \d+', errline) or search(':\d+:', errline))):
                # Try to determine if we are dealing with a warning or an 
                # error.
                index = n
                while index < len(err_file):
                    if 'Warning:' in err_file[index]:
                        warnings += 1
                        type = 'warning'
                        break
                    elif 'Error:' in err_file[index]:
                        errors += 1
                        type = 'error'
                        break
                    index += 1
                if index == len(err_file): #Wasn't resolved
                    errors += 1
                    type = 'error (?)'
                # Find source of error or warning in code
                # Offset by one for zero indexing, one for previous line
                try:
                    errlinenumber = int(search('line (\d+)', errline).groups()[0]) - 2
                except:
                    errlinenumber = int(search(':(\d+):', errline).groups()[0]) - 2
                offset = -1
                while errlinenumber >= 0 and not code_file[errlinenumber].startswith('pytex.inputline = '):
                    errlinenumber -= 1
                    offset += 1
                if errlinenumber >= 0:
                    codelinenumber, codelineextra = match('pytex\.inputline = \'(\d+)(.*)\'', code_file[errlinenumber]).groups()
                    codelinenumber = int(codelinenumber) + offset
                    messages.append('* PythonTeX code ' + type + ' on line ' + str(codelinenumber) + codelineextra + ':')
                else:
                    messages.append('* PythonTeX code error.  Error line cannot be determined.')
                    messages.append('  Error is likely due to system and/or PythonTeX-generated code.')
            messages.append('  ' + errline.rstrip('\r\n'))
        # Take care of saving .stderr, if needed
        if stderr:
            # Need to keep track of whether successfully found a name and line number
            errkey = None
            # Need a dict for storing processed results
            # Especially in the case of warnings, there may be stderr content
            # for multiple code snippets
            errdict = defaultdict(list)
            # Loop through the error file
            for (n, errline) in enumerate(err_file):
                # When the basename is found with a line number, determine
                # the inputinstance and the fixed line number.  The fixed 
                # line number is the line number counted based on 
                # non-inline user-generated code, not counting anything 
                # that is automatically generated or any custom_code* that
                # is not typeset.  If it isn't in a code or block 
                # environment, where it could have line numbers, it 
                # doesn't count.
                if (basename in errline and 
                        (search('line \d+', errline) or search(':\d+:', errline))):
                    if search('line \d+', errline):
                        lineform = True
                    else:
                        lineform = False
                    # Get the inputinstance
                    if lineform:
                        errlinenumber = int(search('line (\d+)', errline).groups()[0]) - 2
                    else:
                        errlinenumber = int(search(':(\d+):', errline).groups()[0]) - 2
                    stored_errlinenumber = errlinenumber
                    while errlinenumber >= 0 and not code_file[errlinenumber].startswith('pytex.inputinstance = '):
                        errlinenumber -= 1
                    if errlinenumber >= 0:
                        inputinstance = match('pytex\.inputinstance = \'(.+)\'', code_file[errlinenumber]).groups()[0]
                    else:
                        messages.append('* PythonTeX error')
                        messages.append('    Could not parse stderr into a .stderr file')
                        messages.append('    The offending file was ' + err_file_name)
                        errors += 1
                        break
                    errlinenumber = stored_errlinenumber
                    while errlinenumber >= 0 and not code_file[errlinenumber].startswith('pytex.inputcommand = '):
                        errlinenumber -= 1
                    if errlinenumber >= 0:
                        if 'inline' in code_file[errlinenumber]:
                            messages.append('* PythonTeX error')
                            messages.append('    An inline command cannot be used to create stderr content')
                            messages.append('    Inline commands do not have proper line numbers for stderr')
                            messages.append('    The offending session was ' + ':'.join([inputtype, inputsession, inputgroup]))
                            errors += 1
                            break
                    else:
                        messages.append('* PythonTeX error')
                        messages.append('    Could not parse stderr into a .stderr file')
                        messages.append('    The offending file was ' + err_file_name)
                        errors += 1
                        break
                    # Get the fixed line number
                    should_count = False
                    fixedline = 0
                    # Need to stop counting when we reach the "real" line
                    # number of the error.  Need +1 because stored_errlinenumber
                    # was the zero-index line before the error actually 
                    # occurred.  All of this depends on the precise 
                    # spacing in the automatically generated scripts.
                    breaklinenumber = stored_errlinenumber + 1
                    for (m, line) in enumerate(code_file):
                        if line.startswith('pytex.inputinstance = '):
                            if should_count:
                                fixedline -= 2
                            should_count = False
                        elif line.startswith('pytex.inputcommand = ') and 'inline' not in line:
                            should_count = True
                            fixedline -= 3
                        elif should_count:
                            fixedline += 1
                        if m == breaklinenumber:
                            break
                    # Take care of settings governing the name that 
                    # appears in .stderr
                    fullbasename = os.path.join(outputdir, basename)
                    if stderrfilename == 'full':
                        errline = errline.replace(fullbasename, basename)
                    elif stderrfilename == 'session':
                        errline = errline.replace(fullbasename, inputsession)
                    elif stderrfilename == 'genericfile':
                        errline = errline.replace(fullbasename + '.' + typedict[inputtype].extension, '<file>')
                    elif stderrfilename == 'genericscript':
                        errline = errline.replace(fullbasename + '.' + typedict[inputtype].extension, '<script>')
                    if lineform:
                        errline = sub('line \d+', 'line ' + str(fixedline), errline)
                    else:
                        errline = sub(':\d+:', ':' + str(fixedline) + ':', errline)
                    errkey = basename + '_' + inputinstance
                    errdict[errkey].append(errline)
                elif errkey is not None:
                    errdict[errkey].append(errline)
                else:
                    messages.append('* PythonTeX warning')
                    messages.append('    Could not parse stderr into a .stderr file')
                    messages.append('    The offending file was ' + err_file_name)
                    messages.append('    Remember that .stderr files are only possible for block and code environments')
                    warnings += 1
                    break
            if errdict:
                for key in errdict:
                    stderr_file_name = os.path.join(outputdir, key + '.stderr')
                    f = open(stderr_file_name, 'w', encoding=encoding)
                    f.write(''.join(errdict[key]))
                    f.close()
                    files.append(stderr_file_name)


    # Clean up temp files, and update the list of existing files
    if keeptemps == 'none':
        for ext in [typedict[inputtype].extension, 'pytxmcr', 'out', 'err']:
            fname = os.path.join(outputdir, basename + '.' + ext)
            if os.path.isfile(fname):
                os.remove(fname)
    elif keeptemps == 'code':
        for ext in ['pytxmcr', 'out', 'err']:
            fname = os.path.join(outputdir, basename + '.' + ext)
            if os.path.isfile(fname):
                os.remove(fname)
        files.append(os.path.join(outputdir, basename + '.' + typedict[inputtype].extension))
    elif keeptemps == 'all':
        for ext in [typedict[inputtype].extension, 'pytxmcr', 'out', 'err']:
            files.append(os.path.join(outputdir, basename + '.' + ext))

    # If there were no errors or warnings, clear the default message header
    if len(messages) == 1:
        messages = []
    
    # Return a dict of dicts of results
    return {'process': 'code',
            'key': currentkey,
            'files': files,
            'macros': macros,
            'errors': errors,
            'warnings': warnings,
            'messages': messages,
            'dependencies': dependencies}    




def do_pygments(outputdir, jobname, fvextfile, pygments_settings, 
                update_pygments, pytxcode, encoding):
    '''
    Create Pygments content.
    
    To be run during multiprocessing.
    '''
    # Eventually, it might be nice to add some code that inserts line breaks 
    # to keep typeset code from overflowing the margins.  That could require 
    # a info about page layout from the LaTeX side and it might be tricky to 
    # do good line breaking, but it should be considered.
    
    # Create what's needed for storing results
    pygments_files = defaultdict(list)
    pygments_macros = defaultdict(list)
    errors = 0
    warnings = 0
    messages = []
    
    # Create dicts of formatters and lexers.
    formatter = dict()
    lexer = dict()
    for codetype in pygments_settings:
        if not codetype.endswith('_cons'):
            pyglexer = pygments_settings[codetype]['lexer']
            pygstyle = pygments_settings[codetype]['style']
            pygtexcomments = pygments_settings[codetype]['texcomments']
            pygmathescape = pygments_settings[codetype]['mathescape']
            commandprefix = pygments_settings[codetype]['commandprefix']
            formatter[codetype] = LatexFormatter(style=pygstyle, 
                    texcomments=pygtexcomments, mathescape=pygmathescape, 
                    commandprefix=commandprefix)
            lexer[codetype] = get_lexer_by_name(pyglexer)
    
    # Actually parse and highlight the code.
    #
    # We need to initialize an empty list for storing code and a dict to keep 
    # track of instances, so that repeated instances can be skipped.  Note 
    # that the parsing for code execution can't be reused here.  Highlighting 
    # must be done instance by instance, while parsing for execution 
    # concatenates instances into a single (modified) list, which is saved 
    # to a file and then executed.  Furthermore, we may need to highlight 
    # code that hasn't changed but has new highlighting settings.
    code = []
    def negonefactory():
        return -1
    lastinstance = defaultdict(negonefactory)
    # Parse the code and highlight according to update_pygments
    for codeline in pytxcode:
        # Check for the beginning of new a command/environment.  If found, 
        # save any code from the last (type, session, group, instance), and 
        # detemine how to proceed.
        if codeline.startswith('=>PYTHONTEX#'):
            # Process any code from the last (type, session, group, instance).
            # Save it either to pygments_macros or to an external file, depending 
            # on size.  Keep track of external files that are created, for 
            # cleanup.
            if code:
                processed = highlight(''.join(code), lexer[inputtype], 
                                      formatter[inputtype])
                # Use macros if dealing with an inline command or if content
                # is sufficiently short
                if inputcommand.startswith('inline') or len(code) < fvextfile:
                    # Highlighted code brought in via macros needs SaveVerbatim
                    processed = sub(r'\\begin{Verbatim}\[(.+)\]', 
                                    r'\\begin{{SaveVerbatim}}[\1]{{pytx@{0}@{1}@{2}@{3}}}'.format(inputtype, inputsession, inputgroup, inputinstance), processed, count=1)
                    processed = processed.rsplit('\\', 1)[0] + '\\end{SaveVerbatim}\n\n'                    
                    pygments_macros[currentkey].append(processed)
                else:
                    if inputsession.startswith('EXT:'):
                        fname = os.path.join(outputdir, inputsession.replace('EXT:', '') + '.pygtex')
                        f = open(fname, 'w', encoding=encoding)
                    else:
                        fname = os.path.join(outputdir, inputtype + '_' + inputsession + '_' + inputgroup + '_' + inputinstance + '.pygtex')
                        f = open(fname, 'w', encoding=encoding)
                    f.write(processed)
                    f.close()
                    pygments_files[currentkey].append(fname)
                code=[]
            #Extract parameters and prepare for the next block of code
            [inputtype, inputsession, inputgroup, inputinstance, inputcommand] = codeline.split('#', 7)[1:6]
            currentkey = inputtype + '#' + inputsession + '#' + inputgroup
            currentinstance = int(inputinstance)
            # We have to check for environments that are read multiple times 
            # (and thus written to .pytxcode multiple times) by LaTeX.  We 
            # need to ignore any environments and commands that do NOT need 
            # their code typeset.  If we need to highlight an external file, 
            # we should bring in its contents.
            proceed = False                          
            if (not currentkey.startswith('CC:') and 
                    update_pygments[currentkey] and (inputgroup.endswith('verb') or 
                    inputcommand == 'block' or inputcommand == 'inlineb')):
                if inputsession.startswith('EXT:'):
                    # Deal with an external file
                    # No code will follow, so no need to worry about proceed
                    extfile = os.path.normcase(inputsession.replace('EXT:', ''))
                    try:                    
                        f = open(extfile, 'r', encoding=encoding)
                        code = f.readlines()
                        f.close()
                    except (UnicodeEncodeError, UnicodeDecodeError):
                        messages.append('* PythonTeX error')
                        messages.append('    Cannot read file ' + extfile + ' using encoding ' + encoding + '.')
                        messages.append('    Set PythonTeX to use a different encoding, or change the encoding of the file.')
                        messages.append('    UTF-8 encoding is recommended for all files.')
                        errors += 1
                        exist_status[currentkey] = ''
                elif lastinstance[currentkey] < currentinstance:  
                    lastinstance[currentkey] = currentinstance
                    proceed = True
        #Only collect code if it should be highlighted
        elif proceed:
            code.append(codeline)   
    # Take care of anything left in the code list
    # This must be a direct copy of the commands from above
    if code:
        processed = highlight(''.join(code), lexer[inputtype], 
                              formatter[inputtype])
        # Use macros if dealing with an inline command or if content
        # is sufficiently short
        if inputcommand.startswith('inline') or len(code) < fvextfile:
            # Highlighted code brought in via macros needs SaveVerbatim
            processed = sub(r'\\begin{Verbatim}\[(.+)\]', 
                            r'\\begin{{SaveVerbatim}}[\1]{{pytx@{0}@{1}@{2}@{3}}}'.format(inputtype, inputsession, inputgroup, inputinstance), processed, count=1)
            processed = processed.rsplit('\\', 1)[0] + '\\end{SaveVerbatim}\n\n'                    
            pygments_macros[currentkey].append(processed)
        else:
            if inputsession.startswith('EXT:'):
                fname = os.path.join(outputdir, inputsession.replace('EXT:', '') + '.pygtex')
                f = open(fname, 'w', encoding=encoding)
            else:
                fname = os.path.join(outputdir, inputtype + '_' + inputsession + '_' + inputgroup + '_' + inputinstance + '.pygtex')
                f = open(fname, 'w', encoding=encoding)
            f.write(processed)
            f.close()
            pygments_files[currentkey].append(fname)
    
    # Return a dict of dicts of results
    return {'process': 'pygments',
            'pygments_files': pygments_files,
            'pygments_macros': pygments_macros,
            'errors': errors,
            'warnings': warnings,
            'messages': messages} 




def run_console(outputdir, jobname, fvextfile, pygments_settings, update_code,
                update_pygments, consoledict, pyconbanner, pyconfilename,
                encoding):
    '''
    Use Python's code module to typeset emulated Python interactive sessions,
    optionally highlighting with Pygments.
    '''
    # Create what's needed for storing results
    files = defaultdict(list)
    macros = defaultdict(list)
    pygments_files = defaultdict(list)
    pygments_macros = defaultdict(list)
    errors = defaultdict(int)
    warnings = defaultdict(int)
    messages = []
    dependencies = dict()
    
    # Lazy import what's needed
    import code
    from collections import deque
    #// Python 2
    ## Can't use io for everything, because it requires Unicode
    ## The current system doesn't allow for Unicode under Python 2
    #try:
    #    from cStringIO import StringIO
    #except ImportError:
    #    from StringIO import StringIO
    #\\ End Python 2
    #// Python 3
    from io import StringIO
    #\\ End Python 3
    
    
    class Console(code.InteractiveConsole):
        '''
        A subclass of code.InteractiveConsole that takes a list and treats it
        as console input.
        '''
        
        def __init__(self, banner, filename):
            if banner == 'none':
                self.banner = 'NULL BANNER'
            elif  banner == 'standard':
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
    
        def consolize(self, console_code):
            self.console_code = deque(console_code)
            self.lastinputinstance = -1
            old_stdout = sys.stdout
            sys.stdout = self.iostdout
            self.interact(self.banner)
            sys.stdout = old_stdout
            self.session_log = self.iostdout.getvalue()
    
        def raw_input(self, prompt):
            # Have to do a lot of looping and trying to make sure we get 
            # something valid to execute
            try:
                line = self.console_code.popleft().rstrip('\r\n')
            except IndexError:
                raise EOFError
            while line.startswith('=>PYTHONTEX#'):
                inputinstance = int(line.split('#', 5)[4])
                while self.lastinputinstance == inputinstance:
                    try:
                        line = self.console_code.popleft().rstrip('\r\n')
                    except IndexError:
                        raise EOFError
                    if line.startswith('=>PYTHONTEX#'):
                        inputinstance = int(line.split('#', 5)[4])
                self.lastinputinstance = inputinstance
                try:
                    line = self.console_code.popleft().rstrip('\r\n')
                    self.write('=>PYTHONTEX:INSTANCE#' + str(inputinstance) + '#\n')
                except IndexError:
                    raise EOFError
            if line or prompt == sys.ps2:
                self.write('{0}{1}\n'.format(prompt, line))
            else:
                self.write('\n')
            return line
        
        def write(self, data):
            self.iostdout.write(data)
    
    for key in consoledict:
        # Python 2 doesn't support non-ASCII in console environment,
        # so do a quick check for this by trying to encode in ASCII
        #// Python 2
        #try:
        #    ''.join(consoledict[key]).encode('ascii')
        #except (UnicodeEncodeError, UnicodeDecodeError):
        #    inputline = consoledict[key][0].rsplit('#', 2)[1]
        #    messages.append('* PythonTeX error')
        #    messages.append('    Non-ascii character(s) near line ' + inputline)
        #    messages.append('    Non-ascii characters are not allowed in console environments under Python 2')
        #    errors[key] += 1
        #    continue
        #\\ End Python 2
        [inputtype, inputsession, inputgroup] = key.split('#')
        con = Console(pyconbanner, pyconfilename)
        con.consolize(consoledict[key])
        result = con.session_log.splitlines()
        console_content = []
        inputinstance = -1
        # Determine if Pygments is needed
        inputtypecons = inputtype + '_cons'
        if inputtypecons in pygments_settings:
            pygmentize = True
            pyglexer = pygments_settings[inputtypecons]['lexer']
            pygstyle = pygments_settings[inputtypecons]['style']
            pygtexcomments = pygments_settings[inputtypecons]['texcomments']
            pygmathescape = pygments_settings[inputtypecons]['mathescape']
            commandprefix = pygments_settings[inputtypecons]['commandprefix']
            if 'python3' in pygments_settings[inputtypecons]:
                python3 = pygments_settings[inputtypecons]['python3']
                formatter = LatexFormatter(style=pygstyle, 
                        texcomments=pygtexcomments, mathescape=pygmathescape, 
                        commandprefix=commandprefix, python3=python3)
            else:
                formatter = LatexFormatter(style=pygstyle, 
                        texcomments=pygtexcomments, mathescape=pygmathescape, 
                        commandprefix=commandprefix)
            lexer = get_lexer_by_name(pyglexer)
        else:
            pygmentize = False
        # Need to put the PythonTeX delimiter first, before the banner
        # If there is a null banner, remove it
        if pyconbanner == 'none':
            result = result[1:]
        else:
            for n, line in enumerate(result):
                if line.startswith('=>PYTHONTEX:INSTANCE#'):
                    break
            delim = result[n]
            result[1:n+1] = result[0:n]
            result[0] = delim
        for line in result:
            if line.startswith('=>PYTHONTEX:INSTANCE#'):
                if console_content:
                    if console_content[-1].isspace():
                        console_content[-1] = ''
                    if pygmentize:
                        processed = highlight(''.join(console_content), lexer, formatter)
                        if len(console_content) < fvextfile:                            
                            processed = sub(r'\\begin{Verbatim}\[(.+)\]', 
                                            r'\\begin{{SaveVerbatim}}[\1]{{pytx@{0}@{1}@{2}@{3}}}'.format(inputtype, inputsession, inputgroup, inputinstance), processed, count=1)
                            processed = processed.rsplit('\\', 1)[0] + '\\end{SaveVerbatim}\n\n'
                            pygments_macros[key].append(processed)
                        else:
                            fname = os.path.join(outputdir, inputtype + '_' + inputsession + '_' + inputgroup + '_' + inputinstance + '.pygtex')
                            f = open(fname, 'w', encoding=encoding)
                            f.write(processed)
                            f.close()
                            pygments_files[key].append(fname)  
                    else:
                        if len(console_content) < fvextfile:
                            processed = ('\\begin{{SaveVerbatim}}{{pytx@{0}@{1}@{2}@{3}}}\n'.format(inputtype, inputsession, inputgroup, inputinstance) + 
                                    ''.join(console_content) + '\\end{SaveVerbatim}\n\n')
                            macros[key].append(processed)
                        else:
                            processed = ('\\begin{Verbatim}\n' + 
                                    ''.join(console_content) + '\\end{Verbatim}\n\n')
                            fname = os.path.join(outputdir, inputtype + '_' + inputsession + '_' + inputgroup + '_' + inputinstance + '.tex')
                            f = open(fname, 'w', encoding=encoding)
                            f.write(processed)
                            f.close()
                            files[key].append(fname) 
                inputinstance = line.split('#')[1]
            else:
                console_content.append(line + '\n')
        if console_content:
            if console_content[-1].isspace():
                console_content[-1] = ''
            if pygmentize:
                processed = highlight(''.join(console_content), lexer, formatter)
                if len(console_content) < fvextfile:                              
                    processed = sub(r'\\begin{Verbatim}\[(.+)\]', 
                                    r'\\begin{{SaveVerbatim}}[\1]{{pytx@{0}@{1}@{2}@{3}}}'.format(inputtype, inputsession, inputgroup, inputinstance), processed, count=1)
                    processed = processed.rsplit('\\', 1)[0] + '\\end{SaveVerbatim}\n\n'
                    pygments_macros[key].append(processed)
                else:
                    fname = os.path.join(outputdir, inputtype + '_' + inputsession + '_' + inputgroup + '_' + inputinstance + '.pygtex')
                    f = open(fname, 'w', encoding=encoding)
                    f.write(processed)
                    f.close()
                    pygments_files[key].append(fname)  
            else:
                if len(console_content) < fvextfile:
                    processed = ('\\begin{{SaveVerbatim}}{{pytx@{0}@{1}@{2}@{3}}}\n'.format(inputtype, inputsession, inputgroup, inputinstance) + 
                            ''.join(console_content) + '\\end{SaveVerbatim}\n\n')
                    macros[key].append(processed)
                else:
                    processed = ('\\begin{Verbatim}\n' + 
                            ''.join(console_content) + '\\end{Verbatim}\n\n')
                    fname = os.path.join(outputdir, inputtype + '_' + inputsession + '_' + inputgroup + '_' + inputinstance + '.pygtex')
                    f = open(fname, 'w', encoding=encoding)
                    f.write(processed)
                    f.close()
                    files[key].append(fname)
           
    # Return a dict of dicts of results
    return {'process': 'console',
            'files': files,
            'macros': macros,
            'pygments_files': pygments_files,
            'pygments_macros': pygments_macros,
            'errors': errors,
            'warnings': warnings,
            'messages': messages,
            'dependencies': dependencies} 




def save_data(data):
    '''
    Save data for the next run
    '''
    pythontex_data_file = os.path.join(data['settings']['outputdir'], 'pythontex_data.pkl')
    f = open(pythontex_data_file, 'wb')
    pickle.dump(data, f, -1)
    f.close()




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
    data = {'version': version}
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
    #// Python 2
    #sys.stdout = codecs.getwriter(data['encoding'])(sys.stdout, 'strict')
    #sys.stderr = codecs.getwriter(data['encoding'])(sys.stderr, 'strict')
    #\\ End Python 2
    #// Python 3
    sys.stdout = codecs.getwriter(data['encoding'])(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter(data['encoding'])(sys.stderr.buffer, 'strict')
    #\\ End Python 3


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
    hash_code(data, temp_data, old_data, typedict)
    
    
    # Parse the code and write scripts for execution.
    parse_code_write_scripts(data, temp_data, typedict)
    
    
    # Execute the code and perform Pygments highlighting via multiprocessing.
    do_multiprocessing(data, temp_data, old_data, typedict)


    # Save data for the next run
    save_data(data)
    
    
    # Print exit message
    print('\n--------------------------------------------------')
    # If some rerun settings are used, there may be unresolved errors or 
    # warnings; if so, print a summary of those along with the current 
    # error and warning summary
    unresolved_errors = 0
    unresolved_warnings = 0
    if temp_data['rerun'] in ('errors', 'modified'):
        for key in data['exit_status']:
            if not temp_data['update_code'][key]:
                unresolved_errors += data['exit_status'][key][0]
                unresolved_warnings += data['exit_status'][key][1]
    if unresolved_warnings != 0 or unresolved_errors != 0:
        print('PythonTeX:  {0}'.format(data['raw_jobname']))
        print('    - Old:      {0} error(s), {1} warnings(s)'.format(unresolved_errors, unresolved_warnings))
        print('    - Current:  {0} error(s), {1} warnings(s)'.format(temp_data['errors'], temp_data['warnings']))        
    else:
        print('PythonTeX:  {0} - {1} error(s), {2} warnings(s)\n'.format(data['raw_jobname'], temp_data['errors'], temp_data['warnings']))

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