#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Install PythonTeX

This installation script is written to work with TeX Live and MiKTeX.  Note
that PythonTeX is included in TeX Live 2013 and later, and may be installed 
via the package manager.  Thus, this installation script is only needed with 
TeX Live when you wish to install the latest version.  PythonTeX is not 
currently available via the MiKTeX package manager.

The script will automatically overwrite (and thus update) all previously 
installed PythonTeX files in the designated installation location.  When 
Kpathsea is available, files may be installed in TEXMFDIST, TEXMFLOCAL, 
TEXMFHOME, or a manually specified location.  Otherwise, the installation 
location must be specified manually.  Installing in TEXMFDIST is useful 
under TeX Live if you want to install PythonTeX and then update it in the 
future via the package manager.

The `mktexlsr` (TeX Live) or `initexmf --update-fndb` (MiKTeX) command is 
executed at the end of the script, to make the system aware of any new files.

Under TeX Live, the script attempts to create a binary wrapper (Windows) or 
symlink (Linux and OS X) for launching the main PythonTeX scripts, 
`pythontex*.py` and `depythontex*.py`.  Under MiKTeX, it attempts to create
a batch file in `miktex/bin`.


Copyright (c) 2012-2014, Geoffrey M. Poore
All rights reserved.
Licensed under the BSD 3-Clause License:
    http://www.opensource.org/licenses/BSD-3-Clause

'''


# Imports
import sys
import platform
from os import path, mkdir, makedirs
if platform.system() != 'Windows':
    # Only create symlinks if not under Windows 
    # (os.symlink doesn't exist under Windows)
    from os import symlink, chmod, unlink
from subprocess import call, check_call, check_output
from shutil import copy
import textwrap


# We need a version of input that works under both Python 2 and 3
try:
    input = raw_input
except:
    pass


# Print startup messages and notices
print('Preparing to install PythonTeX')
if platform.system() != 'Windows':
    message = '''
              You may need to run this script with elevated permissions
              and/or specify the environment.  For example, you may need
              "sudo env PATH=$PATH".  That is typically necessary when your
              system includes a TeX distribution, and you have manually
              installed another distribution (common with Ubuntu etc.).  If 
              the installation path you want is not automatically detected, 
              it may indicate a permissions issue.              
              '''
    print(textwrap.dedent(message))


# Attempt to detect the TeX distribution
try:
    if sys.version_info.major == 2:
        texout = check_output(['latex', '--version'])
    else:
        texout = check_output(['latex', '--version']).decode('utf-8')
except:
    sys.exit('Could not retrieve latex info when running "latex --version"')
if 'TeX Live' in texout:
    detected_texdist = True
    texlive = True
    miktex = False
elif platform.system() == 'Windows' and 'MiKTeX' in texout:
    detected_texdist = True
    texlive = False
    miktex = True
else:
    detected_texdist = False
    texlive = False
    miktex = False


# Make sure all necessary files are present
# The pythontex_gallery and pythontex_quickstart are optional; we 
# check for them when installing doc, and install if available
needed_files = ['pythontex.py', 'pythontex2.py', 'pythontex3.py',
                'pythontex_engines.py', 'pythontex_utils.py',
                'depythontex.py', 'depythontex2.py', 'depythontex3.py',
                'pythontex.sty', 'pythontex.ins', 'pythontex.dtx', 
                'pythontex.pdf', 'README',
                'syncpdb.py']
missing_files = False
# Print a list of all files that are missing, and exit if any are
for eachfile in needed_files:
    if not path.exists(eachfile):
        print('Could not find file ' + eachfile)
        missing_files = True
if missing_files:
    sys.exit('Exiting due to missing files.')


# Retrieve the location of valid TeX trees
if sys.version_info[0] == 2:
    try:
        texmf_dist = check_output(['kpsewhich', '-var-value', 'TEXMFDIST']).rstrip('\r\n')
    except:
        texmf_dist = None
    try:
        texmf_local = check_output(['kpsewhich', '-var-value', 'TEXMFLOCAL']).rstrip('\r\n')
    except:
        texmf_local = None
    try:
        texmf_home = check_output(['kpsewhich', '-var-value', 'TEXMFHOME']).rstrip('\r\n')
    except:
        texmf_home = None
else:
    try:
        texmf_dist = check_output(['kpsewhich', '-var-value', 'TEXMFDIST']).decode('utf-8').rstrip('\r\n')
    except:
        texmf_dist = None
    try:
        texmf_local = check_output(['kpsewhich', '-var-value', 'TEXMFLOCAL']).decode('utf-8').rstrip('\r\n')
    except:
        texmf_local = None
    try:
        texmf_home = check_output(['kpsewhich', '-var-value', 'TEXMFHOME']).decode('utf-8').rstrip('\r\n')
    except:
        texmf_home = None


# Get installation location from user
texmf_vars = [texmf_dist, texmf_local, texmf_home]
message = '''
          Choose an installation location.
          
          TEXMFDIST is a good choice if you want to update PythonTeX 
          in the future using your TeX distribution's package manager
          (assuming that is supported).
          
            1. TEXMFDIST
                 {0}
            2. TEXMFLOCAL
                 {1}
            3. TEXMFHOME
                 {2}
            4. Manual location
            
            5. Exit without installing
          '''.format(*[x if x else '<INVALID>' for x in texmf_vars])

if any(texmf_vars):
    path_choice = ''
    while (path_choice not in ('1', '2', '3', '4', '5') or 
            (int(path_choice) <= 3 and not texmf_vars[int(path_choice)-1])):
        print(textwrap.dedent(message))
        path_choice = input('Installation location (number):  ')
        if path_choice == '':
            sys.exit()
    if path_choice == '1':
        texmf_path = texmf_dist
    elif path_choice == '2':
        texmf_path = texmf_local
    elif path_choice == '3':
        texmf_path = texmf_home
    elif path_choice == '4':
        texmf_path = input('Enter a path:\n')
        if texmf_path == '':
            sys.exit()
        if platform.system() == 'Windows':
            if 'texlive' in texmf_path.lower():
                detected_texdist = True
                texlive = True
                miktex = False
            elif 'miktex' in texmf_path.lower():
                detected_texdist = True
                texlive = False
                miktex = True
    else:
        sys.exit()
else:
    print('Failed to detect possible installation locations automatically.')
    print('TEXMF paths could not be located with kpsewhich.')
    texmf_path = input('Plese enter an installation path, or press "Enter" to exit:\n')
    if texmf_path == '':
        sys.exit()

# Make sure path slashes are compatible with the operating system
# Kpathsea returns forward slashes, but Windows needs back slashes
texmf_path = path.expandvars(path.expanduser(path.normcase(texmf_path)))

# Check to make sure the path is valid 
# This should only be needed for manual input, but it's a good check
if not path.isdir(texmf_path):
    sys.exit('Invalid installation path.  Exiting.')

# Now check that all other needed paths are present
if path_choice != '2':
    doc_path = path.join(texmf_path, 'doc', 'latex')
    package_path = path.join(texmf_path, 'tex', 'latex')
    scripts_path = path.join(texmf_path, 'scripts')
    source_path = path.join(texmf_path, 'source', 'latex')
else:
    doc_path = path.join(texmf_path, 'doc', 'latex', 'local')
    package_path = path.join(texmf_path, 'tex', 'latex', 'local')
    scripts_path = path.join(texmf_path, 'scripts', 'local')
    source_path = path.join(texmf_path, 'source', 'latex', 'local')
# May need to create some local directories
make_paths = False
for eachpath in [doc_path, package_path, scripts_path, source_path]:
    if not path.exists(eachpath):
        if make_paths:
            makedirs(eachpath)
            print('  * Created ' + eachpath)
        else:
            choice = ''
            while choice not in ('y', 'n'):
                choice = input('Some directories do not exist.  Create them? [y/n]  ')
                if choice == '':
                    sys.exit()
            if choice == 'y':
                make_paths = True
                try:
                    makedirs(eachpath)
                    print('  * Created ' + eachpath)
                except (OSError, IOError) as e:
                    if e.errno == 13:
                        print('\nInsufficient permission to install PythonTeX')
                        if platform.system() == 'Windows':
                            message = '''
                                      You may need to run the installer as "administrator".
                                      This may be done under Vista and later by right-clicking on
                                      pythontex_install.bat, then selecting "Run as administrator".
                                      Or you can open a command prompt as administrator 
                                      (Start, Programs, Accessories, right-click Command Prompt,
                                      Run as administrator), change to the directory in which
                                      pythontex_install.py is located, and run 
                                      "python pythontex_install.py".
                                      '''
                            print(textwrap.dedent(message))
                            call(['pause'], shell=True)
                        else:
                            print('(For example, you may need "sudo", or possibly "sudo env PATH=$PATH")\n')
                        sys.exit(1)
                    else:
                        raise
            else:
                message = '''
                          Paths were not created.  The following will be needed.
                            * {0}
                            * {1}
                            * {2}
                            * {3}
                          
                          Exiting.
                          '''.format(doc_path, package_path, scripts_path, source_path)
                print(textwrap.dedent(message))
                sys.exit()

# Modify the paths by adding the pythontex directory, which will be created
doc_path = path.join(doc_path, 'pythontex')
package_path = path.join(package_path, 'pythontex')
scripts_path = path.join(scripts_path, 'pythontex')
source_path = path.join(source_path, 'pythontex')


# Install files
# Use a try/except in case elevated permissions are needed (Linux and OS X)
print('\nPythonTeX will be installed in \n  ' + texmf_path)
try:
    # Install docs
    if not path.exists(doc_path):
        mkdir(doc_path)
    copy('pythontex.pdf', doc_path)
    copy('README', doc_path)
    for doc in ('pythontex_quickstart.tex', 'pythontex_quickstart.pdf', 
                'pythontex_gallery.tex', 'pythontex_gallery.pdf'):
        if path.isfile(doc):
            copy(doc, doc_path)
        else:
            doc = path.join('..', doc.rsplit('.', 1)[0], doc)
            if path.isfile(doc):
                copy(doc, doc_path)
    # Install package
    if not path.exists(package_path):
        mkdir(package_path)
    copy('pythontex.sty', package_path)
    # Install scripts
    if not path.exists(scripts_path):
        mkdir(scripts_path)
    copy('pythontex.py', scripts_path)
    copy('depythontex.py', scripts_path)
    copy('pythontex_utils.py', scripts_path)
    copy('pythontex_engines.py', scripts_path)
    copy('syncpdb.py', scripts_path)
    for ver in [2, 3]:
        copy('pythontex{0}.py'.format(ver), scripts_path)
        copy('depythontex{0}.py'.format(ver), scripts_path)
    # Install source
    if not path.exists(source_path):
        mkdir(source_path)
    copy('pythontex.ins', source_path)
    copy('pythontex.dtx', source_path)
except (OSError, IOError) as e:
    if e.errno == 13:
        print('\nInsufficient permission to install PythonTeX')
        if platform.system() == 'Windows':
            message = '''
                      You may need to run the installer as "administrator".
                      This may be done under Vista and later by right-clicking on
                      pythontex_install.bat, then selecting "Run as administrator".
                      Or you can open a command prompt as administrator 
                      (Start, Programs, Accessories, right-click Command Prompt,
                      Run as administrator), change to the directory in which
                      pythontex_install.py is located, and run 
                      "python pythontex_install.py".
                      '''
            print(textwrap.dedent(message))
            call(['pause'], shell=True)
        else:
            print('(For example, you may need "sudo", or possibly "sudo env PATH=$PATH")\n')
        sys.exit(1)
    else:
        raise        


# Install binary wrappers, create symlinks, or suggest the creation of 
# wrappers/batch files/symlinks.  This part is operating system dependent.
if platform.system() == 'Windows':
    # If under Windows, we create a binary wrapper if under TeX Live 
    # or a batch file if under MiKTeX.  Otherwise, alert the user 
    # regarding the need for a wrapper or batch file.    
    if miktex:
        try:
            if sys.version_info.major == 2:
                bin_path = check_output(['kpsewhich', '-var-value', 'TEXMFDIST']).rstrip('\r\n')
            else:
                bin_path = check_output(['kpsewhich', '-var-value', 'TEXMFDIST']).decode('utf-8').rstrip('\r\n')
            bin_path = path.join(bin_path, 'miktex', 'bin')
            
            for s in ('pythontex.py', 'depythontex.py'):
                batch = '@echo off\n"{0}" %*\n'.format(path.join(scripts_path, s))
                f = open(path.join(bin_path, s.replace('.py', '.bat')), 'w')
                f.write(batch)
                f.close()
        except:
            message = '''
                      Could not create a batch file for launching pythontex.py and 
                      depythontex.py.  You will need to create a batch file manually.
                      Sample batch files are included with the main PythonTeX files.
                      The batch files should be in a location on the Windows PATH.
                      The bin/ directory in your TeX distribution may be a good 
                      location.
                      
                      The scripts pythontex.py and depythontex.py are located in 
                      the following directory:
                        {0}
                      '''.format(scripts_path)
            print(textwrap.dedent(message))
    else:
        # Assemble the binary path, assuming TeX Live
        # The directory bin/ should be at the same level as texmf
        bin_path = path.join(path.split(texmf_path)[0], 'bin', 'win32') 
        if path.exists(path.join(bin_path, 'runscript.exe')):
            for f in ('pythontex.py', 'depythontex.py'):
                copy(path.join(bin_path, 'runscript.exe'), path.join(bin_path, '{0}.exe'.format(f.rsplit('.')[0])))
            print('\nCreated binary wrapper...')
        else:
            message = '''
                      Could not create a wrapper for launching pythontex.py and 
                      depythontex.py; did not find runscript.exe.  You will need 
                      to create a wrapper manually, or use a batch file.  Sample 
                      batch files are included with the main PythonTeX files.  
                      The wrapper or batch file should be in a location on the 
                      Windows PATH.  The bin/ directory in your TeX distribution 
                      may be a good location.
                      
                      The scripts pythontex.py and depythontex.py are located in 
                      the following directory:
                        {0}
                      '''.format(scripts_path)
            print(textwrap.dedent(message))
else:
    # Optimistically proceed as if every system other than Windows can 
    # share one set of code.
    root_path = path.split(texmf_path)[0]
    # Create a list of all possible subdirectories of bin/ for TeX Live
    # Source:  http://www.tug.org/texlive/doc/texlive-en/texlive-en.html#x1-250003.2.1
    texlive_platforms = ['alpha-linux', 'amd64-freebsd', 'amd64-kfreebsd',
                         'armel-linux', 'i386-cygwin', 'i386-freebsd',
                         'i386-kfreebsd', 'i386-linux', 'i386-solaris',
                         'mips-irix', 'mipsel-linux', 'powerpc-aix', 
                         'powerpc-linux', 'sparc-solaris', 'universal-darwin',
                         'x86_64-darwin', 'x86_64-linux', 'x86_64-solaris']
    symlink_created = False
    # Try to create a symlink in the standard TeX Live locations
    for pltfrm in texlive_platforms:
        bin_path = path.join(root_path, 'bin', pltfrm)
        if path.exists(bin_path):
            # Unlink any old symlinks if they exist, and create new ones
            # Not doing this gave permissions errors under Ubuntu
            for f in ('pythontex.py', 'pythontex2.py', 'pythontex3.py',
                      'depythontex.py', 'depythontex2.py', 'depythontex3.py'):
                link = path.join(bin_path, f)
                if path.exists(link):
                    unlink(link)
                symlink(path.join(scripts_path, f), link)
                chmod(link, 0o775)
            symlink_created = True
    
    # If the standard TeX Live bin/ locations didn't work, try the typical 
    # location for MacPorts TeX Live.  This should typically be 
    # /opt/local/bin, but instead of assuming that location, we just climb 
    # two levels up from texmf-dist and then look for a bin/ directory that
    # contains a tex executable.  (For MacPorts, texmf-dist should be at 
    # /opt/local/share/texmf-dist.)
    if not symlink_created and platform.system() == 'Darwin':
        bin_path = path.join(path.split(root_path)[0], 'bin')
        if path.exists(bin_path):
            try:
                # Make sure this bin/ is the bin/ we're looking for, by
                # seeing if pdftex exists
                check_output([path.join(bin_path, 'pdftex'), '--version'])
                # Create symlinks
                for f in ('pythontex.py', 'pythontex2.py', 'pythontex3.py',
                          'depythontex.py', 'depythontex2.py', 'depythontex3.py'):
                    link = path.join(bin_path, f)
                    if path.exists(link):
                        unlink(link)
                    symlink(path.join(scripts_path, f), link)
                    chmod(link, 0o775)
                symlink_created = True
            except:
                pass
    if symlink_created:
        print("\nCreated symlink in Tex's bin/ directory...")
    else:
        print('\nCould not automatically create a symlink to pythontex*.py and depythontex*.py.')
        print('You may wish to create one manually, and make it executable via chmod.')
        print('The scripts pythontex*.py and depythontex*.py are located in the following directory:')
        print('    ' + scripts_path)


# Alert TeX to the existence of the package via mktexlsr
if not miktex:
    try:
        # Need to adjust if under Windows with a user-specified TeX Live
        # installation and a default MiKTeX installation; want to call
        # mktexlsr for the user-specified TeX Live installation
        if platform.system() == 'Windows' and 'MiKTeX' in texout:
            check_call(path.join(bin_path, 'mktexlsr'))
        else:
            check_call(['mktexlsr'])
        print('\nRunning "mktexlsr" to make TeX aware of new files...')
    except:
        print('Could not run "mktexlsr".')
        print('Your system may not be aware of newly installed files.')
else:
    success = False
    try:
        check_call(['initexmf', '--admin', '--update-fndb'])
        print('\nRunning "initexmf --admin --update-fndb" to make TeX aware of new files...')
        check_call(['initexmf', '--update-fndb'])
        print('\nRunning "initexmf --update-fndb" to make TeX aware of new files...')
        success = True
    except:
        pass
    if not success:
        try:
            check_call(['initexmf', '--update-fndb'])
            print('\nRunning "initexmf --update-fndb" to make TeX aware of new files...')
            print('Depending on your installation settings, you may also need to run')
            print('"initexmf --admin --update-fndb"')
        except:
            print('Could not run "initexmf --update-fndb" or "initexmf --admin --update-fndb"')
            print('Your system may not be aware of newly installed files.')

            
if platform.system() == 'Windows':
    # Pause so that the user can see any errors or other messages
    # input('\n[Press ENTER to exit]')
    print('\n')
    call(['pause'], shell=True)
