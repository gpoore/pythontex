#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
This is the main PythonTeX script.

Two versions of this script and the other PythonTeX scripts are provided.  One 
set of scripts, with names ending in "2", runs under Python 2.7.  These 
scripts will not run under 2.6 without at least a few modifications.  The 
other set of scripts, with names ending in "3", runs under Python 3.1 or 
greater.

This script needs to be able to import pythontex_types*.py; in general it 
should be in the same directory.  This script creates scripts that need to 
be able to import pythontex_utils*.py.  The location of that file is 
determined via the kpsewhich command, which is part of the Kpathsea library 
included with some TeX distributions, including TeX Live and MiKTeX.


Licensed under the BSD 3-Clause License:

Copyright (c) 2012, Geoffrey M. Poore

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
from re import match, sub, search
from collections import defaultdict
import subprocess
import multiprocessing
from hashlib import sha1
import codecs
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import LatexFormatter
import textwrap
#// Python 2
from pythontex_types2 import *
try:
    import cPickle as pickle
except:
    import pickle
from io import open
#\\ End Python 2
#// Python 3
#from pythontex_types3 import *
#import pickle
#\\ End Python 3


# Script parameters
# Version
version = '0.9beta3'




def process_argv(data, temp_data):
    '''
    Process command line options.
    
    Currently, we are only getting the job name and optionally the encoding.  
    All other options are passed via the file of code.
    '''
    
    # Make sure we have the right number of arguments; if so, process them
    if len(sys.argv) < 2:
        print('* PythonTeX error')
        print('    Incorrect number of command line arguments passed to pythontex*.py.')
        sys.exit(2)
    raw_jobname = sys.argv[1]
    # Strip off the .tex extension if it was passed, since we need the TeX \jobname
    if raw_jobname.endswith('.tex'):
        raw_jobname = raw_jobname.rsplit('.', 1)[0]
    
    # We need to see if the tex file exists.  If not, we issue a 
    # warning, but attempt to continue since it's possible a file with 
    # another extension is being compiled.
    if not os.path.isfile(raw_jobname + '.tex'):
        print('* PythonTeX warning')
        print('    Job name does not seem to correspond to a .tex document.')
        print('    Attempting to proceed.')
        temp_data['warnings'] += 1
    
    # We need a "sanitized" version of the jobname, with spaces and 
    # asterisks replaced with hyphens.  This is done to avoid TeX issues 
    # with spaces in file names, paralleling the approach taken in 
    # pythontex.sty.  From now on, we will use the sanitized version every 
    # time we create a file that contains the jobname string.  The raw 
    # version will only be used in reference to pre-existing files created 
    # on the TeX side, such as the .pytxcode file.
    jobname = raw_jobname.replace(' ', '-').replace('"', '').replace('*', '-')
    
    # We need to check to make sure that the "sanitized" jobname doesn't 
    # lead to a collision with a file that already has that name, so that 
    # two files attempt to use the same PythonTeX folder.
    # 
    # If <jobname>.tex and <raw_jobname>.tex both exist, we exit.
    # If <jobname>* and <raw_jobname>* both exist, we issue a warning but 
    # attempt to proceed.
    if jobname != raw_jobname:
        if os.path.isfile(jobname + '.tex') and os.path.isfile(raw_jobname + '.tex'):
            print('* PythonTeX error')
            print('    Directory naming collision between the following files:')
            print('      ' + raw_jobname + '.tex')
            print('      ' + jobname + '.tex')
            sys.exit(1)
        else:
            ls = os.listdir('.')
            collision = False
            for file in ls:
                if file.startswith(jobname):
                    collision = True
                    break
            if collision:
                print('* PythonTeX warning')
                print('    Potential directory naming collision between the following names:')
                print('      ' + raw_jobname)
                print('      ' + jobname + '*')
                print('    Attempting to proceed.')
                temp_data['warnings'] += 1
    # Set the encoding to a default value unless a command-line option was given
    if len(sys.argv) == 4:
        if sys.argv[2] in ('--coding', '--encoding'):
            encoding = sys.argv[3]
    else:
        encoding = 'utf-8'
    
    # Store the results in data
    data['raw_jobname'] = raw_jobname
    data['jobname'] = jobname    
    data['encoding'] = encoding



    
def load_code_get_settings(data, temp_data):
    '''
    Load the code file, process the settings contained in its first few lines,
    and remove the settings lines so that the remainder is ready for code 
    processing.
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
        sys.exit(1)

    # Process settings passed from the TeX side via the code file.
    #
    # Determine the output and working directories and other general settings.
    # Extract settings for Pygments.  Save these in a list of dictionaries.
    #
    # While processing settings, determine how many lines of the code file are 
    # devoted to settings, so that these can be removed.
    
    # Create a dict for Pygments settings
    # Each dict entry will itself be a dict
    pygments_settings = dict()
    # Keep track of the number of settings lines, so they can be removed later
    pytxcode_settings_offset = 0
    for line in pytxcode:
        if line.startswith('=>PYTHONTEX:SETTINGS#'):
            pytxcode_settings_offset += 1
            # A hash symbol "#" should never be within content, but be 
            # careful just in case
            content = line.replace('=>PYTHONTEX:SETTINGS#', '', 1).rsplit('#', 1)[0]
            if content.startswith('outputdir='):
                data['outputdir'] = content.split('=', 1)[1]
            elif content.startswith('workingdir='):
                data['workingdir'] = content.split('=', 1)[1]
            elif content.startswith('stderr='):
                content = content.split('=', 1)[1]
                if content in ('true', 'True'):
                    data['stderr'] = True
                else:
                    data['stderr'] = False
            elif content.startswith('stderrfilename='):
                data['stderrfilename'] = content.split('=', 1)[1]
            elif content.startswith('keeptemps='):
                data['keeptemps'] = content.split('=', 1)[1]
            elif content.startswith('pyfuture='):
                pyfuture = content.split('=', 1)[1]
                data['pyfuture'] = pyfuture
                #// Python 2
                # We save the pyfuture option regardless of the Python version,
                # but we only use it under Python 2.
                update_default_code2(pyfuture)
                #\\ End Python 2
            elif content.startswith('pygments='):
                content = content.split('=', 1)[1]
                if content in ('true', 'True'):
                    data['pygments'] = True
                else:
                    data['pygments'] = False
            elif content.startswith('fvextfile='):
                try:
                    fvextfile = int(content.split('=', 1)[1])                    
                except ValueError:
                    print('* PythonTeX error')
                    print('    Unable to parse package option fvextfile.')
                    sys.exit(1)
                if fvextfile < 0:
                    data['fvextfile'] = sys.maxsize
                elif fvextfile == 0:
                    data['fvextfile'] = 1
                    print('* PythonTeX warning')
                    print('    Invalid value for package option fvextfile.')
                    temp_data['warnings'] += 1
                else:
                    data['fvextfile'] = fvextfile
            elif content.startswith('pyglexer='):
                globalpyglexer = content.split('=', 1)[1]
                if globalpyglexer == '':
                    globalpyglexer = None
                data['pyglexer'] = globalpyglexer
            elif content.startswith('pygmentsglobal:'):
                options = content.split(':', 1)[1].strip('{}').replace(' ', '').split(',')
                # Set default values, modify based on settings
                globalpygstyle = None
                globalpygtexcomments = None
                globalpygmathescape = None
                for option in options:
                    if option.startswith('style='):
                        globalpygstyle = option.split('=', 1)[1]
                    elif option == 'texcomments':
                        globalpygtexcomments = True
                    elif option.startswith('texcomments='):
                        option = option.split('=', 1)[1]
                        if option == 'true' or option == 'True':
                            globalpygtexcomments = True
                    elif option == 'mathescape':
                        globalpygmathescape = True
                    elif option.startswith('mathescape='):
                        option = option.split('=', 1)[1]
                        if option == 'true' or option == 'True':
                            globalpygmathescape = True
                    elif option != '':
                        print('* PythonTeX warning')
                        print('    Unknown global Pygments option:  ' + option)
                        temp_data['warnings'] += 1
                # Store the global settings in pygments_settings.  Use a key 
                # that can't conflict with anything (inputtype can't ever 
                # contain a hash symbol).  This key is deleted later, as soon 
                # as it is no longer needed.  Note that no global lexer can be
                # specified. 
                pygments_settings['#GLOBAL'] = {'lexer': globalpyglexer, 
                                                'style': globalpygstyle,
                                                'texcomments': globalpygtexcomments,
                                                'mathescape': globalpygmathescape}
            elif content.startswith('pygmentsfamily:'):
                [inputtype, lexer, options] = content.split(':', 1)[1].replace(' ','').split(',', 2)
                if globalpyglexer is not None:
                    lexer = globalpyglexer
                options = options.strip('{}').split(',')
                # Set default values, modify based on settings
                pygstyle = 'default'
                pygtexcomments = False
                pygmathescape = False
                for option in options:
                    if option.startswith('style='):
                        pygstyle = option.split('=', 1)[1]
                    elif option == 'texcomments':
                        pygtexcomments = True
                    elif option.startswith('texcomments='):
                        option = option.split('=', 1)[1]
                        if option == 'true' or option == 'True':
                            pygtexcomments = True
                    elif option == 'mathescape':
                        pygmathescape = True
                    elif option.startswith('mathescape='):
                        option = option.split('=', 1)[1]
                        if option == 'true' or option == 'True':
                            pygmathescape = True
                    elif option != '':
                        print('* PythonTeX warning')
                        print('    Unknown Pygments option for ' + inputtype + ':  ' + '"' + option + '"')
                # Modify family settings based on global settings
                if globalpygstyle is not None:
                    pygstyle = globalpygstyle
                if globalpygtexcomments is not None:
                    pygtexcomments = globalpygtexcomments
                if globalpygmathescape is not None:
                    pygmathescape = globalpygmathescape
                pygments_settings[inputtype] = {'lexer': lexer,
                                                'style': pygstyle,
                                                'texcomments': pygtexcomments,
                                                'mathescape': pygmathescape,
                                                'commandprefix': 'PYG' + pygstyle}
            elif content.startswith('customcode:'):
                (inputtype, code) = content.split(':', 1)[1].split(',', 1)
                try:
                    code = eval(code)
                except:
                    print('* PythonTeX error)')
                    print('    Invalid custom code:  ' + code)
                    sys.exit(1)
                if not isinstance(code, list):
                    print('* PythonTeX error)')
                    print('    Invalid custom code:  ' + code)
                    sys.exit(1)
                typedict[inputtype].custom_code.extend(code)
            elif content.startswith('pyconbanner='):
                data['pyconbanner'] = content.split('=', 1)[1]
            elif content.startswith('pyconfilename='):
                data['pyconfilename'] = content.split('=', 1)[1]
            elif content.startswith('depythontex='):
                content = content.split('=', 1)[1]
                if content in ('true', 'True'):
                    data['depythontex'] = True
                else:
                    data['depythontex'] = False
            else:
                print('* PythonTeX warning')
                print('    Unknown option "' + content + '"')
                temp_data['warnings'] += 1
        else:
            break
    
    # Store all results in data that haven't already been stored.  Note that
    # all code is only stored in temp_data, since the thing we really need to 
    # save is not the code itself but rather a hash of the code.
    data['pygments_settings'] = pygments_settings
    # Remove code lines that correspond to settings.  These will always be 
    # present, and thus always need to be removed.
    pytxcode = pytxcode[pytxcode_settings_offset:]
    temp_data['pytxcode'] = pytxcode




def get_old_data(data, old_data):
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
    code should gracefully accomodate.
    '''

    # Create a string containing the name of the data file
    pythontex_data_file = os.path.join(data['outputdir'], 'pythontex_data.pkl')
    # Create a string containing the name of the pythontex_utils*.py file
    # Note that the file name depends on the Python version
    pythontex_utils_file = 'pythontex_utils' + str(sys.version_info[0]) +'.py'
    
    # Create a function for getting the path to the utils file, if needed
    def get_pythontex_path(pythontex_utils_file):
        '''
        Get the path to the PythonTeX scripts, via kpsewhich
        '''
        exec_cmd = ['kpsewhich', '--format', 'texmfscripts', pythontex_utils_file]
        try:
            # Get path, convert from bytes to unicode, and strip off 
            # end-of-line characters
            scriptpath_full = subprocess.check_output(exec_cmd).decode('utf-8').rstrip('\r\n')
        except OSError:
            print('* PythonTeX error')
            print('    Your system appears to lack kpsewhich.')
            sys.exit(1)
        except subprocess.CalledProcessError:
            print('* PythonTeX error')
            print('    kpsewhich is not happy with its arguments.')
            print('    This command was attempted:')
            print('      ' + ' '.join(exec_cmd))
            sys.exit(1)
        # Split the end of the path ("/pythontex_utils*.py")
        scriptpath = os.path.split(scriptpath_full)[0]
        return scriptpath
    
    # Load the old data if it exists
    if os.path.isfile(pythontex_data_file):
        f = open(pythontex_data_file, 'rb')
        old_data.update(pickle.load(f))
        f.close()
        temp_data['loaded_old_data'] = True
    else:
        temp_data['loaded_old_data'] = False
    # Set the scriptpath in the current data
    if temp_data['loaded_old_data']:
        if not os.path.isfile(os.path.join(old_data['scriptpath'], pythontex_utils_file)):
            data['scriptpath'] = get_pythontex_path(pythontex_utils_file)
        else:
            data['scriptpath'] = old_data['scriptpath']
    else:
        data['scriptpath'] = get_pythontex_path(pythontex_utils_file)
    
    # Set path for scripts, via the function from pythontex_types*.py
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
    # difference between the two approaches should be negligible.
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
    # Calculate hashes for each set of code (type, session, group).
    # We don't have to skip the first few lines of settings, because they have
    # already been removed.
    hasher = defaultdict(sha1)
    for codeline in pytxcode:
        # Detect the start of a new command/environment
        # Switch variables if so
        if codeline.startswith('=>PYTHONTEX#'):
            [inputtype, inputsession, inputgroup] = codeline.split('#', 4)[1:4]
            currentkey = inputtype + '#' + inputsession + '#' + inputgroup
            if inputsession.startswith('EXT:'):
			    # We use os.path.normcase to make sure slashes are 
                # appropriate, thus allowing code in subdirectories to be 
                # specified
                extfile = os.path.normcase(inputsession.replace('EXT:', ''))
                if not os.path.isfile(extfile):
                    print('* PythonTeX error')
                    print('    Cannot find external file ' + extfile)
                    sys.exit(1)
                # We read and hash the file in binary.  Opening in text mode 
                # would require an unnecessary decoding and encoding cycle.
                f = open(extfile, 'rb')
                hasher[currentkey].update(f.read())
                f.close()
            else:
				# We need to hash most of the code info, because code needs 
                # to be executed again if anything but the line number changes.
                # The text must be encoded to bytes for hashing.
                hasher[currentkey].update(codeline.rsplit('#', 2)[0].encode(encoding))
        else:
            # The text must be encoded to bytes for hashing
            hasher[currentkey].update(codeline.encode(encoding))
    # For PythonTeX (as opposed to Pygments) content, the hashes should also 
    # include the default code and custom code, in case these have changed.  
    # Based on the order in which the code will be executed, these should be 
    # hashed first.  But we don't know ahead of time what entries will be in 
    # the hashdict, so we hash them last.  The result is the same, since we 
    # get a unique hash.
    for key in hasher:
        inputtype = key.split('#', 1)[0]
        if not inputtype.startswith('PYG'):
            hasher[key].update(''.join(typedict[inputtype].default_code).encode(encoding))
            hasher[key].update(''.join(typedict[inputtype].custom_code).encode(encoding))
    # Create a dictionary of hashes, in string form
    hashdict = dict()
    for key in hasher:
        hashdict[key] = hasher[key].hexdigest()
    # Delete the hasher so it can't be accidentally used instead of hashdict
    del hasher
    # Save the hashdict into data.  It is tempting to think that the hashdict 
    # is now complete, but we must actually modify it again when code is 
    # executed.  If a (type, session, group) returns an error message, then 
    # we need to set its hash value to a null string so that it will be 
    # executed the next time PythonTeX runs (hopefully after the cause of 
    # the error has been resolved).
    data['hashdict'] = hashdict

    # See what needs to be updated.
    # In the process, copy over macros and files that may be reused.
    update_code = dict()
    macros = defaultdict(list)
    files = defaultdict(list)
    # If old data was loaded, and it contained sufficient information, and 
    # settings are compatible, determine what has changed so that only 
    # modified code may be executed.  Otherwise, execute everything.
    # We don't have to worry about checking for changes in pyfuture, because
    # custom code and default code are hashed.  The treatment of keeptemps
    # could be made more efficient (if changed to 'none', just delete old temp
    # files rather than running everything again), but given that it is 
    # intended as a debugging aid, that probable isn't worth it.  We don't 
    # have to check for the stderr option or stderrfilename, because any 
    # session that produces an error automatically runs every time.  
    if (loaded_old_data and
            'version' in old_data and
            data['version'] == old_data['version'] and
            data['encoding'] == old_data['encoding'] and
            data['workingdir'] == old_data['workingdir'] and
            data['keeptemps'] == old_data['keeptemps']):
        old_hashdict = old_data['hashdict']
        old_macros = old_data['macros']
        old_files = old_data['files']
        # Compare the hash values, and set which code needs to be run
        for key in hashdict:
            if key in old_hashdict and hashdict[key] == old_hashdict[key]:
                update_code[key] = False
                if key in old_macros:
                    macros[key] = old_macros[key]
                if key in old_files:
                    files[key] = old_files[key]
            else:
                update_code[key] = True        
    else:        
        for key in hashdict:
            update_code[key] = True
    # Save to data
    temp_data['update_code'] = update_code
    data['macros'] = macros
    data['files'] = files
    
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
    pygments_settings = data['pygments_settings']
    globalpyglexer = pygments_settings['#GLOBAL']['lexer']
    globalpygstyle = pygments_settings['#GLOBAL']['style']
    globalpygtexcomments = pygments_settings['#GLOBAL']['texcomments']
    globalpygmathescape = pygments_settings['#GLOBAL']['mathescape']
    for key in hashdict:
        inputtype = key.split('#', 1)[0]
        if inputtype.startswith('PYG') and inputtype not in pygments_settings:
            if globalpyglexer is not None:
                lexer = globalpyglexer
            else:
                lexer = inputtype.replace('PYG', '', 1)
            pygstyle = 'default'
            pygtexcomments = False
            pygmathescape = False
            if globalpygstyle is not None:
                pygstyle = globalpygstyle
            if globalpygtexcomments is not None:
                pygtexcomments = globalpygtexcomments
            if globalpygmathescape is not None:
                pygmathescape = globalpygmathescape
            pygments_settings[inputtype] = {'lexer': lexer,
                                            'style': pygstyle, 
                                            'texcomments': pygtexcomments,
                                            'mathescape': pygmathescape,
                                            'commandprefix': 'PYG' + pygstyle}
    # Add settings for console, based on type, if these settings haven't 
    # already been created by passing explicit console settings from the TeX 
    # side.
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
            # settings have changed.  All of this should possibly be done
            # elsewhere; there may be a more logical location.
            if loaded_old_data:
                old_pygments_settings = old_data['pygments_settings']                
                if ((inputtypecons in old_pygments_settings and 
                        inputtypecons not in pygments_settings) or
                        data['pyconbanner'] != old_data['pyconbanner'] or
                        data['pyconfilename'] != old_data['pyconfilename']):
                    update_code[key] = True
    # The global Pygments settings are no longer needed, so we delete them.
    # They are always present to be deleted, even if Pygments isn't used, 
    # because they are automatically created on the TeX side.
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
    fvextfile = data['fvextfile']
    if (loaded_old_data and 
            data['version'] == old_data['version'] and
            data['encoding'] == old_data['encoding']):
        old_hashdict = old_data['hashdict']   
        old_pygments_settings = old_data['pygments_settings']
        old_pygments_macros = old_data['pygments_macros']
        old_pygments_files = old_data['pygments_files']
        old_fvextfile = old_data['fvextfile']
        old_pygments_style_defs = old_data['pygments_style_defs']
        for key in hashdict:
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
    if loaded_old_data:
        # Clean up for code that will be run again, and for code that no 
        # longer exists.  We use os.path.normcase() to fix slashes in the path
        # name, in an attempt to make saved paths platform-independent.
        old_hashdict = old_data['hashdict']
        old_files = old_data['files']
        old_pygments_files = old_data['pygments_files']
        for key in hashdict:
            if update_code[key]:
                if key in old_files:
                    for f in old_files[key]:
                        f = os.path.normcase(f)
                        if os.path.isfile(f):
                            os.remove(f)
                if key in old_pygments_files:
                    for f in old_pygments_files[key]:
                        f = os.path.normcase(f)
                        if os.path.isfile(f):
                            os.remove(f)
            elif update_pygments[key] and key in old_pygments_files:
                for f in old_pygments_files[key]:
                    f = os.path.normcase(f)
                    if os.path.isfile(f):
                        os.remove(f)
        for key in old_hashdict:
            if key not in hashdict:
                for f in old_files[key]:
                    f = os.path.normcase(f)
                    if os.path.isfile(f):
                        os.remove(f)
                for f in old_pygments_files[key]:
                    f = os.path.normcase(f)
                    if os.path.isfile(f):
                        os.remove(f)





def parse_code_write_scripts(data, temp_data, typedict):
    '''
    Parse the code file into separate scripts, based on 
    (type, session, groups).  Write the script files.
    '''
    codedict = defaultdict(list)
    consoledict = defaultdict(list)
    # Create variables to ease data access
    hashdict = data['hashdict']
    outputdir = data['outputdir']
    workingdir = data['workingdir']
    encoding = data['encoding']
    pytxcode = temp_data['pytxcode']
    update_code = temp_data['update_code']
    update_pygments = temp_data['update_pygments']
    files = data['files']
    # We need to keep track of the last instance for each session, so 
    # that duplicates can be eliminated.  Some LaTeX environments process 
    # their contents multiple times and thus will create duplicates.  We 
    # initialize to -1, since instances begin at zero.
    lastinstance = dict()
    for key in hashdict:
        lastinstance[key] = -1
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
                elif update_code[currentkey]:
                    switched = True
                    addcode = True
                    if inputcommand == 'inline':
                        inline = True
                    else:
                        inline = False
                        # Correct for line numbering in environments; content 
                        # doesn't really start till the line after the "\begin"
                        inputline = str(int(inputline)+1)
        #Only collect for a session (and later write it to a file) if it needs to be updated
        elif addconsole:
            consoledict[currentkey].append(codeline)
        elif addcode:
            # If just switched commands/environments, associate with the input 
            # line and check for indentation errors
            if switched:
                switched = False
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

    # Save the code sessions that need to be updated
    # Keep track of the files that are created
    for key in codedict:
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
        for code in typedict[inputtype].default_code:
            if '__future__' in code:
                sessionfile.write(code)
                sessionfile.write('\n')
        for code in typedict[inputtype].custom_code:
            if '__future__' in code:
                sessionfile.write(code)
                sessionfile.write('\n')
        # Check for __future__ in the actual code.  We only check the first 
        # four content-containing lines.  Note that line 0 of codedict[key]
        # sets PythonTeX variables.
        counter = 0
        in_docstring = False
        for (n, line) in enumerate(codedict[key]):
            # Detect __future__ imports
            if '__future__' in line:
                sessionfile.write(line)
                codedict[key][n] = ''
            # Ignore comments, empty lines, and lines with complete docstrings
            elif (line.startswith('#') or 
                    line.isspace() or
                    line.count('"""')%2 == 0 or 
                    line.count("'''")%2 == 0):
                pass
            # Detect if entering or leaving a docstring
            elif line.count('"""')%2 == 1 or line.count("'''")%2 == 1:
                in_docstring = not in_docstring
            # Stop looking for future imports as soon as a non-comment, 
            # non-empty, non-docstring, non-future import line is found
            elif not in_docstring:
                counter += 1
            if counter > 4:
                break
        # Write the remainder of the default code
        for code in typedict[inputtype].default_code:
            if '__future__' not in code:
                sessionfile.write(code)
                sessionfile.write('\n')
        sessionfile.write(typedict[inputtype].set_stdout_encoding(encoding))
        sessionfile.write('\n'.join(typedict[inputtype].utils_code))
        sessionfile.write('\n')
        # Write all custom code not involving __future__
        for code in typedict[inputtype].custom_code:
            if '__future__' not in code:
                sessionfile.write(code)
                sessionfile.write('\n')
        sessionfile.write(typedict[inputtype].open_macrofile(outputdir,
                inputtype + '_' + inputsession + '_' + inputgroup, encoding))
        sessionfile.write(typedict[inputtype].set_workingdir(workingdir))
        sessionfile.write(typedict[inputtype].set_inputs_const(inputtype, inputsession, inputgroup))
        sessionfile.write('\n')            
        sessionfile.write(''.join(codedict[key]))
        sessionfile.write('\n\n\n\n')
        sessionfile.write(typedict[inputtype].close_macrofile())
        sessionfile.close()




def do_multiprocessing(data, temp_data, old_data, typedict):
    outputdir = data['outputdir']
    jobname = data['jobname']
    fvextfile = data['fvextfile']
    hashdict = data['hashdict']
    encoding = data['encoding']
    update_code = temp_data['update_code']
    update_pygments = temp_data['update_pygments']
    pygments_settings = data['pygments_settings']
    update_pygments = temp_data['update_pygments']
    codedict = temp_data['codedict']
    consoledict = temp_data['consoledict']
    pytxcode = temp_data['pytxcode']
    keeptemps = data['keeptemps']
    files = data['files']
    macros = data['macros']
    pygments_files = data['pygments_files']
    pygments_macros = data['pygments_macros']
    pygments_style_defs = data['pygments_style_defs']
    errors = temp_data['errors']
    warnings = temp_data['warnings']
    stderr = data['stderr']
    stderrfilename = data['stderrfilename']
    # Set maximum number of concurrent processes for multiprocessing
    # Accoding to the docs, cpu_count() may raise an error
    try:
        max_processes = multiprocessing.cpu_count()
    except NotImplementedError:
        max_processes = 1
    pool = multiprocessing.Pool(max_processes)
    tasks = []
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
                                                        data['pyconbanner'],
                                                        data['pyconfilename'],
                                                        encoding]))
            break
    
    # Add code processes.  Note that everything placed in the codedict 
    # needs to be executed, based on previous testing.
    for key in codedict:
        [inputtype, inputsession, inputgroup] = key.split('#')
        print('* Pythontex executing', inputtype, inputsession, inputgroup)
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
                                                 encoding]))
    
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
        for key in result['files']:
            files[key].extend(result['files'][key])
        for key in result['macros']:
            macros[key].extend(result['macros'][key])
        for key in result['pygments_files']:
            pygments_files[key].extend(result['pygments_files'][key])
        for key in result['pygments_macros']:
            pygments_macros[key].extend(result['pygments_macros'][key])
        errors += result['errors']
        warnings += result['warnings']
        messages.extend(result['messages'])
        hashdict.update(result['exit_status'])
    
    # Save all content
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
    # We store the error and warning counts, so that they can be printed at
    # the very end of the program, in case anything must ever be done after 
    # this point.
    temp_data['errors'] = errors
    temp_data['warnings'] = warnings




def run_code(inputtype, inputsession, inputgroup, outputdir, command, 
             command_options, extension, stderr, stderrfilename, keeptemps,
             encoding):
    '''
    Function for multiprocessing code files
    '''
    # Create what's needed for storing results
    currentkey = inputtype + '#' + inputsession + '#' + inputgroup
    files = []
    macros = []
    pygments_files = []
    pygments_macros = []
    errors = 0
    warnings = 0
    messages = []
    exit_status = dict()
    
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
    f = open(os.path.join(outputdir, basename + '.out'), 'r', encoding=encoding)
    outfile = f.readlines()
    f.close()
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
        fname = os.path.join(outputdir, basename + '_' + inputinstance + '.stdout')
        files.append(fname)
        f = open(fname, 'w', encoding=encoding)
        f.write(''.join(printfile))
        f.close()
    
    # Load the macros
    macrofile = os.path.join(outputdir, basename + '.pytxmcr')
    if os.path.isfile(macrofile):
        f = open(macrofile, 'r', encoding=encoding)
        macros = f.readlines()
        f.close()

    # Process error messages
    err_file_name = os.path.join(outputdir, basename + '.err')
    code_file_name = os.path.join(outputdir, basename + '.' + typedict[inputtype].extension)
    # Only work with files that have a nonzero size 
    if os.path.isfile(err_file_name) and os.stat(err_file_name).st_size != 0:
        # Reset the hash value, so that the code will be run next time
        exit_status[currentkey] = ''
        # Open error and code files.
        # We can't just use the code in memory, because the full script 
        # file was written but never fully assembled in memory.
        f = open(err_file_name, encoding=encoding)
        err_file = f.readlines()
        f.close()
        f = open(code_file_name, encoding=encoding)
        code_file = f.readlines()
        f.close()
        # We need to let the user know we are switching code files
        messages.append('\n---- Errors for ' + basename + ' ----')
        for errline in err_file:
            if basename in errline and search('line \d+', errline):
                errors += 1
                # Offset by one for zero indexing, one for previous line
                errlinenumber = int(search('line (\d+)', errline).groups()[0]) - 2
                offset = -1
                while errlinenumber >= 0 and not code_file[errlinenumber].startswith('pytex.inputline = '):
                    errlinenumber -= 1
                    offset += 1
                if errlinenumber >= 0:
                    codelinenumber = int(match('pytex\.inputline = \'(\d+)\'', code_file[errlinenumber]).groups()[0])
                    codelinenumber += offset
                    messages.append('* PythonTeX code error on line ' + str(codelinenumber) + ':')
                else:
                    messages.append('* PythonTeX code error.  Error line cannot be determined.')
                    messages.append('* Error is likely due to system and/or PythonTeX-generated code.')
            messages.append('  ' + errline.rstrip('\r\n'))
        # Take care of saving .stderr, if needed
        if stderr:
            # Need to keep track of whether successfully set name and line number
            found = False
            # Loop through the error file
            for (n, errline) in enumerate(err_file):
                # When the basename is found with a line number, determine
                # the inputinstance and the fixed line number.  The fixed 
                # line number is the line number counted based on 
                # non-inline user-generated code, not counting anything 
                # that is automatically generated or any custom_code that
                # is not typeset.  If it isn't in a code or block 
                # environment, where it could have line numbers, it 
                # doesn't count.
                if basename in errline and search('line \d+', errline):
                    found = True
                    # Get the inputinstance
                    errlinenumber = int(search('line (\d+)', errline).groups()[0]) - 2
                    while errlinenumber >= 0 and not code_file[errlinenumber].startswith('pytex.inputinstance = '):
                        errlinenumber -= 1
                    if errlinenumber >= 0:
                        inputinstance = match('pytex\.inputinstance = \'(\d+)\'', code_file[errlinenumber]).groups()[0]
                    else:
                        messages.append('* PythonTeX warning')
                        messages.append('    Could not parse stderr into a .stderr file')
                        messages.append('    The offending file was ' + err_file_name)
                        warnings += 1
                    # Get the fixed line number
                    should_count = False
                    fixedline = 2
                    # Need to stop counting when we reach the "real" line
                    # number of the error.  Need -1 to offset for zero 
                    # indexing.  All of this depends on the precise 
                    # spacing in the automatically generated scripts.
                    breaklinenumber = int(search('line (\d+)', errline).groups()[0]) - 1
                    for (m, line) in enumerate(code_file):
                        if line.startswith('pytex.inputinstance = '):
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
                        err_file[n] = errline.replace(fullbasename, basename)
                    elif stderrfilename == 'session':
                        err_file[n] = errline.replace(fullbasename, inputsession)
                    elif stderrfilename == 'genericfile':
                        err_file[n] = errline.replace(fullbasename + '.' + typedict[inputtype].extension, '<file>')
                    elif stderrfilename == 'genericscript':
                        err_file[n] = errline.replace(fullbasename + '.' + typedict[inputtype].extension, '<script>')
                    err_file[n] = sub('line \d+', 'line ' + str(fixedline), err_file[n])
            if found:
                stderr_file_name = os.path.join(outputdir, basename + '_' + inputinstance + '.stderr')
                f = open(stderr_file_name, 'w', encoding=encoding)
                f.write(''.join(err_file))
                f.close()
                files.append(stderr_file_name)
            else:
                messages.append('* PythonTeX warning')
                messages.append('    Could not parse stderr into a .stderr file')
                messages.append('    The offending file was ' + err_file_name)
                messages.append('    Remember that .stderr files are only possible for block and code environments')
                warnings += 1

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
    
    # Return a dict of dicts of results
    return {'files': {currentkey: files},
            'macros': {currentkey: macros},
            'pygments_files': {currentkey: pygments_files},
            'pygments_macros': {currentkey: pygments_macros},
            'errors': errors,
            'warnings': warnings,
            'messages': messages,
            'exit_status': exit_status}    




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
    files = defaultdict(list)
    macros = defaultdict(list)
    pygments_files = defaultdict(list)
    pygments_macros = defaultdict(list)
    errors = 0
    warnings = 0
    messages = []
    exit_status = dict()
    
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
    lastinstance = dict()
    for key in update_pygments:
        lastinstance[key] = -1
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
            if (update_pygments[currentkey] and (inputgroup.endswith('verb') or 
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
    return {'files': files,
            'macros': macros,
            'pygments_files': pygments_files,
            'pygments_macros': pygments_macros,
            'errors': errors,
            'warnings': warnings,
            'messages': messages,
            'exit_status': exit_status} 




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
    errors = 0
    warnings = 0
    messages = []
    exit_status = dict()
    
    # Lazy import what's needed
    import code
    from collections import deque
    #// Python 2
    # Can't use io for everything, because it requires Unicode
    # The current system doesn't allow for Unicode under Python 2
    try:
        from cStringIO import StringIO
    except ImportError:
        from StringIO import StringIO
    #\\ End Python 2
    #// Python 3
    #from io import StringIO
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
        try:
            ''.join(consoledict[key]).encode('ascii')
        except (UnicodeEncodeError, UnicodeDecodeError):
            exit_status[key] = ''
            inputline = consoledict[key][0].rsplit('#', 2)[1]
            messages.append('* PythonTeX error')
            messages.append('    Non-ascii character(s) near line ' + inputline)
            messages.append('    Non-ascii characters are not allowed in console environments under Python 2')
            errors += 1
            continue
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
                            fname = os.path.join(outputdir, inputtype + '_' + inputsession + '_' + inputgroup + '_' + inputinstance + '.pygtex')
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
    return {'files': files,
            'macros': macros,
            'pygments_files': pygments_files,
            'pygments_macros': pygments_macros,
            'errors': errors,
            'warnings': warnings,
            'messages': messages,
            'exit_status': exit_status} 




def save_data(data):
    '''
    Save data for the next run
    '''
    pythontex_data_file = os.path.join(data['outputdir'], 'pythontex_data.pkl')
    f = open(pythontex_data_file, 'wb')
    pickle.dump(data, f, -1)
    f.close()




# The "if" statement is needed for multiprocessing under Windows; see the 
# multiprocessing documentation.
if __name__ == '__main__':
    # Print PythonTeX version.  Flush to make the message go out immediately,  
    # so that the user knows PythonTeX has started.
    print('This is PythonTeX v' + version)
    sys.stdout.flush()

    # Create dictionaries for storing data.
    #
    # All data that must be saved for subsequent runs is stored in "data".
    # (We start off by saving the script version in this dict.)
    # All data that is only created for this run is stored in "temp_data".
    # (We start off by creating keys for keeping track of errors and warnings.)
    # All old data will eventually be loaded into "old_data".
    # Since dicts are mutable data types, the global dicts can be modified
    # from within functions, as long as the dicts are passed to the functions.
    # For simplicity, variables will often be created within functions to
    # refer to dictionary values.
    data = {'version': version}
    temp_data = {'errors': 0, 'warnings': 0}
    old_data = dict()    
    
    
    # Process command-line options.
    #
    # This gets the raw_jobname (actual job name), jobname (a sanitized job 
    # name, used for creating files named after the jobname), and the 
    # encoding to be used for all files.
    process_argv(data, temp_data)
    # Once we have the encoding, we set stdout and stderr to use this 
    # encoding.  Later, we will parse the saved stderr of scripts executed 
    # via multiprocessing subprocesses, and print the parsed results to 
    # stdout.  The saved stderr uses the same encoding that was used 
    # for the files that created it (this is important for code containing 
    # unicode characters), so we also need stdout for the main PythonTeX
    # script to support this encoding.  Setting stderr encoding is primarily 
    # a matter of symmetry.  Ideally, pythontex*.py will be bug-free,
    # and stderr won't be needed!
    #// Python 2
    sys.stdout = codecs.getwriter(data['encoding'])(sys.stdout, 'strict')
    sys.stderr = codecs.getwriter(data['encoding'])(sys.stderr, 'strict')
    #\\ End Python 2
    #// Python 3
    #sys.stdout = codecs.getwriter(data['encoding'])(sys.stdout.buffer, 'strict')
    #sys.stderr = codecs.getwriter(data['encoding'])(sys.stderr.buffer, 'strict')
    #\\ End Python 3


    # Load the code and process the settings it passes from the TeX side.
    #
    # This gets a list containing the code (the part of the code file 
    # containing the options is removed) and the processed settings.
    load_code_get_settings(data, temp_data)
    # Now that the settings are loaded, check if outputdir exits.
    # If not, create it.
    if not os.path.isdir(data['outputdir']):
        os.mkdir(data['outputdir'])


    # Load/create old_data
    get_old_data(data, old_data)
    
    
    # Hash the code.  Determine what needs to be executed.  Determine whether
    # Pygments should be used.  Update pygments_settings to account for 
    # Pygments commands and environments (as opposed to PythonTeX commands and 
    # environments).
    hash_code(data, temp_data, old_data, typedict)
    
    
    # Parse the code.
    parse_code_write_scripts(data, temp_data, typedict)
    
    
    # Execute the code and perform Pygments highlighting via multiprocessing.
    do_multiprocessing(data, temp_data, old_data, typedict)


    # Save data for the next run
    save_data(data)
    
    
    # Print exit message
    print('\n--------------------------------------------------')
    print('PythonTeX:  ' + data['raw_jobname'] + ' - ' + str(temp_data['errors']) + ' error(s), ' + str(temp_data['warnings']) + ' warning(s)')

    return temp_data['errors']
