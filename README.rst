===============================================
                  PythonTeX
===============================================

-----------------------------------------------
    Fast Access to Python from within LaTeX
-----------------------------------------------


:Author: Geoffrey Poore

:Version: 0.10beta2

:License:  LPPL_ (LaTeX code) and `BSD 3-Clause`_ (Python code)

.. _LPPL: http://www.latex-project.org/lppl.txt

.. _`BSD 3-Clause`: http://www.opensource.org/licenses/BSD-3-Clause


PythonTeX provides fast, user-friendly access to Python from within LaTeX.  It allows Python code entered within a LaTeX document to be executed, and the results to be included within the original document.  It also provides syntax highlighting for code within LaTeX documents via the Pygments package.

See ``pythontex.pdf`` for installation instructions.  See ``pythontex_gallery.pdf`` for examples of what is possible with PythonTeX.


Current status
--------------

The 0.10beta series will become the first full release with only minor tweaks 
by the end of January, unless major bugs are discovered.  As soon as the full 
release is out, PythonTeX will be submitted to CTAN.

Upcoming development will focus on ``depythontex``.


Version History
---------------

v0.10beta2 (2013/01/23)

* Improved ``pythontex*.py``'s handling of the name of the file being processed.  A warning is no longer raised if the name is given with an extension; extensions are now processed (stripped) automatically.  The filename may now contain a path to the file, so you need not run ``pythontex*.py`` from within the document's directory.
* Added command-line option ``--verbose`` for more verbose output.  Currently, this prints a list of all processes that are launched.
* Fixed a bug that could crash ``pythontex*.py`` when the package option ``pygments=false``.
* Added documentation about ``autoprint`` behavior in the preamble.  Summary:  ``code`` commands and environments are allowed in the preamble as of v0.10beta.  ``autoprint`` only applies to the body of the document, because nothing can be typeset in the preamble.  Content printed in the preamble can be brought in by explicitly using ``\printpythontex``, but this should be used with great care.
* Revised ``\stdoutpythontex`` and ``\printpythontex`` so that they work in the preamble.  Again, this should be used with great care if at all.
* Revised treatment of any content that custom code attempts to print.  Custom code is not allowed to print to the document (see documentation).  If custom code attempts to print, a warning is raised, and the printed content is included in the ``pythontex*.py`` run summary.
* One-line entries in stderr, such as those produced by Python's ``warnings.warn()``, were not previously parsed because they are of the form ``:<linenumber>:`` rather than ``line <linenumber>``.  These are now parsed and synchronized with the document.  They are also correctly parsed for inclusion in the document via ``\stderrpythontex``.
* If the package option ``stderrfilename`` is changed, all sessions that produced errors or warnings are now re-executed automatically, so that their stderr content is properly updated with the new filename.


v0.10beta (2013/01/09)

* Backward-incompatible: Redid treatment of command-line options for 
  ``pythontex*.py``, using Python's ``argparse`` module.  Run 
  ``pythontex*.py`` with option ``-h`` to see new command line options.
* Deprecated: ``\setpythontexcustomcode`` is deprecated in favor of the 
  ``\pythontexcustomc`` command and ``pythontexcustomcode`` 
  environment.  These allow entry of pure code, unlike 
  ``\setpythontexcustomcode``.  These also allow custom code to be 
  added to the beginning or end of a session, via an optional argument.
  Improved treatment of errors and warnings associated with custom 
  code.
* The summary of errors and warnings now correctly differentiates 
  errors and warnings produced by user code, rather than treating all 
  of them as errors.  By default, ``pythontex*.py`` now returns an 
  exit code of 1 if there were errors.
* The PythonTeX utilities class now allows external file dependencies 
  to be specified via ``pytex.add_dependencies()``, so that sessions 
  are automatically re-executed when external dependencies are 
  modified (modification is determined via either hash or mtime; this 
  is governed by the new ``hashdependencies`` option).
* The PythonTeX utilities class now allows created files to be 
  specified via ``pytex.add_created()``, so that created files may be 
  automatically cleaned up (deleted) when the code that created them 
  is modified (for example, name change for a saved plot).
* Added the following package options.

  - ``stdout`` (or ``print``): Allows input of stdout to be disabled.  
    Useful for debugging.
  - ``runall``: Executes everything.  Useful when code depends on 
    external data.
  - ``rerun``: Determines when code is re-executed.  Code may be set 
    to always run (same as ``runall`` option), or only run when it is 
    modified or when it produces errors or warnings.  By default, 
    code is always re-executed if there are errors or modifications, 
    but not re-executed if there are warnings.
  - ``hashdependencies``: Determines whether external dependencies 
    (data, external code files highlighted with Pygments, etc.) are 
    checked for modification via hashing or modification time.  
    Modification time is default for performance reasons.

* Added the following new command line options.  The options that are 
  equivalent to package options are overridden by the package options 
  when present.

  - ``--error-exit-code``:  Determines whether an exit code of 1 is 
    returned if there were errors.  On by default, but can be turned 
    off since it is undesirable when working with some editors.
  - ``--runall``: Equivalent to new package option.
  - ``--rerun``:  Equivalent to new package option.
  - ``--hashdependencies``:  Equivalent to new package option.

* Modified the ``fixlr`` option, so that it only patches commands if 
  they have not already been patched (avoids package conflicts).
* Added ``\setpythontexautoprint`` command for toggling autoprint 
  on/off within the body of the document.
* Installer now attempts to create symlinks under OS X and Linux with 
  TeX Live, and under OS X with MacPorts Tex Live.
* Performed compatibility testing under lualatex and xelatex 
  (previously, had only tested with pdflatex).  Added documentation 
  for using these TeX engines; at most, slightly different preambles 
  are needed.  Modified the PythonTeX gallery to support all three 
  engines.
* Code commands and environments may now be used in the preamble.  
  This, combined with the new treatment of custom code, allows 
  PythonTeX to be used in creating LaTeX packages.
* Added documentation for using PythonTeX in LaTeX programming.
* Fixed a bug that sometimes caused incorrect line numbers with 
  ``stderr`` content.  Improved processing of stderr.
* Fixed a bug in automatic detection of pre-existing listings 
  environment.
* Improved the detection of imports from ``__future__``.  Detection 
  should now be stricter, faster, and more accurate.


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

