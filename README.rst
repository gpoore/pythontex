===============================================
                  PythonTeX
===============================================

-----------------------------------------------
    Fast Access to Python from within LaTeX
-----------------------------------------------


:Author: Geoffrey Poore

:Version: 0.13

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

v0.13 (2014/07/14)
------------------

New features
~~~~~~~~~~~~

*  Added ``--interactive`` command-line option. This runs a single
   session in interactive mode, allowing user input. Among other things,
   this is useful when working with debuggers.

*  Added ``--debug`` command-line option. This runs a single session
   with the default debugger in interactive mode. Currently, only
   standard (non-console) Python sessions are supported. The default
   Python debugger is the new ``syncpdb``, which wraps ``pdb`` and
   synchronizes code line numbers with document line numbers. All
   ``pdb`` commands that take a line number or filename:lineno as an
   argument will refer to document files and line numbers when the
   argument has a percent symbol (``%``) as a prefix. For example,
   ``list %50`` lists code that came from around line 50 in the
   document. The ``--debug`` option will support other languages and
   provide for customization in the future.

*  Added command-line option ``--jobs``, which allows the maximum number
   of concurrent processes to be specified (#35).

*  Added support for GNU Octave, via the ``octave`` family of commands
   and environments (#36). Parsing of Octave stderr is not ideal, though
   synchronization works in most cases; this will be addressed by a
   future rewrite of the stderr parser.

*  Installer now automatically works with MiKTeX, not just TeX Live.

*  The PythonTeX utilities class has a new ``open()`` method that opens
   files and automatically tracks dependencies/created files.

*  When ``pythontex2.py`` and ``pythontex3.py`` are run directly, the
   Python interpreter is automatically set to a reasonable default
   (``py -2`` or ``py -3`` under Windows, using the Python 3.3+ wrapper;
   ``python2`` or ``python3`` under other systems).

*  The installer now creates symlinks for the numbered scripts
   ``pythontex*.py`` and ``depythontex*.py``.

*  Added Python version checking to all numbered scripts.

*  Under Python, the type of data passed via ``\setpythontexcontext`` may 
   now be set using YAML-style tags (``!!str``, ``!!int``, ``!!float``). For 
   example, ``{myint=!!int 123}``.

*  The ``fancyvrb`` options ``firstline`` and ``lastline`` now work with
   the ``pygments`` environment and ``\inputpygments`` command. This required 
   some additional patching of ``fancyvrb``.

*  The ``pytx@Verbatim`` and ``pytx@SaveVerbatim`` environments are now
   used for typesetting verbatim code. These are copies of the
   ``fancyvrb`` environments. This prevents conflicts when literal
   ``Verbatim`` and ``SaveVerbatim`` environments need to be typeset.

*  Improved ``latexmk`` compatibility (#40). Added discussion of
   ``latexmk`` usage to documentation.

*  Tildes ``~`` may now be used in ``outputdir`` and ``workingdir`` to
   refer to the user’s home directory, even under Windows.

Bugfixes
~~~~~~~~

*  Fixed a bug that prevented created files from being cleaned up when
   the working directory was not the document root directory and the
   full path to the files was not provided.

*  Fixed a bug that prevented the ``fvextfile`` option from working when
   external files were highlighted.


Objectives for future releases
==============================

* Improve support for macro programming with PythonTeX.  Add ``depythontex`` support for user macros.
* Improve system for adding other languages.
* Improve ``stderr`` synchronization.  Simplify support for multiple languages.
* Add finer-grained control.  Work toward ``rerun`` control of execution at the session level, and control of whether ``stdout`` and ``strerr`` are displayed at the command/environment level.
* Refactor to separate the code-management core from LaTeX-related features, so that the core can be used with other document formats (for example, markdown) in a manner similar to Sweave.
