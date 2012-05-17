#!/usr/bin/env python

# This is the main PythonTeX script.
#
# It, and the other PythonTeX scripts, are specifically written to run 
# correctly under Python 2.6 and 2.7 as well as under Python 3.x, without 
# modification.  They will not run under older versions because, among other 
# things, multiprocessing is required.
#
# This script needs to be able to import pythontex_types.py; in general it 
# should be in the same directory.  This  script creates scripts that need to 
# be able to import pythontex_types.py and pythontex_utils.py.  The location 
# of those two files is determined via the kpsewhich command, which is part of 
# the Kpathsea library included with some TeX distributions, including TeX Live
# and MiKTeX.
#
# Long-term, depending on what languages besides Python are supported, 
# alternatives to pythontex.py written in another language may be something to 
# consider.  Perl is commonly available and can use multiple processors, so 
# it would be a logical choice for an alternate implementation.  A C version 
# could probably increase speed a great deal, but since it would require 
# compilation and since the execution time of this script will in general only
# be a small fraction of the overall execution time, it probably isn't worth 
# it for most applications.  Lua apparently doesn't support true parallel 
# execution so as to stay light-weight, so it wouldn't be a good option for a 
# (fast) alternate implementation.
#
#
# Licensed under the BSD 3-Clause License:
# 
'''
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


#Imports
import sys
from re import match, sub, search
from os import path, mkdir, listdir, remove, stat
from collections import defaultdict
from subprocess import Popen, check_output, CalledProcessError
import multiprocessing
from hashlib import sha1
import cPickle as pickle
from pythontex_types import *


#Script parameters
#Version
pythontex_version='0.9beta'


#Function for multiprocessing code files
def run_code(inputtype,inputsession,inputgroup,outputdir):
    #Open files for stdout and stderr, run the code, then close the files
    basename=inputtype+'_'+inputsession+'_'+inputgroup
    outfile=open(path.join(outputdir,basename+'.out'),'w')
    errfile=open(path.join(outputdir,basename+'.err'),'w')
    exec_cmd=[typedict[inputtype].command, 
             path.join(outputdir, basename + '.' + typedict[inputtype].extension)]
    #Use .wait() so that code execution finishes before the next process is started
    Popen(exec_cmd, stdout=outfile, stderr=errfile).wait()
    outfile.close()
    errfile.close()
    #Process stdout into file(s) that are included into .tex
    outfile=open(path.join(outputdir,basename+'.out'),'r')
    outfile_lines=outfile.readlines()
    outfile.close()
    inputinstance=''
    printfile=[]
    #Go through the output line by line, and save any printed content to its own file, named based on instance.
    #This might be done more efficiently by redefining the print function or using StringIO within each individual code file.
    #While that could be a little more efficient, it would not generalize easily to other languages.
    #It would require that another language support redefinition of the print function (Perl doesn't) or have a StringIO equivalent.
    #Given that any speed increase would probably be negligible under most circumstances, it is probably better to go with the most general approach.
    #Any worthwhile language must be able to print to stdout.
    #An optional, Python-specific approach using StringIO or something similar should be reconsidered at a later date
    for line in outfile_lines:
        #If the line contains the text '=>PYTHONTEX#PRINT#', we are switching between instances; if so, we need to save any printed content from the last session and get the inputinstance for the current session
        if line.startswith('=>PYTHONTEX#PRINT#'):
            if len(printfile)>0:
                f=open(path.join(outputdir,basename+'_'+inputinstance+'.stdout'),'w')
                f.write(''.join(printfile))
                f.close()
            printfile=[]
            inputinstance=line.split('#')[2]
        else:
            printfile.append(line)
    #After the last line of output is processed, there may be content in the printfile list that has not yet been saved, so we take care of that
    if len(printfile)>0:
        f=open(path.join(outputdir,basename+'_'+inputinstance+'.stdout'),'w')
        f.write(''.join(printfile))
        f.close()


#Function for creating Pygments content.  To be run during multiprocessing.
#Eventually, it might be nice to add something that inserts line breaks to keep typeset code from overflowing the margins.
#That could require a goob bit of info about page layout from the LaTeX side and it might get tricky to do good line breaking, but it should be kept in mind.
def do_pygments(outputdir, jobname, saveverbatim_threshold, oldsaveverbatim_threshold, pygments_settings, oldpygments_settings, updateresults, codefile, codefile_param_offset):
    #Try to import what's needed; otherwise, return an error
    try:
        from pygments import highlight
        from pygments.lexers import get_lexer_by_name
        from pygments.formatters import LatexFormatter
    except ImportError:
        print('\n* PythonTeX Error')
        print('    Could not import Pygments!')
        sys.exit(1)
    #Create a defaultdict of lists in which to store all pygmentized content until it is written to file
    #Pygmentized content is stored in this way so that it may be pickled and thus unchanged code (type, session, group) need not be highlighted again
    pygmentized=defaultdict(list)
    #Load pickled pygmentized content
    if path.isfile(path.join(outputdir,'pygments_database.pkl')):
        f=open(path.join(outputdir,'pygments_database.pkl'),'rb')
        oldpygmentized=pickle.load(f)
        f.close()
    else:
        oldpygmentized=defaultdict(list)
    #Create formatter_dicts and lexer_dicts, and at the same time create style macros for LaTeX
    #Note that we must be careful to create each set of style macros only once
    style_dict=defaultdict(int)
    formatter_dict=defaultdict(LatexFormatter)
    lexer_dict=defaultdict(get_lexer_by_name)
    #Note that in a later version we should make sure non-ascii characters work for XeTeX etc. (Latexformatter_dict takes an encoding option)
    for codetype in pygments_settings:
        (lexer,pygstyle,pygtexcomments,pygmathescape)=pygments_settings[codetype]
        formatter_dict[codetype]=LatexFormatter(style=pygstyle, texcomments=pygtexcomments,
                mathescape=pygmathescape, commandprefix='PYG'+pygstyle)
        lexer_dict[codetype]=get_lexer_by_name(lexer, stripall=True)
        if pygstyle not in style_dict:
            style_dict[pygstyle]=1
            #Create a key for storing styles that won't conflict with intputtype#inputsession#inputgroup
            currentkey='pygstyle#'+pygstyle
            #Reuse styles if they were already created, otherwise create them
            if currentkey in oldpygmentized:
                pygmentized[currentkey]=oldpygmentized[currentkey]
            else:
                pygmentized[currentkey]=formatter_dict[codetype].get_style_defs()
    #Copy any old highlighted code that is to be reused
    #Code can only be reused if it doesn't need to be updated, was previously used with Pygments, and has the same Pygments settings as the last use
    #Also, code can only be reused only so long as the threshold for using external files remains unchanged
    for key in updateresults:
        inputtype=key.split('#',1)[0]
        if updateresults[key]==False and inputtype in oldpygments_settings \
                and pygments_settings[inputtype]==oldpygments_settings[inputtype] \
                and saveverbatim_threshold==oldsaveverbatim_threshold:
            pygmentized[key]=oldpygmentized[key]
    #Actually parse and highlight the code
    #We need to initialize an empty list for storing code and a defaultdict to keep track of instances, so that repeated instances can be skipped
    code=[]
    lastinstance=defaultdict(int)
    for key in updateresults:
        lastinstance[key]=-1
    #We also need a quick-lookup dictionary for determining what to process
    #We only want to evaluate all this once, not every time we switch commands/environments
    should_pygmentize=defaultdict(bool)
    for key in updateresults:
        [inputtype,inputsession,inputgroup]=key.split('#')
        #We should only highlight code that the user has designated to be processed by Pygments
        if inputtype not in pygments_settings:
            should_pygmentize[key]=False
        #We need to highlight code if it has changed
        #Or if it is unchanged but its Pygments settings have changed
        elif updateresults[key]==False and inputtype in oldpygments_settings \
                    and pygments_settings[inputtype]==oldpygments_settings[inputtype] \
                    and saveverbatim_threshold==oldsaveverbatim_threshold:
            should_pygmentize[key]=False
        else:
            should_pygmentize[key]=True
    for codeline in codefile[codefile_param_offset:-1]:
        #Detect if start of new command/environment
        #If so, save any code from the last (type,session,group,instance), and detemine how to proceed
        if codeline.startswith('=>PYTHONTEX#'):
            #Process any code from the last (type,session,group,instance)
            #Either save it to pygmentized or an external file, depending on size
            #Note that we don't have to worry about cleaning up any external files that are no longer used, since the main script takes care of that via basename checking
            if len(code)>0:
                processed=highlight(''.join(code), lexer_dict[inputtype], formatter_dict[inputtype])
                if len(code)<saveverbatim_threshold:
                    processed=sub(r'\\begin{Verbatim}\[(.+)\]', r'\\begin{{SaveVerbatim}}[\1]{{pytx@{0}@{1}@{2}@{3}}}'.format(inputtype,inputsession,inputgroup,inputinstance), processed, count=1).rsplit('\\',1)[0]
                    processed=processed+'\\end{SaveVerbatim}\n\n'
                    pygmentized[currentkey].append(processed)
                else:
                    if inputsession.startswith('EXT:'):
                        f=open(path.join(outputdir,inputsession.replace('EXT:','')+'_'+inputtype.replace('PYG','',1)+'.pygtex'),'w')
                    else:
                        f=open(path.join(outputdir,inputtype+'_'+inputsession+'_'+inputgroup+'_'+inputinstance+'.pygtex'),'w')
                    f.write(processed)
                    f.write('\\endinput\n')
                    f.close()
                code=[]
            #Now proceed to extract paramets and prepare for the next code
            [inputtype,inputsession,inputgroup,inputinstance,inputcmd,inputstyle,inputline]=codeline.split('#')[1:8]
            currentkey=inputtype+'#'+inputsession+'#'+inputgroup
            currentinstance=int(inputinstance)
            proceed=True
            #We have to check for environments that are read multiple times (and thus written to .pytxcode multiple times) by LaTeX
            #We need to ignore any environments and commands that do NOT need their code typeset
            if lastinstance[currentkey]<currentinstance:
                lastinstance[currentkey]=currentinstance
                if should_pygmentize[currentkey]==False or inputcmd=='code' or inputcmd=='inline' or inputcmd=='inlinec':
                    proceed=False
                elif inputsession.startswith('EXT:'):
                    extfile=path.normcase(inputsession.replace('EXT:',''))
                    f=open(extfile)
                    code=f.readlines()
                    f.close()
            else:
                proceed=False
        #Only collect for a session (and later write it to a file) if it needs to be updated
        elif proceed:
            code.append(codeline)
    #We need to take care of any code remaining
    if len(code)>0:
        processed=highlight(''.join(code), lexer_dict[inputtype], formatter_dict[inputtype])
        code=[]
        if len(code)<saveverbatim_threshold:
            if inputsession.startswith('EXT:'):
                processed=sub(r'\\begin{Verbatim}\[(.+)\]', r'\\begin{SaveVerbatim}[\1]{pytx@'+extfile+r'}', processed, count=1).replace(r'\end{Verbatim}', r'\end{SaveVerbatim}')
            else:
                processed=sub(r'\\begin{Verbatim}\[(.+)\]', r'\\begin{SaveVerbatim}[\1]{pytx@'+inputtype+'@'+inputsession+'@'+inputgroup+'@'+inputinstance+r'}', processed, count=1).replace(r'\end{Verbatim}', r'\end{SaveVerbatim}')
            pygmentized[currentkey].append(processed)
        else:
            f=open(path.join(outputdir,inputtype+'_'+inputsession+'_'+inputgroup+'_'+inputinstance+'.pygtex'))
            f.write(processed)
            f.write(r'\endinput')
            f.close()
    #Save highlighted results
    f=open(path.join(outputdir,'pygments_database.pkl'),'wb')
    pickle.dump(pygmentized,f,-1)
    f.close()
    #Open a file for Pygments content, write content, then close
    f=open(path.join(outputdir,jobname+'.pytxpyg'),'w')
    #The style info must be written first, so that the macros exist for SaveVerbatim
    #The way in which the following is done could probably be optimized, perhaps by storing style separately
    for key in pygmentized:
        if key.startswith('pygstyle#'):
            f.write(''.join(pygmentized[key]))
            f.write('\n')
    for key in pygmentized:
        if not key.startswith('pygstyle#'):
            f.write(''.join(pygmentized[key]))
            f.write('\n')
    f.close()


#Main
#The "if" statement is needed for multiprocessing under Windows; see the multiprocessing documentation
if __name__=='__main__':
    #Take care of a few multiprocessing chores
    #Add support for freezing into Windows executable.  This needs to be immediately after the beginning of __main__
    multiprocessing.freeze_support()
    #Set maximum number of concurrent processes for multiprocessing
    try:
        max_processes=multiprocessing.cpu_count()
    except NotImplementedError:
        max_processes=1

    #Print PythonTeX version, to let the user know that PythonTeX has started
    #Flush to make the message go out immediately, so that the user knows PythonTeX has started
    print('This is PythonTeX v'+pythontex_version)
    sys.stdout.flush()
    
    #Process command-line options
	#Currently, we are only getting the job name, but eventually we may want additional options, unless all options continue to be passed through from the TeX side
    #We do a little basic error checking during processing
    if len(sys.argv)!=2:
        print('* PythonTeX error\n    Incorrect number of command line arguments passed to pythontex.py.')
        sys.exit(2)
    else:
        jobnameraw=sys.argv[1]
        #We need to strip off the .tex extension if it was passed, since we need the TeX \jobname
        if jobnameraw.endswith('.tex'):
            jobnameraw=jobnameraw.rsplit('.',1)[0]
        #We need to see if the tex file exists.  If not, we issue a warning, but attempt to continue since it's possible a file with another extension is being compiled.
        if not path.exists(jobnameraw+'.tex'):
            print('* PythonTeX warning\n    Job name does not seem to correspond to a .tex document.\n    Attempting to proceed.')
        #We need a "sanitized" version of the jobname, with spaces and asterisks replaced with hyphens
        #This is done to avoid TeX issues with spaces in file names, paralleling the approach taken in pythontex.sty
        #From now on, we will use the sanitized version every time we create a file that contains the jobname string
        #The raw version will only be used in reference to pre-existing files created on the TeX side, such as the .pytxcode file
        jobname=jobnameraw.replace(' ','-').replace('\"','').replace('*','-')
        #We need to check to make sure that the "sanitized" jobname doesn't lead to a collision with a file that already has that name, so that two files attempt to use the same PythonTeX folder
        if jobname!=jobnameraw:
            if path.exists(jobname+'.tex') and path.exists(jobnameraw+'.tex'):
                print('* PythonTeX error\n    Directory naming collision between the following files:')
                print('      \"'+jobnameraw+'.tex\"\n      \"'+jobname+'.tex\"')
                sys.exit(1)
            else:
                ls=listdir('.')
                collision=False
                for file in ls:
                    if file.startswith(jobname):
                        collision=True
                        break
                if collision:
                    print('* PythonTeX warning\n    Potential directory naming collision between the following files:')
                    print('      \"'+jobnameraw+'.*\"\n      \"'+jobname+'.*\"\n    Attempting to proceed.')

    #Bring in the .pytxcode file as a list
    if path.exists(jobnameraw+'.pytxcode'):
        f=open(jobnameraw+'.pytxcode','r')
        codefile=f.readlines()
        f.close()
    else:
        print('* PythonTeX error\n    Code file '+jobnameraw+'.pytxcode does not exist.  Run LaTeX to create it.')
        sys.exit(1)

    #Process options passed via the code file, from the TeX side.
    #Extract settings for Pygments, determine the output directory, and set the treatment of temp files.
    #Determine if some Pygments content should be saved using external files rather than SaveVerbatim.
    #While processing options, figure out how many lines of the code file are devoted to options, so that these can be skipped later.
    codefile_param_offset=0  #Keep track of number of param lines, so can skip later
    pygments_settings=defaultdict(tuple)
    saveverbatim_threshold=sys.maxsize
    for line in codefile:
        if line.startswith('=>PYTHONTEX#PARAMS#'):
            codefile_param_offset+=1
            content=line.split('#')[2]
            if content.startswith('keeptemps='):
                keeptemps=content.split('=')[1]
            elif content.startswith('outputdir='):
                outputdir=content.split('=')[1]
            elif content.startswith('pygments='):
                usepygments=content.split('=')[1]
            elif content.startswith('pygmentsoptions:'):
                options=content.split(':',1)[1].strip('{}').replace(' ','').split(',')
                globalpygstyle=''
                globalpygtexcomments=''
                globalpygmathescape=''
                for option in options:
                    if option.startswith('style='):
                        globalpygstyle=option.split('=')[1]
                    if option == 'texcomments':
                        globalpygtexcomments=True
                    if option.startswith('texcomments='):
                        option=option.split('=')[1]
                        if option=='true' or option=='True':
                            globalpygtexcomments=True
                    if option == 'mathescape':
                        globalpygmathescape=True
                    if option.startswith('mathescape='):
                        option=option.split('=')[1]
                        if option=='true' or option=='True':
                            globalpygmathescape=True
            elif content.startswith('pygmentsfamily:'):
                [inputtype,lexer,options]=content.split(':',1)[1].replace(' ','').split(',',2)
                options=options.strip('{}').split(',')
                pygstyle='default'
                pygtexcomments=False
                pygmathescape=False
                for option in options:
                    if option.startswith('style='):
                        pygstyle=option.split('=')[1]
                    if option == 'texcomments':
                        pygtexcomments=True
                    if option.startswith('texcomments='):
                        option=option.split('=')[1]
                        if option=='true' or option=='True':
                            pygtexcomments=True
                    if option == 'mathescape':
                        pygmathescape=True
                    if option.startswith('mathescape='):
                        option=option.split('=')[1]
                        if option=='true' or option=='True':
                            pygmathescape=True
                if globalpygstyle != '':
                    pygstyle=globalpygstyle
                if globalpygtexcomments != '':
                    pygtexcomments=globalpygtexcomments
                if globalpygmathescape != '':
                    pygmathescape=globalpygmathescape
                pygments_settings[inputtype]=(lexer,pygstyle,pygtexcomments,pygmathescape)
            elif content.startswith('pygextfile='):
                try:
                    saveverbatim_threshold=int(content.split('=')[1])
                    if saveverbatim_threshold<0:
                        saveverbatim_threshold=1
                except ValueError:
                    print('* PythonTeX error\n    Unable to parse package option pygextfile.')
                    sys.exit(1)
        else:
            break
    #Check if pythontex-files directory exists, create it if not
    if not path.exists(outputdir):
        mkdir(outputdir)
    
    #Figure out where the PythonTeX scripts are located, so that we can tell other scripts how to import them
    #Note that we do a lot of testing to make sure that we have indeed found the scripts, and to make sure that the scripts path is still valid from previous runs
    #This depends on having a TeX installation that includes kpsewhich (TeX Live and MiKTeX, possibly others)
    #Also load saved Pygments settings from the last run
    pythontex_info={}
    pythontex_info_file=path.join(outputdir,'pythontex_info.pkl')
    if path.exists(pythontex_info_file):
        f=open(pythontex_info_file,'rb')
        pythontex_info=pickle.load(f)
        f.close()
        oldpygments_settings=pythontex_info['pygments_settings']
        oldsaveverbatim_threshold=pythontex_info['saveverbatim_threshold']
        #We need to make sure the path to pythontex_utils.py is still valid
        if not path.exists(path.join(pythontex_info['script_path'],'pythontex_utils.py')):
            exec_cmd=['kpsewhich', '-format', 'texmfscripts', 'pythontex_utils.py']
            try:
                script_path=check_output(exec_cmd).rstrip('\r\n')
            except OSError:
                print('Your system appears to lack kpsewhich.  Exiting.')
                sys.exit(1)
            except CalledProcessError:
                print('kpsewhich is not happy with its arguments.')
                print('This command was attempted:')
                print('    ' + ' '.join(exec_cmd))
                print('Exiting.')
                sys.exit(1)
            pythontex_info['script_path']=path.split(script_path)[0]
            if not path.exists(path.join(pythontex_info['script_path'],'pythontex_utils.py')):
                print('* PythonTeX error\n    Cannot find pythontex_utils.py')
                sys.exit(1)
    else:
        #We get the path to pythontex_utils.py via kpsewhich.  Then we strip off end of line characters and the end of the path ("/pythontex_utils.py")
        exec_cmd=['kpsewhich', '-format', 'texmfscripts', 'pythontex_utils.py']
        try:
            script_path=check_output(exec_cmd).rstrip('\r\n')
        except OSError:
            print('Your system appears to lack kpsewhich.  Exiting.')
            sys.exit(1)
        except CalledProcessError:
            print('kpsewhich is not happy with its arguments.')
            print('This command was attempted:')
            print('    ' + ' '.join(exec_cmd))
            print('Exiting.')
            sys.exit(1)
        pythontex_info['script_path']=path.split(script_path)[0]
        #We need to make sure that we succeeded in getting the path.
        if not path.exists(path.join(pythontex_info['script_path'],'pythontex_utils.py')):
            print('* PythonTeX error\n    Cannot find pythontex_utils.py')
            sys.exit(1)
        oldpygments_settings=defaultdict(tuple)
        oldsaveverbatim_threshold=saveverbatim_threshold
    #Update path for scripts
    update_types_import(pythontex_info['script_path'])
    
    
    #Hash the code to see what has changed and needs to be updated
    #Technically, the code could simultaneously be hashed and divided into lists according to session and group.
    #But that approach would involve creating and appending to a lot of lists that would never be used.
    #The current approach of hashing, then only creating lists of code that must be executed, involves more matching than the simultaneous approach, but it also involve much less memory allocation and list appending.
    #Any speed tradeoffs are likely negligible, and no tests have been conducted.
    #The current approach is based on simplicity and on the supposition that it might be faster due to the lack of unnecessary allocation and appending.
    #Note that the PythonTeX data accompanying code must be hashed in addition to the code; the code could stay the same, but its distribution among commands and environments could have changed since the last run.
    print('  Hashing...')
    sys.stdout.flush()
    hasher=defaultdict(sha1)
    #Calculate hashes for each set of code (type,session,group)
    #Ignore the first few lines, which are reserved for parameter passing from LaTeX
    #Also, we ignore the last line of the code, which is just "PYTHONTEX#END#END#END#END#END#END#END#", to avoid creating an entry for it
    for codeline in codefile[codefile_param_offset:-1]:
        #Detect if start of new command/environment, and switch variables if so
        if codeline.startswith('=>PYTHONTEX#'):
            [inputtype,inputsession,inputgroup]=codeline.split('#',4)[1:4]
            currentkey=inputtype+'#'+inputsession+'#'+inputgroup
            if inputsession.startswith('EXT:'):
			    #We use path.normcase to make sure any slashes are appropriate, thus allowing code in subdirectories to be specified
                extfile=path.normcase(inputsession.replace('EXT:',''))
                if not path.exists(extfile):
                    print('* PythonTeX error\n    Cannot find external file '+extfile+' to input.  Exiting')
                    sys.exit(1)
                f=open(extfile,'rb')
                hasher[currentkey].update(f.read())
                f.close()
            else:
				#We need to hash most of the code info, because code needs to be executed again if anything but the line number changes
                hasher[currentkey].update(codeline.rsplit('#',2)[0])
        else:
            hasher[currentkey].update(codeline)
    #Create dictionary of hashes
    hashdict=defaultdict(str)
    for key in hasher:
        hashdict[key]=hasher[key].hexdigest()
    del hasher
    #Eventually, may want to add a check for invalid keys here
    
    
    #Check for use of the Pygments commands/environment, and assign proper Pygments settings if necessary
    #Unlike regular PythonTeX families of commands and environments, the Pygments commands and environment don't automatically create their own Pygments settings.
    #This is because we can't know ahead of time which lexers will be needed; these commands and environments take a lexer name as an argument.
    #We can only do this now, since we need the hashdict
    for key in hashdict:
        inputtype=key.split('#',1)[0]
        if inputtype.startswith('PYG') and inputtype not in pygments_settings:
            lexer=inputtype.replace('PYG','',1)
            pygstyle='default'
            pygtexcomments=False
            pygmathescape=False
            if globalpygstyle != '':
                pygstyle=globalpygstyle
            if globalpygtexcomments != '':
                pygtexcomments=globalpygtexcomments
            if globalpygmathescape != '':
                pygmathescape=globalpygmathescape
            pygments_settings[inputtype]=(lexer,pygstyle,pygtexcomments,pygmathescape)
    
    
    #See what needs to be updated.
    #This code may not be optimal for the first run; it is written with subsequent runs in mind.
    #If PythonTeX has run before, load the old hash values and compare
    #Otherwise, run everything
    updateresults=defaultdict(bool)
    #If stored hashes and PythonTeX labels (to be referenced) are present in pythontex_info, determine what has changed so only that code may be executed
    #Otherwise, execute everything.
    #Along the way, clean up old files and see if Pygments content needs to be updated
    updatepygments=False
    if 'hashdict' in pythontex_info and 'pytxref' in pythontex_info:
        oldhashdict=pythontex_info['hashdict']
        #Compare the hash values, and set which code needs to be run
        for key in hashdict:
            if key in oldhashdict and hashdict[key]==oldhashdict[key]:
                updateresults[key]=False
            else:
                updateresults[key]=True
        #Clean up for code that will be run again, and for code that no longer exists
		#This could also be done by keeping a running list of everything created, but the extra performance from that approach is probably negligible
        for key in hashdict:
            if updateresults[key]:
                ls=listdir(outputdir)
                [inputtype,inputsession,inputgroup]=key.split('#')
                if inputtype in pygments_settings:
                    updatepygments=True
                pattern=inputtype+'_'+inputsession+'_'+inputgroup
                for f in ls:
                    if f.startswith(pattern):
                        remove(path.join(outputdir,f))
        for key in oldhashdict:
            if key not in hashdict:
                ls=listdir(outputdir)
                [inputtype,inputsession,inputgroup]=key.split('#')
                if inputtype in oldpygments_settings:
                    updatepygments=True
                pattern=inputtype+'_'+inputsession+'_'+inputgroup
                for f in ls:
                    if f.startswith(pattern):
                        remove(path.join(outputdir,f))
    else:
        for key in hashdict:
            updateresults[key]=True
        if len(pygments_settings)>0:
            updatepygments=True
    #It is tempting to think that we would go ahead and save the new hashes at this point.
    #But actually we must wait until error messages are returned.
    #If a (type, session, group) returns an error message, then we need to set its hash value to a null string so that it will be executed the next time PythonTeX runs (hopefully after the cause of the error has been resolved).

    
    #Parse the .pytxcode file into code types, sessions, and groups
    print('  Parsing...')
    sys.stdout.flush()
    codedict=defaultdict(list)
    #We need to keep track of last instance for each session, so duplicates can be eliminated.
    #Some LaTeX environments process their contents multiple times and thus will create duplicates.
    #We initialize to -1, since instances begin at zero.
    lastinstance=defaultdict(int)
    for key in hashdict:
        lastinstance[key]=-1
    #Ignore the first few lines that are use for parameters, and skip the last line
    for codeline in codefile[codefile_param_offset:-1]:
        #Detect if start of new command/environment, and switch variables if so
        if codeline.startswith('=>PYTHONTEX#'):
            switched=True
            [inputtype,inputsession,inputgroup,inputinstance,inputcmd,inputstyle,inputline]=codeline.split('#')[1:8]
            currentkey=inputtype+'#'+inputsession+'#'+inputgroup
            currentinstance=int(inputinstance)
            proceed=True
            #We have to check for environments that are read multiple times (and thus written to .pytxcode multiple times) by LaTeX
            if updateresults[currentkey] and lastinstance[currentkey]<currentinstance:
                lastinstance[currentkey]=currentinstance
                #We need to ignore any verbatim environments and commands
                #If any are present, they are to be typeset by Pygments, not actually executed as code
                #Note that we don't have to check for EXT:<file> sessions, because they are never followed by code and thus can't affect the codedict
                if inputcmd=='verb' or inputcmd=='inlinev':
                    proceed=False
            else:
                proceed=False
            #We need to know if we are dealing with an inline command, so we can treat it appropriately
            if inputcmd=='inline':
                inline=True
            else:
                inline=False
        #Only collect for a session (and later write it to a file) if it needs to be updated
        elif proceed:
            #If just switched commands/environments, associate with the input line and check for indentation errors
            if switched:
                switched=False
                codedict[currentkey].append(typedict[inputtype].set_inputs(
                        inputtype,inputsession,inputgroup,inputinstance,inputcmd,inputstyle,inputline))
                if not inline:
                    codedict[currentkey].append(typedict[inputtype].set_printing(inputinstance))
                #We need to make sure that each time we switch, we are starting out with no indentation
                #Technically, we could allow indentation to continue between commands and environments, but that seems like a recipe for disaster.
                if codeline.startswith(' ') or codeline.startswith('\t'):
                    print('* PythonTeX error\n    Command/environment cannot begin with indentation (space or tab) near line '+inputline)
                    sys.exit(1)
            if inline:
                codedict[currentkey].append(typedict[inputtype].inline(codeline))
            else:
                codedict[currentkey].append(codeline)

    #Save the code sessions that need to be updated
    for key in codedict:
        if not key.startswith('PYG'):
            [inputtype,inputsession,inputgroup]=key.split('#')
            sessionfile=open(path.join(outputdir,
                    inputtype+'_'+inputsession+'_'+inputgroup+'.'+typedict[inputtype].extension),'w')
            sessionfile.write(typedict[inputtype].shebang)
            sessionfile.write('\n\n')
            sessionfile.write('\n'.join(typedict[inputtype].imports))
            sessionfile.write('\n')
            sessionfile.write(typedict[inputtype].set_workingdir(outputdir))
            sessionfile.write('\n\n')
            sessionfile.write(typedict[inputtype].open_reffile(outputdir,
                    inputtype+'_'+inputsession+'_'+inputgroup))
            sessionfile.write('\n\n')
            sessionfile.write(''.join(codedict[key]))
            sessionfile.write('\n\n')
            sessionfile.write(typedict[inputtype].close_reffile(outputdir,
                    inputtype+'_'+inputsession+'_'+inputgroup))
            sessionfile.close()

    #Execute code using multiprocessing
    print('  Executing...')
    sys.stdout.flush()
    pool=multiprocessing.Pool(max_processes)
    tasks=[]
    #Add in a Pygments process if applicable
    #For debugging:    do_pygments(outputdir,jobname,saveverbatim_threshold,oldsaveverbatim_threshold,pygments_settings,oldpygments_settings,updateresults,codefile,codefile_param_offset)
    if updatepygments or pygments_settings!=oldpygments_settings \
            or saveverbatim_threshold!=oldsaveverbatim_threshold:
        tasks.append(pool.apply_async(do_pygments,[outputdir,jobname,saveverbatim_threshold,oldsaveverbatim_threshold,pygments_settings,oldpygments_settings,updateresults,codefile,codefile_param_offset]))
    #Add in code processes
    #Note that everything placed in the codedict needs to be executed, based on previous testing--no further testing is needed here
    for key in codedict:
        [inputtype,inputsession,inputgroup]=key.split('#')
        tasks.append(pool.apply_async(run_code,[inputtype,inputsession,inputgroup,outputdir]))
    for task in tasks:
        task.get()

    #Combine the LaTeX labels created by all code and combine with pre-existing labels
    if 'pytxref' in pythontex_info:
        pytexrefs=pythontex_info['pytxref']
        #Clean out unused code
        for key in pytexrefs.keys():
            if key not in hashdict:
                del pytexrefs[key]
    else:
        pytexrefs=defaultdict(list)
    #Update the dictionary of labels that PythonTeX will reference
    #Note that we only go through the keys in the codedict, because only the codedict keys could have created labels
    for key in codedict:
        [inputtype,inputsession,inputgroup]=key.split('#')
        reffile=path.join(outputdir,inputtype+'_'+inputsession+'_'+inputgroup+'.pytxref')
        if path.exists(reffile):
            f=open(reffile,'r')
            pytexrefs[key]=f.readlines()
            f.close()
    #Update pythontex_info
    pythontex_info['pytxref']=pytexrefs
    #Concatenate all labels into a single file, which may be pulled into LaTeX
    catreffile=open(path.join(outputdir,jobname+'.pytxref'),'w')
    for key in pytexrefs:
        catreffile.write(''.join(pytexrefs[key]))
    catreffile.close()
    
    #Print errors, modifying line numbers to correspond with the tex document
    #We also set the hashes corresponding to any (type,session,group)'s with error to null strings.
    #This makes sure they will be executed the next time.
    print('  Cleaning up and reporting errors...')
    sys.stdout.flush()
    #Currently, error messages are printed in order of appearance, one (type,session,group) at a time.
    #This has the advantage that all errors from one set of code are together.
    errorcount=0
    for key in codedict:
        [inputtype,inputsession,inputgroup]=key.split('#')
        basename=inputtype+'_'+inputsession+'_'+inputgroup
        errfilename=path.join(outputdir,basename+'.err')
        codefilename=path.join(outputdir,basename+'.'+typedict[inputtype].extension)
        #Only work with files that have a nonzero size (there might be a better way to do this, maybe with exit codes?)
        if path.exists(errfilename) and stat(errfilename).st_size!=0:
            #Reset the hash value, so that the code will be run next time
            hashdict[key]=''
            #Open error and code files
            # #### Is there any reason not to just use the code that is still in memory?
            f=open(errfilename)
            errfile=f.readlines()
            f.close()
            f=open(codefilename)
            codefile=f.readlines()
            f.close()
            #We need to let the user know we are switching code files
            print('\n---- Errors for '+basename+' ----')
            for errline in errfile:
                if basename in errline and search('line \d+',errline):
                    errorcount+=1
                    #Offset by one for zero indexing, one for previous line
                    errlinenumber=int(search('line (\d+)',errline).groups()[0])-2
                    offset=0
                    while errlinenumber>=0 and not codefile[errlinenumber].startswith('pytex.inputline='):
                        errlinenumber-=1
                        offset+=1
                    if errlinenumber>=0:
                        codelinenumber=int(match('pytex.inputline=\'(\d+)\'',codefile[errlinenumber]).groups()[0])
                        codelinenumber+=offset
                        print('* PythonTeX code error on line '+str(codelinenumber)+':')
                    else:
                        print('* PythonTeX code error.  Error line cannot be determined.')
                        print('* Error is likely due to system and/or PythonTeX-generated code.')
                print('  '+errline.rstrip('\r\n'))

    
    #Clean up temp files
    if keeptemps=='none' or keeptemps=='code':
        ls=listdir(outputdir)
        for key in codedict:
            [inputtype,inputsession,inputgroup]=key.split('#')
            if keeptemps=='none':
                for ext in [typedict[inputtype].extension,'pytxref','out','err']:
                    f=path.join(outputdir,inputtype+'_'+inputsession+'_'+inputgroup+'.'+ext)
                    if path.exists(f):
                        remove(f)
            if keeptemps=='code':
                for ext in ['pytxref','out','err']:
                    f=path.join(outputdir,inputtype+'_'+inputsession+'_'+inputgroup+'.'+ext)
                    if path.exists(f):
                        remove(f)

    #Save info for next run
	pythontex_info['hashdict']=hashdict
    pythontex_info['pygments_settings']=pygments_settings
    pythontex_info['saveverbatim_threshold']=saveverbatim_threshold
    f=open(pythontex_info_file,'wb')
    pickle.dump(pythontex_info,f,-1)
    f.close()
    
    # Print exit message
    print('\n--------------------------------------------------')
    print('PythonTeX: ' + jobnameraw + ' - ' + str(errorcount) + ' error(s)')

