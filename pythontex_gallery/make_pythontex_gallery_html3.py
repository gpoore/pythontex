# -*- coding: utf8 -*-

'''
This script creates an HTML version of pythontex_gallery.tex, using
depythontex.  This task could be accomplished manually with little effort,
but that would involve directly modifying pythontex_gallery.tex, which is
undesirable.

The conversion process involves a few tricks for dealing with image formats
and paths.  These could be unnecessary in a document that is specifically
written with HTML conversion in mind.  For example, all images could be
saved in the main document directory (or have their full path specified
explicitly), all images could be saved in PNG format, and all images could
have their extension specified in the `\includegraphics` command.

Pandoc doesn't currently deal with all the LaTeX in the gallery file
correctly, so a few special tweaks are required.
'''

# Imports
#// Python 2
#from __future__ import unicode_literals
#from io import open
#\\ End Python 2
import os
import re
import subprocess
import shutil


# Script params
encoding = 'utf-8'

# Read in the gallery
with open('pythontex_gallery.tex', encoding=encoding) as f:
    gallery = f.readlines()


# Add depythontex package option
# This assumes that the pythontex `\usepackage` is alone
for n, line in enumerate(gallery):
    if re.search(r'\\usepackage.*\{pythontex\}', line):
        if re.search(r'\\usepackage\[', line):
            gallery[n] = re.sub(r'\[(.*)\]', r'[\1, depythontex]', line)
        else:
            gallery[n] = re.sub(r'\\usepackage.*\{pythontex\}', '\\usepackage[depythontex]{pythontex}', line)
        break
# Change the save location and extension of any graphics
# This assumes `\includegraphics` doesn't use explicit extensions
# Also get rid of mdframed frames, because Pandoc can't currently handle their optional arguments
for n, line in enumerate(gallery):
    if 'savefig' in line and re.search(r"savefig\('\w+\.pdf'", line):
        gallery[n] = re.sub(r"savefig\('(\w+)\.pdf'", r"savefig('\1.png'", line)
    if r'\includegraphics' in line and re.search(r'\\includegraphics(?:\[.*\])?\{\w+\.pdf\}', line):
        gallery[n] = re.sub(r'\\includegraphics(?:\[.*\])?\{(\w+)\.pdf\}', r'\\includegraphics{\1.png}', line)
    if r'\begin{mdframed}' in line:
        gallery[n] = re.sub(r'\\begin\{mdframed\}(?:\[.*\])?', '', line)
    if r'\end{mdframed}' in line:
        gallery[n] = re.sub(r'\\end\{mdframed\}', '', line)


# Create a temp directory and switch to it
os.mkdir('depy_temp')
os.chdir('depy_temp')


# Save the modified version of the gallery
with open('pythontex_gallery.tex', 'w', encoding=encoding) as f:
    f.write(''.join(gallery))


# Compile the document with depythontex, and create html
subprocess.call(['pdflatex', '-interaction=nonstopmode', 'pythontex_gallery.tex'])
try:
    subprocess.call(['pythontex', 'pythontex_gallery.tex'])
except:
    subprocess.call(['pythontex.py', 'pythontex_gallery.tex'])
subprocess.call(['pdflatex', '-interaction=nonstopmode', 'pythontex_gallery.tex'])
# Use minted-style listings, because Pandoc currently doesn't support some features of listings' `\lstinline`
try:
    subprocess.call(['depythontex', '-o', 'depythontex_pythontex_gallery.tex', 'pythontex_gallery.tex', '--listing=minted'])
except:
    subprocess.call(['depythontex.py', '-o', 'depythontex_pythontex_gallery.tex', 'pythontex_gallery.tex', '--listing=minted'])
with open('depythontex_pythontex_gallery.tex', 'r', encoding=encoding) as f:
    depy = f.read()
depy = depy.replace('{python3}', '{python}').replace('{pycon}', '{python}')
with open('depythontex_pythontex_gallery.tex', 'w', encoding=encoding) as f:
    f.write(depy)
subprocess.call(['pandoc', '--standalone', '--mathjax', '--highlight-style', 'tango', 'depythontex_pythontex_gallery.tex', '-o', 'pythontex_gallery.html'])


# Move html and graphics to the main document directory
if os.path.isfile(os.path.join('..', 'pythontex_gallery.html')):
    os.remove(os.path.join('..', 'pythontex_gallery.html'))
shutil.move('pythontex_gallery.html', '..')
graphics_files = os.listdir('.')
for file in graphics_files:
    if file.endswith('.png'):
        if os.path.isfile(os.path.join('..', file)):
            os.remove(os.path.join('..', file))
        shutil.move(file, '..')


# Clean up
os.chdir('..')
shutil.rmtree('depy_temp')
