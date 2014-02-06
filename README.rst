===============================================
                  PythonTeX
===============================================

-----------------------------------------------
    Fast Access to Python from within LaTeX
-----------------------------------------------


:Author: Geoffrey Poore

:Version: 0.13-beta

:License:  LPPL_ (LaTeX code) and `BSD 3-Clause`_ (Python code)

.. _LPPL: http://www.latex-project.org/lppl.txt

.. _`BSD 3-Clause`: http://www.opensource.org/licenses/BSD-3-Clause

   
Overview
========

PythonTeX provides fast, user-friendly access to Python from within LaTeX.  It allows Python code entered within a LaTeX document to be executed, and the results to be included within the original document.  It also provides syntax highlighting for code within LaTeX documents via the Pygments syntax highlighter.

PythonTeX also provides support for Ruby and Julia.  Support for additional languages is coming soon.

See ``pythontex.pdf`` for detailed installation instructions, or use the installation script for TeX Live.  See ``pythontex_quickstart.pdf`` to get started, and ``pythontex_gallery.pdf`` for examples of what is possible with PythonTeX.

The ``depythontex`` utility creates a copy of a PythonTeX document in which all Python code has been replaced by its output.  This plain LaTeX document is more suitable for journal submission, sharing, or conversion to other document formats.  See ``pythontex_gallery.html`` and the accompanying conversion script for an example of a PythonTeX document that was converted to HTML via ``depythontex`` and `Pandoc <http://johnmacfarlane.net/pandoc/>`_.


Citing PythonTeX
================

If you use PythonTeX in your writing and research, please consider citing it in any resulting publications.  Currently, the best paper to cite is the one published in the `2013 SciPy proceedings <http://conference.scipy.org/proceedings/scipy2013/poore.html>`_.


Latest release
==============

(Full release history is available `here <https://github.com/gpoore/pythontex/blob/master/NEWS.rst>`_.)

v0.13-beta (2014/02/06)
-----------------------

New features
~~~~~~~~~~~~

*  Switching to GitHub's Releases for downloads.
*  TeX information such as page dimensions may now be easily passed to the programming-language side, using the new ``\setpythontexcontext`` command.  Contextual information is stored in the ``context`` attribute of the utilities class, which is a dictionary (and also has attributes in Python).
*  The utilities class now has ``pt_to_in()``, ``pt_to_cm()``, and ``pt_to_mm()`` methods for converting units of TeX points into inches, centimeters, and millimeters.  These work with integers and floats, as well as strings that consist of numbers and optionally end in "pt".  There is also a ``pt_to_bp()`` for converting TeX points (1/72.27 inch) into big (DTP or PostScript) points (1/72 inch).
*  Expanded Quickstart.  Quickstart is now compatible with all LaTeX engines.  Quickstart now avoids ``microtype`` issues on some systems (\#32).
*  Added information on citing PythonTeX (\#28).
*  Utilities class has a new attribute ``id``, which is a string that joins the command family name, session name, and session restart parameters with underscores.  This may be used in creating files that need a name that contains a unique, session-based identifier (for example, names for figures that are saved automatically).

Backward-incompatible changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

*  All utilities-class attributes with names of the form ``input_*`` have been renamed with the "``input_``" removed.  Among other things, this makes it easier to access the ``context`` attribute (``pytex.context`` vs. ``pytex.input_context``).
*  ``depythontex`` now has ``-o`` and ``--output`` command-line options for specifying the name of the output file.  If an output file is not specified, then output is written to ``stdout``.  This allows ``depythontex`` output to be piped to another program.
*  All scripts ``*2.py`` now have shebangs with ``env python2``, and all scripts ``*3.py`` now have shebangs with ``env python3``.  This allows the wrapper scripts (``env python`` shebang) to be used with the default Python installation, and the numbered scripts to be used with specific versions.  Remember that except for console content, the ``--interpreter`` option is what determines the Python version that actually executes code.  The version of Python used to launch ``pythontex.py`` merely determines the version that manages code execution.  (``--interpreter`` support for console content is coming.)
*  Changed the template style used in the ``CodeEngine`` class.  Replacement fields are now surrounded by single curly braces (as in Python's format string syntax), rather than double curly braces.  Literal curly braces are obtained by doubling braces.  This allows the use of literal adjacent double braces in templates, which was not possible previously.
*  The Julia template now uses the new ``in()`` function, replacing ``contains()``.  This requires Julia v0.2.0+.

Bugfixes
~~~~~~~~

*  Modified test for LuaTeX, so that ``\directlua`` is not ``\let`` to ``\relax`` if it does not exist.  This was causing incompatibility with ``babel`` under pdfTeX and XeTeX (\#33).
*  Added missing shebangs to ``depythontex*.py``.  Handling of ``utilspath`` is now more forgiving, so that ``pythontex_utils.py`` can be installed in alternate locations (\#23).
*  ``depythontex`` no longer leaves a blank line where ``\usepackage{pythontex}`` was removed.
*  Console environments typeset with ``fancyvrb`` no longer end with an unnecessary empty line.
*  Fixed bug in installer when ``kpsewhich`` was not found (\#21).


Objectives for future releases
==============================

* Improve support for macro programming with PythonTeX.  Add ``depythontex`` support for user macros.
* Improve system for adding other languages.
* Improve ``stderr`` synchronization.  Simplify support for multiple languages.
* Add finer-grained control.  Work toward ``rerun`` control of execution at the session level, and control of whether ``stdout`` and ``strerr`` are displayed at the command/environment level.
* Refactor to separate the code-management core from LaTeX-related features, so that the core can be used with other document formats (for example, markdown) in a manner similar to Sweave.
