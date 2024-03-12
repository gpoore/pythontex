===============================================
                  PythonTeX
===============================================

------------------------------------------------------------------------------------------
 Execute Python and other code in LaTeX documents, or typeset it with syntax highlighting
------------------------------------------------------------------------------------------


PythonTeX executes code in LaTeX documents and allows the output to be
included in the original document.  It supports Python as well as Bash,
JavaScript, Julia, Octave, Perl, R, Raku (Perl 6), Ruby, Rust, and SageMath.
PythonTeX also provides syntax highlighting for typeset code in LaTeX
documents via the `Pygments <https://pygments.org/>`_ syntax highlighter.

See ``pythontex_quickstart.pdf`` to get started, and ``pythontex_gallery.pdf``
for examples of what is possible with PythonTeX.  PythonTeX is included in TeX
Live and MiKTeX and may be installed via the package manager.  See
``pythontex.pdf`` for detailed installation instructions if you want to
install the current development version, or just use the installation script
for TeX Live and MiKTeX.

The ``depythontex`` utility creates a copy of a PythonTeX document in which
all code has been replaced by its output.  This plain LaTeX document is
more suitable for journal submission, sharing, or conversion to other document
formats.  See ``pythontex_gallery.html`` and the accompanying conversion
script for an example of a PythonTeX document that was converted to HTML via
``depythontex`` and `Pandoc <http://johnmacfarlane.net/pandoc/>`_.


Example
=======

*  LaTeX document ``doc.tex``:

   .. code-block:: latex

      \documentclass{article}

      \usepackage{pythontex}

      \newcommand{\pymultiply}[2]{\py{#1*#2}}

      \begin{document}

      \begin{pycode}
      print("Python says ``Hello!''")
      \end{pycode}

      $8 \times 256 = \pymultiply{8}{256}$

      \end{document}

*  Compiling under Windows:

   ::

      pdflatex -interaction=nonstopmode doc.tex
      pythontex doc.tex
      pdflatex -interaction=nonstopmode doc.tex


*  Compiling under other operating systems:

   ::

      pdflatex -interaction=nonstopmode doc.tex
      pythontex.py doc.tex
      pdflatex -interaction=nonstopmode doc.tex



*  Output:

   ::

      Python says “Hello!”
      8 × 256 = 2048

Notice that there is a three-step compile process.  This is what makes
possible commands like ``\pymultiply`` that use Python or other languages
internally.  You may want to configure your LaTeX editor with a shortcut for
running ``pythontex`` or ``pythontex.py``, or configure your LaTeX build
system to run ``pythontex`` or ``pythontex.py``.


Citing PythonTeX
================

If you use PythonTeX in your writing and research, please consider citing it
in any resulting publications.  The best and most recent paper is in
`Computational Science & Discovery <http://stacks.iop.org/1749-4699/8/i=1/a=014010>`_
(doi:10.1088/1749-4699/8/1/014010).  You may also cite the paper in the
`2013 SciPy proceedings <http://conference.scipy.org/proceedings/scipy2013/poore.html>`_.


Development status
==================

Starting in 2020, I have increasingly used Markdown and HTML instead of
PythonTeX and LaTeX when creating new teaching materials.  I can no longer
make major time investments in open-source software that I do not use
frequently myself.  PythonTeX v0.19 is under development.  It will address
some minor bugs and incompatibilities that have developed with Python and
dependencies over the last few years.  After v0.19, there should be occasional
releases to keep PythonTeX running, but no major changes or significant new
features are anticipated.

I have been developing `Codebraid <https://codebraid.org/>`_ since 2019,
partially to have a PythonTeX equivalent for Markdown but also in the hope
that it could eventually be integrated with LaTeX as a PythonTeX replacement.
I currently have a grant to develop
`minted <https://github.com/gpoore/minted>`_ v3.0, and as part of this am
creating new software for passing data between LaTeX and Python.  I cannot
make any guarantees, but I hope that this will eventually make it possible to
create a new LaTeX package based on Codebraid, with significant PythonTeX
compatibility.


License
=======

LPPL_ for LaTeX code and `BSD 3-Clause`_ for Python code.

.. _LPPL: http://www.latex-project.org/lppl.txt

.. _`BSD 3-Clause`: http://www.opensource.org/licenses/BSD-3-Clause
