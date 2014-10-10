|flattr|_

===============================================
                  PythonTeX
===============================================

-----------------------------------------------
    Fast Access to Python from within LaTeX
-----------------------------------------------


:Author: Geoffrey Poore

:Version: 0.14

:License:  LPPL_ (LaTeX code) and `BSD 3-Clause`_ (Python code)

.. _LPPL: http://www.latex-project.org/lppl.txt

.. _`BSD 3-Clause`: http://www.opensource.org/licenses/BSD-3-Clause

   
Overview
========

PythonTeX provides fast, user-friendly access to Python from within LaTeX.  It allows Python code entered within a LaTeX document to be executed, and the results to be included within the original document.  It also provides syntax highlighting for code within LaTeX documents via the Pygments syntax highlighter.

PythonTeX also provides support for Ruby, Julia, and Octave.  Support for additional languages is coming soon.

See ``pythontex.pdf`` for detailed installation instructions, or use the installation script for TeX Live and MiKTeX.  See ``pythontex_quickstart.pdf`` to get started, and ``pythontex_gallery.pdf`` for examples of what is possible with PythonTeX.

The ``depythontex`` utility creates a copy of a PythonTeX document in which all Python code has been replaced by its output.  This plain LaTeX document is more suitable for journal submission, sharing, or conversion to other document formats.  See ``pythontex_gallery.html`` and the accompanying conversion script for an example of a PythonTeX document that was converted to HTML via ``depythontex`` and `Pandoc <http://johnmacfarlane.net/pandoc/>`_.


Citing PythonTeX
================

If you use PythonTeX in your writing and research, please consider citing it in any resulting publications.  Currently, the best paper to cite is the one published in the `2013 SciPy proceedings <http://conference.scipy.org/proceedings/scipy2013/poore.html>`_.


Latest release
==============

(Full release history is available `here <https://github.com/gpoore/pythontex/blob/master/NEWS.rst>`_.)

v0.14 (2014/07/17)
------------------

New features
~~~~~~~~~~~~

*  All commands for working with code inline are now robust, via 
   ``etoolbox``'s ``\newrobustcmd``.  Among other things, this allows 
   commands like ``\py`` to work in standard captions that have not been 
   redefined to avoid protection issues.
*  Upgraded ``syncpdb`` to v0.2, which provides better list formatting.

Backward-incompatible changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

*  The default working directory is now the main document directory instead 
   of the output directory.  Using the output directory was a common source 
   of confusion for new users and was incompatible with plans for future 
   development.  Old documents in which the working directory was not 
   specified will continue to use the output directory, but PythonTeX will 
   print an upgrade message; new documents will use the new setting.  The 
   output directory may be selected as the working directory manually, or 
   with the shorthand 
   "``\setpythontexworkingdir{<outputdir>}``".

*  Standardized version numbering by removing the "v" prefix from the stored 
   version numbers in Python variables and LaTeX macros.  Standardized the 
   PythonTeX scripts by renaming ``version`` to ``__version__``.


Objectives for future releases
==============================

* Improve support for macro programming with PythonTeX.  Add ``depythontex`` support for user macros.
* Improve system for adding other languages.
* Improve ``stderr`` synchronization.  Simplify support for multiple languages.
* Add finer-grained control.  Work toward ``rerun`` control of execution at the session level, and control of whether ``stdout`` and ``strerr`` are displayed at the command/environment level.
* Refactor to separate the code-management core from LaTeX-related features, so that the core can be used with other document formats (for example, markdown) in a manner similar to Sweave.




.. |flattr| image:: https://api.flattr.com/button/flattr-badge-large.png

.. _flattr: https://flattr.com/submit/auto?user_id=gpoore&url=https://github.com/gpoore/pythontex&title=pythontex&category=software
