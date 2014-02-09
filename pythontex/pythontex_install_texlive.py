#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Install PythonTeX

This installation script should work with most TeX distributions.  It is 
primarily written for TeX Live.  It should work with other TeX distributions 
that use the Kpathsea library (such as MiKTeX), though with reduced 
functionality in some cases.  It will require manual input when used with a 
distribution that does not include Kpathsea.

The script will overwrite (and thus update) all previously installed PythonTeX 
files.  When Kpathsea is available, files may be installed in TEXMFDIST,
TEXMFHOME, or a manually specified location.  Otherwise, the installation 
location must be specified manually.  Installing in TEXMFDIST is useful if
you want to install PythonTeX and then update it in the future from CTAN.
The mktexlsr command is executed at the end of the script, to make the system 
aware of any new files.

The script attempts to create a binary wrapper (Windows) or symlink 
(Linux and OS X) for launching the main PythonTeX scripts, pythontex*.py and
depythontex*.py.


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


# Print startup messages and warnings
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


# Make sure all necessary files are present
# The pythontex_gallery and pythontex_quickstart are optional; we check for them when installing doc
needed_files = ['pythontex.py', 'pythontex2.py', 'pythontex3.py',
                'pythontex_engines.py', 'pythontex_utils.py',
                'depythontex.py', 'depythontex2.py', 'depythontex3.py',
                'pythontex.sty', 'pythontex.ins', 'pythontex.dtx', 
                'pythontex.pdf', 'README']
missing_files = False
# Print a list of all files that are missing, and exit if any are
for eachfile in needed_files:
    if not path.exists(eachfile):
        print('Could not find file ' + eachfile)
        missing_files = True
if missing_files:
    print('Exiting.')
    sys.exit(1)


# Retrieve the location of valid TeX trees
# Attempt to use kpsewhich; otherwise, resort to manual input 
should_exit = False  # Can't use sys.exit() in try; will trigger except
try:
    if sys.version_info[0] == 2:
        texmf_dist = check_output(['kpsewhich', '-var-value', 'TEXMFDIST']).rstrip('\r\n')
        texmf_local = check_output(['kpsewhich', '-var-value', 'TEXMFLOCAL']).rstrip('\r\n')
        texmf_home = check_output(['kpsewhich', '-var-value', 'TEXMFHOME']).rstrip('\r\n')
    else:
        texmf_dist = check_output(['kpsewhich', '-var-value', 'TEXMFDIST']).decode('utf-8').rstrip('\r\n')
        texmf_local = check_output(['kpsewhich', '-var-value', 'TEXMFLOCAL']).decode('utf-8').rstrip('\r\n')
        texmf_home = check_output(['kpsewhich', '-var-value', 'TEXMFHOME']).decode('utf-8').rstrip('\r\n')
    message = '''
              Choose an installation location.
              
              TEXMFDIST is a good choice if you want to update PythonTeX 
              in the future using your TeX distribution's package manager.
              
                1. TEXMFDIST
                     {0}
                2. TEXMFLOCAL
                     {1}
                3. TEXMFHOME
                     {2}
                4. Manual location
              '''.format(texmf_dist, texmf_local, texmf_home)
    print(textwrap.dedent(message))
    path_choice = input('Installation location (number):  ')
    if path_choice not in ('1', '2', '3', '4'):
        should_exit = True
    else:
        if path_choice == '1':
            texmf_path = texmf_dist
        elif path_choice == '2':
            texmf_path = texmf_local
        elif path_choice == '3':
            texmf_path = texmf_home
        else:
            texmf_path = input('Enter a path:\n')
except:
    print('Cannot automatically find TEXMF paths.')
    print('kpsewhich does not exist or could not be used.')
    # Need to create the variable that tracks the type of installation
    path_choice = '4'
    texmf_path = input('Please enter a valid installation path:\n')
if should_exit:
    sys.exit()
# Make sure path slashes are compatible with the operating system
# Kpathsea returns forward slashes, but Windows needs back slashes
texmf_path = path.expandvars(path.expanduser(path.normcase(texmf_path)))

# Check to make sure the path is valid 
# This is only really needed for manual input 
# The '' check is for empty manual input
if texmf_path == '' or not path.exists(texmf_path):
    print('Invalid installation path.  Exiting.')
    sys.exit(1)
    

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
make_paths = False
for eachpath in [doc_path, package_path, scripts_path, source_path]:
    if not path.exists(eachpath):
        if make_paths:
            makedirs(eachpath)
            print('  * Created ' + eachpath)
        else:
            choice = input('Some directories do not exist.  Create them? [y/n]\n')
            if choice not in ('y', 'n'):
                sys.exit('Invalid choice')
            elif choice == 'y':
                make_paths = True
                makedirs(eachpath)
                print('  * Created ' + eachpath)
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
    for ver in [2, 3]:
        copy('pythontex{0}.py'.format(ver), scripts_path)
        copy('depythontex{0}.py'.format(ver), scripts_path)
    # Install source
    if not path.exists(source_path):
        mkdir(source_path)
    copy('pythontex.ins', source_path)
    copy('pythontex.dtx', source_path)
except OSError as e:
    if e.errno == 13:
        print('Insufficient permission to install PythonTeX')
        print('(For example, you may need "sudo", or possibly "sudo env PATH=$PATH")\n')
        sys.exit(1)
    else:
        raise        


# Install binary wrappers, create symlinks, or suggest the creation of 
# wrappers/batch files/symlinks.  This part is operating system dependent.
if platform.system() == 'Windows':
    # If under Windows, we create a binary wrapper if under TeX Live and 
    # otherwise alert the user regarding the need for a wrapper or batch file.
    
    # Assemble the binary path, assuming TeX Live
    # The directory bin/ should be at the same level as texmf
    bin_path = path.join(path.split(texmf_path)[0], 'bin', 'win32') 
    if path.exists(path.join(bin_path, 'runscript.exe')):
        copy(path.join(bin_path, 'runscript.exe'), path.join(bin_path, 'pythontex.exe'))
        copy(path.join(bin_path, 'runscript.exe'), path.join(bin_path, 'depythontex.exe'))
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
    # Optimistically proceed as if every system other than Windows can share
    # one set of code.
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
            # Create symlink for pythontex*.py
            link = path.join(bin_path, 'pythontex.py')
            # Unlink any old symlinks if they exist, and create new ones
            # Not doing this gave permissions errors under Ubuntu
            if path.exists(link):
                unlink(link)
            symlink(path.join(scripts_path, 'pythontex.py'), link)
            chmod(link, 0o775)
            # Now repeat for depythontex*.py
            link = path.join(bin_path, 'depythontex.py')
            if path.exists(link):
                unlink(link)
            symlink(path.join(scripts_path, 'depythontex.py'), link)
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
                link = path.join(bin_path, 'pythontex.py')
                if path.exists(link):
                    unlink(link)
                symlink(path.join(scripts_path, 'pythontex.py'), link)
                chmod(link, 0o775)
                link = path.join(bin_path, 'depythontex.py')
                if path.exists(link):
                    unlink(link)
                symlink(path.join(scripts_path, 'depythontex.py'), link)
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
try:
    print('\nRunning mktexlsr to make TeX aware of new files...')
    check_call(['mktexlsr'])
except: 
    print('Could not run mktexlsr.')
    print('Your system may not be aware of newly installed files.')


if platform.system() == 'Windows':
    # Pause so that the user can see any errors or other messages
    # input('\n[Press ENTER to exit]')
    print('\n')
    call(['pause'], shell=True)
