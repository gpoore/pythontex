==================================================
                  PythonTeX News
==================================================


Version History
===============


v0.18 (2021/06/06)
------------------

*  ``\inputpygments`` now checks inputted files for modification, so that
   typeset code will correctly update when the source is changed (#162).

*  Julia now uses project flag "``--project=@.``" (#157, #158).

*  Fixed bug in processing Pygments options (``pygopt``) when a key is used
   without a value (#181).

*  Some error handling for Windows was incompatible with other operating
   systems: replaced checks for ``WindowsError`` with checks for ``OSError``
   (#177).

*  Rust support is now compatible with document and working directory paths
   that contain spaces (#167).



v0.17 (2019/09/22)
------------------

*  Pygments syntax highlighting for the Python console (``pycon`` lexer) now
   uses the ``python3`` option, and the default Python lexer is now
   ``python3`` (#156).

*  Added support for JavaScript (#147; thanks to Nathan Carter).

*  Updated Julia support for Julia versions 0.6 (#107), and 0.7 and 1.0 (#126,
   #130).

*  There are now meaningful error messages for the Julia console when Weave.jl
   is not installed or raises errors (#131).

*  ``pythontexcustomcode`` and ``\pythontexcustomc`` now set
   ``pytex.context`` (#65).

*  Added support for R.  The ``R`` family of commands and environments
   (``\R``, ``\Rc``, ``Rcode``, ...) executes code as a script.
   There is currently no utilities class or equivalent.  The ``Rcon`` family
   (``Rconsole``) executes code to emulate an interactive R session (#121).

*  ``fancyvrb`` settings from ``\setpythontexfv`` and console
   environments now work with Julia and R consoles.

*  ``pythontexcustomcode`` now works with ``juliacon``.  There are now proper
   ``juliaconcode`` and ``Rconcode`` environments that execute code but
   typeset nothing, to parallel ``pyconcode`` (#134).

*  Added support for Perl with the ``perl`` and ``pl`` families of commands
   and environments.  There is currently no utilities class or equivalent.

*  Added support for Perl 6 with the ``perlsix`` and ``psix`` families of
   commands and environments (#104).  There is currently no utilities class or
   equivalent.

*  Updated Rust support by using ``dyn`` with traits in utilities object.

*  Under Windows, capitalization of script paths in ``stderr`` is now
   preserved.

*  Fixed a bug that prevented the ``sub`` environment from working with
   ``depythontex`` (#155).

*  Fixed a bug in checking mtime of dependencies to see if they have been
   modified while ``pythontex`` is running.  The check failed for dependencies
   that do not exist or were deleted before ``pythontex`` can read them
   (#136).



v0.16 (2017/07/20)
------------------

*  Added preliminary console support for Julia (#98).

*  Fixed Python console compatibility with Python 3.6 by setting the ``code``
   module's new ``exitmsg`` argument to suppress the exit message (#100).

*  Improved Rust support, including tracking of created files and
   dependencies (#91).



v0.15 (2016/07/21)
------------------

New features
~~~~~~~~~~~~

*  The ``fvextra`` package is now required.  This provides line breaking with
   fine-grained control over break locations, the ability to highlight
   specific lines or ranges of lines, improved handling of tabs, and several
   additional features.

*  Added ``sub`` commands and environments (``\pys``, ``pysub``, ...).  These
   commands and environments perform string interpolation on text.  Fields
   delimited by ``!{...}`` are replaced by the result of evaluating and then
   printing their content.  This works for all families of commands and
   environments, not just Python.  See the documentation for details about
   field delimiters and escaping.

*  Added ``rust`` and ``rs`` families of commands and environments.  These
   provide essentially complete support for Rust, except that
   ``rstex.formatter()``, ``rstex.before()``, and ``rstex.after()`` will
   likely need additional refinement (#90).

*  Added the ``sage`` family of commands and environments, which provide
   support for Sage (#63).

*  Added ``bash`` family of commands and environments.  This provides basic
   support for bash (no utilities class or equivalent).  Bash works with
   Windows if it is installed.

*  Improved ``console`` compatibility under Linux with Python 3 (#70).

*  Counters for default sessions are now created automatically.  This prevents
   counter errors under some circumstances when working with ``\includeonly``.

*  Commands like ``\py`` can now output verbatim content under LuaTeX.

Bugfixes
~~~~~~~~

*  Fixed a bug that could cause an endless loop when a ``code`` command or
   environment printed a ``code`` command or environment of the same family
   with ``autoprint=true``.



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
   refer to the user�s home directory, even under Windows.

Bugfixes
~~~~~~~~

*  Fixed a bug that prevented created files from being cleaned up when
   the working directory was not the document root directory and the
   full path to the files was not provided.

*  Fixed a bug that prevented the ``fvextfile`` option from working when
   external files were highlighted.



v0.13-beta (2014/02/06)
-----------------------

New features
~~~~~~~~~~~~

*  Switching to GitHub's Releases for downloads.

*  TeX information such as page dimensions may now be easily passed to the
   programming-language side, using the new ``\setpythontexcontext`` command.
   Contextual information is stored in the ``context`` attribute of the
   utilities class, which is a dictionary (and also has attributes in Python).

*  The utilities class now has ``pt_to_in()``, ``pt_to_cm()``, and
   ``pt_to_mm()`` methods for converting units of TeX points into inches,
   centimeters, and millimeters.  These work with integers and floats, as
   well as strings that consist of numbers and optionally end in "pt".  There
   is also a ``pt_to_bp()`` for converting TeX points (1/72.27 inch) into big
   (DTP or PostScript) points (1/72 inch).

*  Expanded Quickstart.  Quickstart is now compatible with all LaTeX engines.
   Quickstart now avoids ``microtype`` issues on some systems (#32).

*  Added information on citing PythonTeX (#28).

*  Utilities class has a new attribute ``id``, which is a string that joins
   the command family name, session name, and session restart parameters with
   underscores.  This may be used in creating files that need a name that
   contains a unique, session-based identifier (for example, names for
   figures that are saved automatically).

Backward-incompatible changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

*  All utilities-class attributes with names of the form ``input_*`` have
   been renamed with the "``input_``" removed.  Among other things, this
   makes it easier to access the ``context`` attribute (``pytex.context``
   vs. ``pytex.input_context``).

*  ``depythontex`` now has ``-o`` and ``--output`` command-line options for
   specifying the name of the output file.  If an output file is not
   specified, then output is written to ``stdout``.  This allows
   ``depythontex`` output to be piped to another program.

*  All scripts ``*2.py`` now have shebangs with ``env python2``, and all
   scripts ``*3.py`` now have shebangs with ``env python3``.  This allows the
   wrapper scripts (``env python`` shebang) to be used with the default
   Python installation, and the numbered scripts to be used with specific
   versions.  Remember that except for console content, the ``--interpreter``
   option is what determines the Python version that actually executes code.
   The version of Python used to launch ``pythontex.py`` merely determines
   the version that manages code execution.  (``--interpreter`` support for
   console content is coming.)

*  Changed the template style used in the ``CodeEngine`` class.  Replacement
   fields are now surrounded by single curly braces (as in Python's format
   string syntax), rather than double curly braces.  Literal curly braces are
   obtained by doubling braces.  This allows the use of literal adjacent
   double braces in templates, which was not possible previously.

*  The Julia template now uses the new ``in()`` function, replacing
   ``contains()``.  This requires Julia v0.2.0+.

Bugfixes
~~~~~~~~

*  Modified test for LuaTeX, so that ``\directlua`` is not ``\let`` to
   ``\relax`` if it does not exist.  This was causing incompatibility with
   ``babel`` under pdfTeX and XeTeX (#33).

*  Added missing shebangs to ``depythontex*.py``.  Handling of ``utilspath``
   is now more forgiving, so that ``pythontex_utils.py`` can be installed in
   alternate locations (#23).

*  ``depythontex`` no longer leaves a blank line where
   ``\usepackage{pythontex}`` was removed.

*  Console environments typeset with ``fancyvrb`` no longer end with an
   unnecessary empty line.

*  Fixed bug in installer when ``kpsewhich`` was not found (#21).



v0.12 (2013/08/26)
------------------

*  Added support for the Julia language, with the ``julia`` and ``jl``
   families of commands and environments.  (Note that Pygments only added
   Julia support in version 1.6.)

*  Warnings and errors are now synchronized with the line numbers of files
   brought in via ``\input``, ``\include``, etc.  This is accomplished using
   the ``currfile`` package.

*  Added package option ``gobble``.  When ``gobble=auto``, all code is
   dedented before being executed and/or typeset.  The current
   implementation is functional but basic; it will be improved and extended
   in the future.

*  The document root directory is now always added to ``sys.path`` (or its
   equivalent), even when it is not the working directory. (The working
   directory has been added to ``sys.path`` since v0.12beta.)  The document
   directory is added after the working directory, so that the working
   directory has precedence.

*  Fixed a bug in ``console`` commands and environments; ``sys.path`` now
   contains the working and document directories, and the working directory
   is now the output directory by default.  This parallels the behavior of
   non-``console`` commands and environments.

*  Added command-line option ``--interpreter`` that allows an interpreter to
   be invoked via a specific command.  This allows, for example, a specific
   version of Python to be invoked.

*  Improved synchronization of stderr in cases when an error is triggered
   far after its origin (for example, an error caused by a multiline string
   that is lacking a closing quote/delimiter, and thus may span several
   chunks of user code).

*  Modified usage of the ``shlex`` module to work around its lack of Unicode
   support in Python versions prior to 2.7.3.

*  Fixed a bug from v0.12beta that prevented ``\inputpygments`` from working
   when ``pygments=true``.

*  Fixed a bug with counters that caused errors when content spanning
   multiple columns was created within a ``tabular`` environment.

*  Added checking for compatible Python versions in ``pythontex.py``.

*  Improved execution of ``*.bat`` and ``*.cmd`` files under Windows.  The
   solution from v0.12beta allowed ``*.bat`` and ``*.cmd`` to be found and
   executed when the extension was not given, but did not give correct
   return codes.


v0.12beta (2013/06/24)
----------------------

*  Merged ``pythontex_types*.py`` into a single replacement
   ``pythontex_engines.py`` compatible with both Python 2 and 3. It is
   now much simpler to add support for additional languages.

*  Added support for the Ruby language as a demonstration of new
   capabilities. The ``ruby`` and ``rb`` families of commands and
   environments may be enabled via the new ``usefamily`` package option.
   Support for additional languages is coming soon. See the new section
   in the documentation on support for other languages for more
   information.

*  Reimplemented treatment of Pygments content for better efficiency.
   Now a Pygments process only runs if there is content to highlight.
   Eliminated redundant highlighting of unmodified code.

*  Improved treatment of dependencies. If a dependency is modified
   (``os.path.getmtime()``) after the current PythonTeX run starts, then
   code that depends on it will be re-executed the next time PythonTeX
   runs. A message is also issued to indicate that this is the case.

*  The utilities class now has ``before()`` and ``after()`` methods that
   are called immediately before and after user code. These may be
   redefined to customize output. For example, LaTeX commands could be
   printed before and after user code; stdout could be redirected to
   ``StringIO`` for further processing; or matplotlib figures could be
   automatically detected, saved, and included in the document.

*  Added explanation of how to track dependencies and created files
   automatically, and how to include matplotlib figures automatically,
   to the documentation for the PythonTeX utilities class.

*  Created a new system for parsing and synchronizing stderr.

   -  Exceptions that do not reference a line number in user code (such
      as those from ``warnings.warn()`` in a module) are now traced back
      to a single command or environment. Previously no synchronization
      was attempted. This is accomplished by writing delimiters to
      stderr before executing the code from each command/environment.

   -  Exceptions that do reference a line in user code are more
      efficiently synchronized with a document line number. This is
      accomplished by careful record keeping as each script is
      assembled. Line number synchronization no longer involves parsing
      the script that was executed.

   -  Improved and generalized parsing of stderr, in preparation for
      supporting additional languages. Exceptions that cannot be
      identified as errors or warnings are treated based on
      ``Popen.returncode``.

*  Created a new system for ``console`` content.

   -  There are now separate families of ``console`` commands and
      environments. No Pygments or ``fancyvrb`` settings are shared with
      the non-``console`` families, as was previously the case. There
      is a new family of commands and environments based on ``pycon``,
      including the ``\pycon`` command (inline reference to console variable),
      ``pyconsole`` environment (same as the old one), ``\pyconc`` and
      ``pyconcode`` (execute only), and ``\pyconv`` and ``pyconverbatim``
      (typeset only). There are equivalent families based on
      ``pylabcon`` and ``sympycon``.

   -  Each console session now runs in its own process and is cached
      individually. Console output is now cached so that changing
      Pygments settings no longer requires re-execution.

   -  Unicode is now supported under Python 2.

   -  The new package option ``pyconfuture`` allows automatic imports
      from ``__future__`` for ``console`` families under Python 2,
      paralleling the ``pyfuture`` option.

   -  Any errors or warnings caused by code that is not typeset
      (``code`` command and environment, startup code) are reported in
      the run summary. This ensures that such code does not create
      mischief.

   -  ``customcode`` is now supported for ``console`` content.

*  Better support for ``latexmk`` and similar build tools. PythonTeX
   creates a file of macros (``*.pytxmcr``) that is always included in a
   document, and thus can be automatically detected and tracked by
   ``latexmk``. This file now contains the time at which PythonTeX last
   created files. When new files are created, the macro file will have a
   new hash, triggering another document compile.

*  Improved the way in which the PythonTeX ``outputdir`` is added to the
   graphics path. This had been done with ``\graphicspath``, but that
   overwrites any graphics path previously specified by the user. Now the
   ``outputdir`` is appended to any pre-existing path.

*  Added the ``depythontex`` option ``--graphicspath``. This adds the
   ``outputdir`` to the graphics path of the ``depythontex`` document.

*  The installer now provides more options for installation locations.
   It will now create missing directories if desired.

*  The working directory (``workingdir``) is now appended to
   ``sys.path``, so that code there may be imported.

*  Under Windows, ``subprocess.Popen()`` is now invoked with
   ``shell=True`` if ``shell=False`` results in a WindowsError. This
   allows commands involving ``*.bat`` and ``*.cmd`` files to be
   executed when the extension is not specified; otherwise, only ``*.exe``
   can be found and run.

*  The path to utils is now found in ``pythontex.py`` via
   ``sys.path[0]`` rather than ``kpsewhich``. This allows the PythonTeX
   scripts to be executed in an arbitrary location; they no longer must
   be installed in a texmf tree where ``kpsewhich`` can find them.

*  Added ``rerun`` value ``never``.

*  At the end of each run, data and macros are only saved if modified,
   improving efficiency.

*  The number of temporary files required by each process was reduced by
   one. All macros for commands like ``\py`` are now returned within
   stdout, rather than in their own file.

*  Fixed a bug with ``\stderrpythontex``; it was defaulting to ``verb``
   rather than ``verbatim`` mode.


v0.11 (2013/04/21)
------------------

* As the first non-beta release, this version adds several features and introduces several changes.  You should read these release notes carefully, since some changes are not backwards-compatible.  Changes are based on a thorough review of all current and planned features.  PythonTeX's capabilities have already grown beyond what was originally intended, and a long list of features still remains to be implemented.  As a result, some changes are needed to ensure consistent syntax and naming in the future.  Insofar as possible, all command names and syntax will be frozen after this release.
* Added the ``pythontex.py`` and ``depythontex.py`` wrapper scripts.  When run, these detect the current version of Python and import the correct PythonTeX code.  It is still possible to run ``pythontex*.py`` and ``depythontex*.py`` directly, but the new wrapper scripts should be used instead for simplicity.  There is now only a single ``pythontex_utils.py``, which works with both Python 2 and Python 3.
* Added the ``beta`` package option.  This makes the current version behave like v0.11beta, for compatibility.  This option is temporary and will probably only be retained for a few releases.
* Backward-incompatible changes (require the ``beta`` option to restore old behavior)

  - The ``pyverb`` environment has been renamed ``pyverbatim``.  The old name was intended to be concise, but promoted confusion with LaTeX's ``\verb`` macro.
  - For ``\printpythontex``, ``\stdoutpythontex``, and ``\stderrpythontex``, the modes ``inlineverb`` and ``v`` have been replaced by ``verb``, and the old mode ``verb`` has been replaced by ``verbatim``.  This brings naming conventions in line with standard LaTeX ``\verb`` and ``verbatim``, avoiding a source of potential confusion.
  - The ``\setpythontexpyglexer``, ``\setpythontexpygopt``, and ``\setpygmentspygopt`` commands now take an optional argument and a mandatory argument, rather than two mandatory arguments.  This creates better uniformity among current and planned settings macros.
  - The ``\setpythontexformatter`` and ``\setpygmentsformatter`` commands have been replaced by the ``\setpythontexprettyprinter`` and ``\setpygmentsprettyprinter`` commands.  This anticipates possible upcoming features.  It also avoids potential confusion with Pygments's formatters and the utilities class's ``formatter()`` method.

* Deprecated (still work, but raise warnings; after a few releases, they will raise errors instead, and after that eventually be removed)

  - The ``rerun`` setting ``all`` was renamed ``always``, in preparation for upcoming features.
  - The ``stderr`` option is replaced by ``makestderr``.  The ``print``/``stdout`` option is replaced by ``debug``.  These are intended to prevent confusion with future features.
  - The ``fixlr`` option is deprecated.  It was originally introduced to deal with some of SymPy's LaTeX formatting, which has since changed.
  - The utilities class method ``init_sympy_latex()`` is deprecated.  The ``sympy_latex()`` and ``set_sympy_latex()`` methods now automatically initialize themselves on first use.

* Added ``autostdout`` package option and ``\setpythontexautostdout``, to complement ``autoprint``.  Added ``prettyprinter`` and ``prettyprintinline`` package options to complement new settings commands.
* Added quickstart guide.
* Installer now installs gallery and quickstart files, if present.


v0.11beta (2013/02/17)
----------------------

* Commands like ``\py`` can now bring in any valid LaTeX code, including verbatim content, under the pdfTeX and XeTeX engines.  Verbatim content was not allowed previously.  LuaTeX cannot bring in verbatim, due to a known bug.
* Added package option ``depythontex`` and scripts ``depythontex*.py``.  These allow a PythonTeX document to be converted into a pure LaTeX document, with no Python dependency.  The package option creates an auxiliary file with extension ``.depytx``.  The ``depythontex*.py`` scripts take this auxiliary file and the original LaTeX document, and combine the two to produce a new document that does not rely on the PythonTeX package.  All PythonTeX commands and environments are replaced by their output.   All Python-generated content is substituted directly into the document.  By default, all typeset code is wrapped in ``\verb`` and ``verbatim``, but ``depythontex*.py`` has a ``--listing`` option that allows ``fancyvrb``, ``listings``, ``minted``, or ``pythontex`` to be used instead.
* The current PythonTeX version is now saved in the ``.pytxcode``.  If this does not match the version of the PythonTeX scripts, a warning is issued.  This makes it easier to determine errors due to version mismatches.
* Fixed an incompatibility with the latest release of ``xstring`` (version 1.7, 2013/01/13).
* Fixed a bug in the ``console`` environment that could cause problems when switching from Pygments highlighting to ``fancyvrb`` when using the ``fvextfile`` option.  Fixed a bug introduced in the v0.10beta series that prevented the ``console`` environment from working with ``fancyvrb``.
* Fixed a bug with PythonTeX verbatim commands and environments that use Pygments.  The verbatim commands and environments were incorrectly treated as if they had the attributes of executed code in the v0.10beta series.
* Fixed a bug from the v0.10beta series that sometimes prevented imports from ``__future__`` from working when there were multiple sessions.
* Fixed a bug related to hashing dependencies' mtime under Python 3.


v0.10beta2 (2013/01/23)
-----------------------

* Improved ``pythontex*.py``'s handling of the name of the file being processed.  A warning is no longer raised if the name is given with an extension; extensions are now processed (stripped) automatically.  The filename may now contain a path to the file, so you need not run ``pythontex*.py`` from within the document's directory.
* Added command-line option ``--verbose`` for more verbose output.  Currently, this prints a list of all processes that are launched.
* Fixed a bug that could crash ``pythontex*.py`` when the package option ``pygments=false``.
* Added documentation about ``autoprint`` behavior in the preamble.  Summary:  ``code`` commands and environments are allowed in the preamble as of v0.10beta.  ``autoprint`` only applies to the body of the document, because nothing can be typeset in the preamble.  Content printed in the preamble can be brought in by explicitly using ``\printpythontex``, but this should be used with great care.
* Revised ``\stdoutpythontex`` and ``\printpythontex`` so that they work in the preamble.  Again, this should be used with great care if at all.
* Revised treatment of any content that custom code attempts to print.  Custom code is not allowed to print to the document (see documentation).  If custom code attempts to print, a warning is raised, and the printed content is included in the ``pythontex*.py`` run summary.
* One-line entries in stderr, such as those produced by Python's ``warnings.warn()``, were not previously parsed because they are of the form ``:<linenumber>:`` rather than ``line <linenumber>``.  These are now parsed and synchronized with the document.  They are also correctly parsed for inclusion in the document via ``\stderrpythontex``.
* If the package option ``stderrfilename`` is changed, all sessions that produced errors or warnings are now re-executed automatically, so that their stderr content is properly updated with the new filename.


v0.10beta (2013/01/09)
----------------------

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
----------------------

*  Added Unicode support, which required the Python code to be split into
   one set for Python 2 and another set for Python 3.  This will require
   any old installation to be completely removed, and a new installation
   created from scratch.
*  Refactoring of Python code.  Documents should automatically re-execute
   all code after updating to the new version.  Otherwise, you should delete
   the PythonTeX directory and run PythonTeX.
*  Improved installation script.
*  Added package options:  ``pyfuture``, ``stderr``, ``upquote``,
   ``pyglexer``, ``pyginline``.  Renamed the ``pygextfile`` option to
   ``fvextfile``.
*  Added custom code and workingdir commands.
*  Added the ``console`` environment and associated options.
*  Rewrote ``pythontex_utils*.py``, creating a new, context-aware interface to
   SymPy's LatexPrinter class.
*  Content brought in via macros no longer uses labels.  Rather, long defs
   are used, which allows line breaks.
*  Pygments highlighting is now default for PythonTeX commands and environments.


v0.9beta2 (2012/05/09)
----------------------

*  Changed Python output extension to ``.stdout``.


v0.9beta (2012/04/27)
---------------------

*  Initial public beta release.
