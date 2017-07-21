|flattr|_

===============================================
                  PythonTeX
===============================================

-----------------------------------------------
    Fast Access to Python from within LaTeX
-----------------------------------------------


:Author: Geoffrey Poore

:Version: 0.16

:License:  LPPL_ (LaTeX code) and `BSD 3-Clause`_ (Python code)

.. _LPPL: http://www.latex-project.org/lppl.txt

.. _`BSD 3-Clause`: http://www.opensource.org/licenses/BSD-3-Clause



Overview
========

PythonTeX provides fast, user-friendly access to Python from within LaTeX.  It
allows Python code entered within a LaTeX document to be executed, and the
results to be included within the original document.  It also provides syntax
highlighting for code within LaTeX documents via the Pygments syntax
highlighter.

PythonTeX also provides support for Ruby, Julia, Octave, Sage, Bash, and Rust.
Support for additional languages is coming soon.

See ``pythontex_quickstart.pdf`` to get started, and ``pythontex_gallery.pdf``
for examples of what is possible with PythonTeX.  PythonTeX is included in
TeX Live and MiKTeX and may be installed via the package manager.  See
``pythontex.pdf`` for detailed installation instructions if you want to
install the current development version, or use the installation script for
TeX Live and MiKTeX.

The ``depythontex`` utility creates a copy of a PythonTeX document in which
all Python code has been replaced by its output.  This plain LaTeX document is
more suitable for journal submission, sharing, or conversion to other document
formats.  See ``pythontex_gallery.html`` and the accompanying conversion
script for an example of a PythonTeX document that was converted to HTML via
``depythontex`` and `Pandoc <http://johnmacfarlane.net/pandoc/>`_.



Citing PythonTeX
================

If you use PythonTeX in your writing and research, please consider citing it
in any resulting publications.  The best and most recent paper is in
`Computational Science & Discovery <http://stacks.iop.org/1749-4699/8/i=1/a=014010>`_ (doi:10.1088/1749-4699/8/1/014010).
You may also cite the paper in the
`2013 SciPy proceedings <http://conference.scipy.org/proceedings/scipy2013/poore.html>`_.



.. |flattr| image:: https://api.flattr.com/button/flattr-badge-large.png

.. _flattr: https://flattr.com/submit/auto?user_id=gpoore&url=https://github.com/gpoore/pythontex&title=pythontex&category=software
