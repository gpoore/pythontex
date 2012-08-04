===============================================
                  PythonTeX
===============================================

-----------------------------------------------
    Fast Access to Python from within LaTeX
-----------------------------------------------


:Author: Geoffrey Poore

:Version: 0.9beta3

:License:  LPPL_ (LaTeX code) and `BSD 3-Clause`_ (Python code)

.. _LPPL: http://www.latex-project.org/lppl.txt

.. _`BSD 3-Clause`: http://www.opensource.org/licenses/BSD-3-Clause


PythonTeX provides fast, user-friendly access to Python from within LaTeX.  It allows Python code entered within a LaTeX document to be executed, and the results to be included within the original document.  It also provides syntax highlighting for code within LaTeX documents via the Pygments package.

See pythontex.pdf for installation instructions.  See pythontex_gallery.pdf for examples of what is possible with PythonTeX.


Current status
--------------

The 0.9 release has been delayed due to the addition of features that were originally intended for a later release (such as Unicode support).  PythonTeX will remain in beta for at least the rest of the summer.  But it should already be stable enough for most applications.


Change log
----------

v0.9beta3 (2012/07/17)

* Added Unicode support, which required the Python code to be split into 
  one set for Python 2 and another set for Python 3.  This will require
  any old installation to be completely removed, and a new installation
  created from scratch.
* Refactoring of Python code.  Documents should automatically re-execute 
  all code after updating to the new version.  Otherwise, you should delete
  the PythonTeX directory and run PythonTeX.
* Improved installation script.
* Added package options:  pyfuture, stderr, upquote, pyglexer, pyginline. 
  Renamed the pygextfile option to fvextfile.
* Added custom code and workingdir commands.
* Added the console environment and associated options.
* Rewrote pythontex_utils*.py, creating a new, context-aware interface to
  SymPy's LatexPrinter class.
* Content brought in via macros no longer uses labels.  Rather, long defs
  are used, which allows line breaks.
* Pygments highlighting is now default for PythonTeX commands and environments.


v0.9beta2 (2012/05/09)

*  Changed Python output extension to .stdout.

v0.9beta (2012/04/27)

* Initial public beta release.

