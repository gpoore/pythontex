#!/usr/bin/env python2
# -*- coding: utf-8 -*-

'''
PythonTeX depythontex script.

This script takes a LaTeX document that uses the PythonTeX package and
creates a new document that does not depend on PythonTeX.  It substitutes all
externally generated content into a copy of the original LaTeX document.
This is useful when you need a document that relies on few external packages
or custom macros (for example, for submission to a journal or conversion to
another document format).

If you just want to share a document that uses PythonTeX, keep in mind that
the document can be modified and compiled just like a regular LaTeX document,
without needing Python or any other external tools, so long as the following
conditions are met:

  * A copy of pythontex.sty is included with the document.
  * The pythontex-files-<name> directory is included with the document.
  * The PythonTeX-specific parts of the document are not modified.

To work, this script requires that the original LaTeX document be compiled
with the package option `depythontex`.  That creates an auxiliary file with
the extension .depytx that contains information about all content that needs
to be substituted.

This script is purposely written in a simple, largely linear form to
facilitate customization.  Most of the key substitutions are performed by a
few functions defined near the beginning of the script, so if you need custom
substitutions, you should begin there.  By default, all typeset code is
wrapped in `\verb` commands and verbatim environments, since these have the
greatest generality.  However, the command-line option --listing allows code
to be typeset with the fancyvrb, listings, minted, or PythonTeX packages
instead.

The script automatically extracts all arguments of all commands and
environments that it replaces, so that these are available if desired for
customized substitution.  Two additional pieces of information are also
available for any typeset code:  the Pygments lexer (often the same as the
language) and the starting line number (if line numbering was used).

Keep in mind that some manual adjustments may be required after a document is
depythontex'ed.  While depythontex attempts to create an exact copy of the
original document, in many cases an identical copy is impossible.  For
example, typeset code may have a different appearance or layout when it is
typeset with a different package.


Copyright (c) 2013-2021, Geoffrey M. Poore
All rights reserved.
Licensed under the BSD 3-Clause License:
    http://www.opensource.org/licenses/BSD-3-Clause

'''


# Imports
#// Python 2
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
#\\ End Python 2
import sys
import os
#// Python 2
if sys.version_info.major != 2:
    sys.exit('This version of the PythonTeX script requires Python 2.')
#\\ End Python 2
#// Python 3
#if sys.version_info.major != 3:
#    sys.exit('This version of the PythonTeX script requires Python 3.')
#\\ End Python 3

#// Python 2
from io import open
input = raw_input
#\\ End Python 2
import argparse
from collections import defaultdict
from re import match, sub, search
import textwrap
import codecs


# Script parameters
# Version
__version__ = '0.18'


# Functions and parameters for customizing the script output

# Style or package for replacing code listings
# This is actually set via command-line option --listing
# It is created here simply for reference
listing = None  #'verbatim', 'fancyvrb', 'listings', 'minted', 'pythontex'

# List of things to add to the preamble
# It can be appended to via the command-line option --preamble
# It is also appended to based on the code listing style that is used
# And it could be manually edited here as well, as long as it remains a list
preamble_additions = list()

# Lexer dict
# If you are using Pygments lexers that don't directly correspond to the
# languages used by the listings package, you can submit replacements via the
# command line option --lexer-dict, or edit this dict manually here.  When
# listings is used, all lexers are checked against this dict to see if a
# substitution should be made.  This approach could easily be modified to
# work with another, non-Pygments highlighting package.
lexer_dict = dict()


def replace_code_cmd(name, arglist, linenum, code_replacement,
                     code_replacement_mode, after, lexer, firstnumber):
    '''
    Typeset code from a command with a command.

    It is only ever called if there is indeed code to typeset.

    Usually, code from a command is also typeset with a command.  This
    function primarily deals with that case.  In cases where code from a
    command is typeset with an environment (for example, `\inputpygments`),
    this function performs some preprocessing and then uses
    replace_code_env() to do the real work.  This approach prevents the two
    functions from unnecessarily duplicating each other, while still giving
    the desired output.

    Args:
        name (str):  name of the command
        arglist (list, of str/None):  all arguments given to the original
            command; the last argument is what is typeset, unless a
            code_replacement is specified or other instructions are given
        linenum (int):  line number in the original TeX document
        code_replacement (str/None):  replacement for the code; usually None
            for commands, because typically the code to be typeset is the
            last argument passed to the command, rather than something
            captured elsewhere (like the body of an environment) or something
            preprocessed (like a console environment's content)
        code_replacement_mode (str/None):  mode in which the replacement is
            to be typeset; raw/None (as TeX; generally unused for code),
            verb (inline), or verbatim (environment)
        after (str):  text immediately following the command; usually
            shouldn't be needed
        lexer (str/None):  Pygments lexer
    Returns:
        (replacement, after) (tuple, of str)

    '''
    # Get the correct replacement
    if code_replacement is None:
        code_replacement = arglist[-1]

    # We only consider two possible modes of typesetting, verbatim and inline
    # verbatim
    if code_replacement_mode == 'verbatim':
        # Sometimes we must replace a command with an environment, for
        # example, for `\inputpygments`

        # Make sure the introduction of an environment where a command was
        # previously won't produce errors with following content; make sure
        # that any following content is on a separate line
        if bool(match('[ \t]*\S', after)):
            after = '\n' + after
        # Rather than duplicating much of replace_code_env(), just use it
        return replace_code_env(name, arglist, linenum, code_replacement,
                                code_replacement_mode, after, lexer, firstnumber)
    else:
        # Usually, we're replacing a command with a command

        # Wrap the replacement in appropriate delimiters
        if (listing in ('verbatim', 'fancyvrb', 'minted') or
                (listing in ('listings', 'pythontex') and
                ('{' in code_replacement or '}' in code_replacement))):
            for delim in ('|', '/', '`', '!', '&', '#', '@', ':', '%', '~', '$',
                          '=', '+', '-', '^', '_', '?', ';'):
                if delim not in code_replacement:
                    break
            code_replacement = delim + code_replacement + delim
        else:
            code_replacement = '{' + code_replacement + '}'
        # Assemble the actual replacement
        if listing in ('verbatim', 'minted'): # `\mint` isn't for inline use
            code_replacement = r'\verb' + code_replacement
        elif listing == 'fancyvrb':
            code_replacement = r'\Verb' + code_replacement
        elif listing == 'listings':
            if lexer is None:
                code_replacement = r'\lstinline[language={}]' + code_replacement
            else:
                if lexer in lexer_dict:
                    lexer = lexer_dict[lexer]
                code_replacement = r'\lstinline[language=' + lexer + ']' + code_replacement
        elif listing == 'pythontex':
            if lexer is None:
                code_replacement = r'\pygment{text}' + code_replacement
            else:
                code_replacement = r'\pygment{' + lexer + '}' + code_replacement
        return (code_replacement, after)


def replace_code_env(name, arglist, linenum, code_replacement,
                     code_replacement_mode, after, lexer, firstnumber):
    '''
    Typeset code from an environment with an environment.

    It is only ever called if there is indeed code to typeset.

    Usually it is only used to typeset code from an environment.  However,
    some commands bring in code that must be typeset as an environment.  In
    those cases, replace_code_cmd() is called initially, and after it
    performs some preprocessing, this function is called.  This approach
    avoids unnecessary duplication between the two functions.

    Args:
        name (str):  name of the environment
        arglist (list, of str/None):  all arguments given to the original
            environment
        linenum (int):  line number in the original TeX document where
            the environment began
        code_replacement (str):  replacement for the code; unlike the case of
            commands, this is always not None if the function is called
        code_replacement_mode (str/None):  mode in which the replacement is
            to be typeset; raw/None (as TeX; generally unused for code),
            verb (inline), or verbatim (environment)
        after (str):  text immediately following the environment; usually
            shouldn't be needed
        lexer (str/None):  Pygments lexer
        firstnumber (str/None):  the first number of the listing, if the listing
            had numbered lines
    Returns:
        (replacement, after) (tuple, of str)

    '''
    # Currently, there is no need to test for code_replacement_mode, because
    # this function is only ever called if the mode is 'verbatim'.  That may
    # change in the future, but it seems unlikely that code entered in an
    # environment would end up typeset with a command.
    if listing == 'verbatim':
        pre = '\\begin{verbatim}'
        post = '\\end{verbatim}'
    elif listing == 'fancyvrb':
        if firstnumber is None:
            pre = '\\begin{Verbatim}'
        else:
            pre = '\\begin{{Verbatim}}[numbers=left,firstnumber={0}]'.format(firstnumber)
        post = '\\end{Verbatim}'
    elif listing == 'listings':
        if lexer is None:
            if firstnumber is None:
                pre = '\\begin{lstlisting}[language={}]'
            else:
                pre = '\\begin{{lstlisting}}[language={{}},numbers=left,firstnumber={0}]'.format(firstnumber)
        else:
            if lexer in lexer_dict:
                lexer = lexer_dict[lexer]
            if firstnumber is None:
                pre = '\\begin{{lstlisting}}[language={0}]'.format(lexer)
            else:
                pre = '\\begin{{lstlisting}}[language={0},numbers=left,firstnumber={1}]'.format(lexer, firstnumber)
        post = '\\end{lstlisting}'
    elif listing == 'minted':
        if lexer is None:
            if firstnumber is None:
                pre = '\\begin{minted}{text}'
            else:
                pre = '\\begin{{minted}}[linenos,firstnumber={0}]{{text}}'.format(firstnumber)
        else:
            if firstnumber is None:
                pre = '\\begin{{minted}}{{{0}}}'.format(lexer)
            else:
                pre = '\\begin{{minted}}[linenos,firstnumber={0}]{{{1}}}'.format(firstnumber, lexer)
        post = '\\end{minted}'
    elif listing == 'pythontex':
        if lexer is None:
            if firstnumber is None:
                pre = '\\begin{pygments}{text}'
            else:
                pre = '\\begin{{pygments}}[numbers=left,firstnumber={0}]{{text}}'.format(firstnumber)
        else:
            if firstnumber is None:
                pre = '\\begin{{pygments}}{{{0}}}'.format(lexer)
            else:
                pre = '\\begin{{pygments}}[numbers=left,firstnumber={0}]{{{1}}}'.format(firstnumber, lexer)
        post = '\\end{pygments}'
    code_replacement = pre + code_replacement + post
    return (code_replacement, after)


# We will need to issue a warning every time that a substitution of printed
# content results in a forced double space.  We could just do this as we go,
# but it's easier for the user to read if we just collect all the warnings
# of this type, and print them once.
forced_double_space_list = list()


def replace_print_cmd(name, arglist, linenum,
                      print_replacement, print_replacement_mode, source,
                      after):
    '''
    Typeset printed content from a command.

    It is only ever called if there is indeed printed content to typeset.

    Args:
        name (str):  name of the command
        arglist (list, of str/None):  all arguments given to the original
            command
        linenum (int):  line number in the original TeX document
        print_replacement (str):  printed content, read directly from file
            into a single string
        print_replacement_mode (str/None):  mode in which the replacement is
            to be typeset; raw/None (as TeX), inlineverb (or v) (as inline),
            or verb (as environment)
        source (str/None):  source of the replacement content
        after (str):  text immediately following the command; important in
            some situations, because spacing can depend on what's next
    Returns:
        (replacement, after) (tuple, of str)

    '''
    if print_replacement_mode == 'verb':
        if print_replacement.count('\n') > 1:
            print('* DePythonTeX error:')
            print('    Attempt to print multiple lines of content near line ' + str(linenum))
            print('    This is not possible in inline verbatim mode')
            sys.exit(1)
        print_replacement = print_replacement.rstrip('\n')
        for delim in ('|', '/', '`', '!', '&', '#', '@', ':', '%', '~', '$',
                      '=', '+', '-', '^', '_', '?', ';'):
            if delim not in print_replacement:
                break
        print_replacement = r'\verb' + delim + print_replacement + delim
    elif print_replacement_mode == 'verbatim':
        if bool(match('\s*?\n', after)):
            # Usually, we would end the verbatim environment with a newline.
            # This is fine if there is content in `after` before the next
            # newline---in fact, it's desirable, because the verbatim package
            # doesn't allow for content on the same line as the end of the
            # environment.  But if `after` is an empty line, then adding a
            # newline will throw off spacing and must be avoided
            print_replacement = '\\begin{verbatim}\n' + print_replacement + '\\end{verbatim}'
        else:
            print_replacement = '\\begin{verbatim}\n' + print_replacement + '\\end{verbatim}\n'
    else:
        # When printed content from a file is included as LaTeX code, we have
        # to be particularly careful to ensure that the content produces the
        # same output when substituted as when brought in by `\input`.  In
        # particular, `\input` strips newlines from each line of content and
        # adds a space at the end of each line.  This space is inside the
        # `\input`, so it will not merge with following spaces.  So when we
        # substitute the content, sometimes we need to replace the final
        # newline with a space that cannot be gobbled.
        #
        # It gets more complicated.  This final space is often not
        # desirable.  It can be prevented by either printing an `\endinput`
        # command, to terminate the `\input`, or printing a percent
        # character % in the last line of the content, which comments out the
        # final newline.  So we must check for `\endinput` anywhere in
        # printed content, and % in the final line, and remove any content
        # after them.  It's also possible that the print is followed by
        # an `\unskip` that eats the space, so we need to check for that too.
        #
        # It turns out that the same approach is needed when a command like
        # `\py` brings in content ending in a newline
        if (print_replacement.endswith('\\endinput\n') and
                not print_replacement.endswith('\\string\\endinput\n')):
            # If `\endinput` is present, everything from it on should be
            # discarded, unless the `\endinput` is not actually a command
            # but rather a typeset name (for example, `\string\endinput` or
            # `\verb|\endinput|`).  It's impossible to check for all cases in
            # which `\endinput` is not a command (at least, without actually
            # using LaTeX), and even checking for most of them would require
            # a good bit of parsing.  We assume that `\endinput`, as a
            # command, will only ever occur at the immediate end of the
            # printed content.  Later, we issue a warning in case it appears
            # anywhere else.
            print_replacement = print_replacement.rsplit(r'\endinput', 1)[0]
        elif (print_replacement.endswith('%\n') and
                not print_replacement.endswith('\\%\n') and
                not print_replacement.endswith('\\string%\n')):
            # Perform an analogous check for a terminating percent characer %.
            # This case would be a bit easier to parse fully, since a percent
            # that comments out the last newline would have to be in the
            # final line of the replacement.  But it would still be
            # very difficult to perform a complete check.  Later, we issue a
            # warning if there is reason to think that a percent character
            # was active in the last line.
            print_replacement = print_replacement.rsplit(r'%', 1)[0]
        elif print_replacement.endswith('\n'):
            # We can't just use `else` because that would catch content
            # from `\py` and similar
            # By default, LaTeX strips newlines and adds a space at the end
            # of each line of content that is brought in by `\input`.  This
            # may or may not be desirable, but we replicate the effect here
            # for consistency with the original document.  We use `\space{}`
            # because plain `\space` would gobble a following space, which
            # isn't consistent with the `\input` behavior being replicated.
            if bool(match(r'\\unskip\s+\S', after)):
                # If there's an `\unskip`, fix the spacing and remove the
                # `\unskip`.  Since this is inline, the `\unskip` must
                # immediately follow the command to do any good; otherwise,
                # it eliminates spaces that precede it, but doesn't get into
                # the `\input` content.
                print_replacement = print_replacement.rstrip(' \t\n')
                after = sub(r'^\\unskip\s+', '', after)
            elif bool(match('\S', after)):
                # If the next character is not whitespace, we can just leave
                # the `\n`, and it will yield a space.
                pass
            elif bool(match('\s*$', after)):
                # If the rest of the current line, and the next line, are
                # whitespace, we will get the correct spacing without needing
                # `\space{}`.  We could leave `\n`, but it would be
                # extraneous whitespace.
                print_replacement = print_replacement[:-1]
            else:
                # Otherwise, we do need to insert `\space{}`
                # We keep the newline at the end of printed content, in case
                # it's at the end of an environment, and thus is needed to
                # protect the following content
                print_replacement += '\\space{}'
                after = sub('^\s+', '', after)
                forced_double_space_list.append((name, linenum))
        else:
            if bool(match('\s+\S', after)):
                # If the following line starts with whitespace, replace it
                # with a newline, to protect in the event that the printed
                # content ended with an end-of-environment command
                after = sub('^\s+', '\n', after)
        # Issue warnings, if warranted
        # Warn about `\endinput`
        if (r'\endinput' in print_replacement and
                print_replacement.count(r'\endinput') != print_replacement.count(r'\string\endinput')):
            print('* DePythonTeX warning:')
            print('    "\\endinput" was present in printed content near line ' + str(linenum))
            print('    If this "\\endinput" was verbatim, you have nothing to worry about')
            print('    If this "\\endinput" is to be active, it should be printed last')
            print('    If you need "\\endinput" elsewhere, customize depythontex.py')
        # Warn if it looks like there are active `%` that could comment
        # out part of the original document.  We only need to check the
        # last line of printed content, because only there could
        # percent characters escape from their original confines within
        # `\input`, and comment out part of the document.
        if print_replacement.endswith('\n'):
            if print_replacement.count('\n') > 1:
                last_line = print_replacement.rsplit('\n', 2)[1]
            else:
                last_line = print_replacement
            if last_line.count('%') != last_line.count(r'\%') + last_line.count(r'\string%'):
                print('* DePythonTeX warning:')
                print('    One or more percent characters are on the last line of ')
                print('    printed content near line ' + str(linenum))
                print('    If they are not verbatim, they could comment out the following newline')
        else:
            if '\n' in print_replacement:
                last_line = print_replacement.rsplit('\n', 1)[1]
            else:
                last_line = print_replacement
            if last_line.count('%') != last_line.count(r'\%') + last_line.count(r'\string%'):
                print('* DePythonTeX warning:')
                print('    One or more percent characters are on the last line of ')
                print('    printed content near line ' + str(linenum))
                print('    If they are not verbatim, they could comment out the following text')
        # Warn if there were `\unskip`'s in the output, in case they weren't
        # positioned correctly
        if bool(match(r'\s*\\unskip', after)):
            print('* DePythonTeX warning:')
            print('    "\\unskip" survived substitution near line ' + str(linenum))
            print('    If it should have adjusted the spacing of printed content')
            print('    you should double-check the spacing')
    return (print_replacement, after)


def replace_print_env(name, arglist, linenum,
                      print_replacement, print_replacement_mode, source,
                      after):
    '''
    Typeset printed content from an environment.

    It is only ever called if there is indeed printed content to typeset.

    This should be similar to replace_print_cmd().  The main difference is
    that the environment context typically ends with a newline, so
    substitution has to be a little different to ensure that spacing after
    the environment isn't modified.

    Args:
        name (str):  name of the environment
        arglist (list, of str/None):  all arguments given to the original
            environment
        linenum (int):  line number in the original TeX document where the
            environment began
        print_replacement (str):  printed content, read directly from file
            into a single string
        print_replacement_mode (str/None):  mode in which the replacement is
            to be typeset; raw/None (as TeX), inlineverb (or v) (as inline),
            or verb (as environment)
        source (str/None):  source of the replacement content
        after (str):  text immediately following the command; important in
            some situations, because spacing can depend on what's next
    Returns:
        (replacement, after) (tuple, of str)

    #### The inlineverb and verb modes should work, but haven't been tested
    since there are currently no environments that use them; they are only
    used by `\printpythontex`, which is a command.
    '''
    if print_replacement_mode == 'verb':
        if print_replacement.count('\n') > 1:
            print('* DePythonTeX error:')
            print('    Attempt to print multiple lines of content near line ' + str(linenum))
            print('    This is not possible in inline verbatim mode')
            sys.exit(1)
        print_replacement = print_replacement.rstrip('\n')
        for delim in ('|', '/', '`', '!', '&', '#', '@', ':', '%', '~', '$',
                      '=', '+', '-', '^', '_', '?', ';'):
            if delim not in print_replacement:
                break
        print_replacement = r'\verb' + delim + print_replacement + delim
        if not bool(match('[ \t]+\S', after)):
            # If there is text on the same line as the end of the
            # environment, we're fine (this is unusual).  Otherwise,
            # we need to toss the newline at the end of the environment
            # and gobble leading spaces.  Leading spaces need to be
            # gobbled because previously they were at the beginning of a
            # line, where they would have been discarded.
            if not bool(match('\s*$', after)):
                after = sub('^\s*?\n\s*', '', after)
    elif print_replacement_mode == 'verbatim':
        if bool(match('\s*?\n', after)):
            # Usually, we would end the verbatim environment with a newline.
            # This is fine if there is content in `after` before the next
            # newline---in fact, it's desirable, because the verbatim package
            # doesn't allow for content on the same line as the end of the
            # environment.  But if `after` is an empty line, then adding a
            # newline will throw off spacing and must be avoided
            print_replacement = '\\begin{verbatim}\n' + print_replacement + '\\end{verbatim}'
        else:
            print_replacement = '\\begin{verbatim}\n' + print_replacement + '\\end{verbatim}\n'
    else:
        # When printed content is included as LaTeX code, we have to be
        # particularly careful to ensure that the content produces the same
        # output when substituted as when brought in by `\input`.  In
        # particular, `\input` strips newlines from each line of content and
        # adds a space at the end of each line.  This space is inside the
        # `\input`, so it will not merge with following spaces.  So when we
        # substitute the content, sometimes we need to replace the final
        # newline with a space that cannot be gobbled.
        #
        # It gets more complicated.  This final space is often not
        # desirable.  It can be prevented by either printing an `\endinput`
        # command, to terminate the `\input`, or printing a percent
        # character % in the last line of the content, which comments out the
        # final newline.  So we must check for `\endinput` anywhere in
        # printed content, and % in the final line, and remove any content
        # after them.  It's also possible that the print is followed by
        # an `\unskip` that eats the space, so we need to check for that too.
        if (print_replacement.endswith('\\endinput\n') and
                not print_replacement.endswith('\\string\\endinput\n')):
            # If `\endinput` is present, everything from it on should be
            # discarded, unless the `\endinput` is not actually a command
            # but rather a typeset name (for example, `\string\endinput` or
            # `\verb|\endinput|`).  It's impossible to check for all cases in
            # which `\endinput` is not a command (at least, without actually
            # using LaTeX), and even checking for most of them would require
            # a good bit of parsing.  We assume that `\endinput`, as a
            # command, will only ever occur at the immediate end of the
            # printed content.  Later, we issue a warning in case it appears
            # anywhere else.
            print_replacement = print_replacement.rsplit(r'\endinput', 1)[0]
            if not bool(match('[ \t]+\S', after)):
                # If there is text on the same line as the end of the
                # environment, we're fine (this is unusual).  Otherwise,
                # we need to toss the newline at the end of the environment
                # and gobble leading spaces.  Leading spaces need to be
                # gobbled because previously they were at the beginning of a
                # line, where they would have been discarded.
                if not bool(match('\s*$', after)):
                    after = sub('^\s*?\n\s*', '', after)
        elif (print_replacement.endswith('%\n') and
                not print_replacement.endswith('\\%\n') and
                not print_replacement.endswith('\\string%\n')):
            # Perform an analogous check for a terminating percent characer %.
            # This case would be a bit easier to parse fully, since a percent
            # that comments out the last newline would have to be in the
            # final line of the replacement.  But it would still be
            # very difficult to perform a complete check.  Later, we issue a
            # warning if there is reason to think that a percent character
            # was active in the last line.
            print_replacement = print_replacement.rsplit(r'%', 1)[0]
            if not bool(match('[ \t]+\S', after)):
                # If there is text on the same line as the end of the
                # environment, we're fine (this is unusual).  Otherwise,
                # we need to toss the newline at the end of the environment
                # and gobble leading spaces.  Leading spaces need to be
                # gobbled because previously they were at the beginning of a
                # line, where they would have been discarded.
                if not bool(match('\s*$', after)):
                    after = sub('^\s*?\n\s*', '', after)
        else:
            # By default, LaTeX strips newlines and adds a space at the end
            # of each line of content that is brought in by `\input`.  This
            # may or may not be desirable, but we replicate the effect here
            # for consistency with the original document.  We use `\space{}`
            # because plain `\space` would gobble a following space, which
            # isn't consistent with the `\input` behavior being replicated.
            if bool(match(r'\s*\\unskip\s+\S', after)):
                # If there's an `\unskip`, fix the spacing and remove the
                # `\unskip`
                print_replacement = print_replacement.rstrip(' \t\n')
                after = sub(r'^\s*\\unskip\s+', '', after)
            elif bool(match('[ \t]+\S', after)):
                # If the next character after the end of the environment is
                # not whitespace (usually not allowed), we can just leave
                # the `\n` in printed content, and it will yield a space.
                # So we need do nothing.  But if there is text on that line
                # we need `\space{}`.
                after = sub('^\s+', '\\space', after)
                forced_double_space_list.append((name, linenum))
            else:
                # If the line at the end of the environment is blank,
                # we can just discard it and keep the newline at the end of
                # the printed content; the newline gives us the needed space
                after = after.split('\n', 1)[1]
        # Issue warnings, if warranted
        # Warn about `\endinput`
        if (r'\endinput' in print_replacement and
                print_replacement.count(r'\endinput') != print_replacement.count(r'\string\endinput')):
            print('* DePythonTeX warning:')
            print('    "\\endinput" was present in printed content near line ' + str(linenum))
            print('    If this "\\endinput" was verbatim, you have nothing to worry about')
            print('    If this "\\endinput" is to be active, it should be printed last')
            print('    If you need "\\endinput" elsewhere, customize depythontex.py')
        # Warn if it looks like there are active `%` that could comment
        # out part of the original document.  We only need to check the
        # last line of printed content, because only there could
        # percent characters escape from their original confines within
        # `\input`, and comment out part of the document.
        if print_replacement.endswith('\n'):
            if print_replacement.count('\n') > 1:
                last_line = print_replacement.rsplit('\n', 2)[1]
            else:
                last_line = print_replacement
            if last_line.count('%') != last_line.count(r'\%') + last_line.count(r'\string%'):
                print('* DePythonTeX warning:')
                print('    One or more percent characters are on the last line of ')
                print('    printed content near line ' + str(linenum))
                print('    If they are not verbatim, they could comment out the following newline')
        else:
            if '\n' in print_replacement:
                last_line = print_replacement.rsplit('\n', 1)[1]
            else:
                last_line = print_replacement
            if last_line.count('%') != last_line.count(r'\%') + last_line.count(r'\string%'):
                print('* DePythonTeX warning:')
                print('    One or more percent characters are on the last line of ')
                print('    printed content near line ' + str(linenum))
                print('    If they are not verbatim, they could comment out the following text')
        # Warn if there were `\unskip`'s in the output, in case they weren't
        # positioned correctly
        if bool(match(r'\s*\\unskip', after)):
            print('* DePythonTeX warning:')
            print('    "\\unskip" survived substitution near line ' + str(linenum))
            print('    If it should have adjusted the spacing of printed content')
            print('    you should double-check the spacing')
    return (print_replacement, after)




# Deal with argv
# Parse argv
parser = argparse.ArgumentParser()
parser.add_argument('--version', action='version',
                    version='DePythonTeX {0}'.format(__version__))
parser.add_argument('--encoding', default='utf-8',
                    help='encoding for all text files (see codecs module for encodings)')
parser.add_argument('--overwrite', default=False, action='store_true',
                    help='overwrite existing output, if it exists (off by default)')
parser.add_argument('--listing', default='verbatim',
                    choices=('verbatim', 'fancyvrb', 'listings', 'minted', 'pythontex'),
                    help='style or package used for typesetting code')
parser.add_argument('--lexer-dict', default=None,
                    help='add mappings from Pygments lexer names to the language names of other highlighting packages; should be a comma-separated list of the form "<Pygments lexer>:<language>, <Pygments lexer>:<language>, ..."')
parser.add_argument('--preamble', default=None,
                    help='line of commands to add to output preamble')
parser.add_argument('--graphicspath', default=False, action='store_true',
                    help=r'Add the outputdir to the graphics path, by modifying an existing \graphicspath command or adding one.')
parser.add_argument('-o', '--output', default=None,
                    help='output file')
parser.add_argument('TEXNAME',
                    help='LaTeX file')
args = parser.parse_args()

# Process argv
encoding = args.encoding
listing = args.listing
if args.preamble is not None:
    preamble_additions.append(args.preamble)
if args.lexer_dict is not None:
    args.lexer_dict = args.lexer_dict.replace(' ', '').replace("'", "").replace('"','').strip('{}')
    for entry in args.lexer_dict.split(','):
        k, v = entry.split(':')
        lexer_dict[k] = v
if args.listing == 'verbatim':
    # In some contexts, the verbatim package might be desirable.
    # But we assume that the user wants minimal packages.
    # Also, the default verbatim environment doesn't allow text to follow the
    # end-of-environment command.
    # If the verbatim package is ever desired, simply uncomment the following:
    # preamble_additions.append('\\usepackage{verbatim}')
    pass
elif args.listing == 'fancyvrb':
    preamble_additions.append('\\usepackage{fancyvrb}')
elif args.listing == 'listings':
    preamble_additions.append('\\usepackage{listings}')
elif args.listing == 'minted':
    preamble_additions.append('\\usepackage{minted}')
elif args.listing == 'pythontex':
    preamble_additions.append('\\usepackage{pythontex}')




# Let the user know things have started
if args.output is not None:
    print('This is DePythonTeX {0}'.format(__version__))
    sys.stdout.flush()




# Make sure we have a valid texfile
texfile_name = os.path.expanduser(os.path.normcase(args.TEXNAME))
if not os.path.isfile(texfile_name):
    resolved = False
    if not texfile_name.endswith('.tex'):
        for ext in ('.tex', '.ltx', '.dtx'):
            if os.path.isfile(texfile_name + ext):
                texfile_name = texfile_name + ext
                resolved = True
                break
    if not resolved:
        print('* DePythonTeX error:')
        print('    Could not locate file "' + texfile_name + '"')
        sys.exit(1)
# Make sure we have a valid outfile
if args.output is not None:
    outfile_name = os.path.expanduser(os.path.normcase(args.output))
    if not args.overwrite and os.path.isfile(outfile_name):
        print('* DePythonTeX warning:')
        print('    Output file "' + outfile_name + '" already exists')
        ans = input('    Do you want to overwrite this file? [y,n]\n    ')
        if ans != 'y':
            sys.exit(1)
# Make sure the .depytx file exists
depytxfile_name = texfile_name.rsplit('.')[0] + '.depytx'
if not os.path.isfile(depytxfile_name):
    print('* DePythonTeX error:')
    print('    Could not find DePythonTeX auxiliary file "' + depytxfile_name + '"')
    print('    Use package option depythontex to creat it')
    sys.exit(1)




# Start opening files and loading data
# Read in the LaTeX file
# We read into a list with an empty first entry, so that we don't have to
# worry about zero indexing when comparing list index to file line number
f = open(texfile_name, 'r', encoding=encoding)
tex = ['']
tex.extend(f.readlines())
f.close()
# Load the .depytx
f = open(depytxfile_name, 'r', encoding=encoding)
depytx = f.readlines()
f.close()
# Process the .depytx by getting the settings contained in the last few lines
settings = dict()
n = len(depytx) - 1
while depytx[n].startswith('=>DEPYTHONTEX:SETTINGS#'):
    content = depytx[n].split('#', 1)[1].rsplit('#', 1)[0]
    k, v = content.split('=', 1)
    if v in ('true', 'True'):
        v = True
    elif v in ('false', 'False'):
        v = False
    settings[k] = v
    depytx[n] = ''
    n -= 1
# Check .depytx version to make sure it is compatible
if settings['version'] != __version__:
    print('* DePythonTeX warning:')
    print('    Version mismatch with DePythonTeX auxiliary file')
    print('    Do a complete compile cycle to update the auxiliary file')
    print('    Attempting to proceed')
# Go ahead and open the outfile, even though we don't need it until the end
# This lets us change working directories for convenience without worrying
# about having to modify the outfile path
if args.output is not None:
    outfile = open(outfile_name, 'w', encoding=encoding)




# Change working directory to the document directory
# Technically, we could get by without this, but that would require a lot of
# path modification.  This way, we can just use all paths straight out of the
# .depytx without any modification, which is much simpler and less error-prone.
if os.path.split(texfile_name)[0] != '':
    os.chdir(os.path.split(texfile_name)[0])




# Open and process the file of macros
# Read in the macros
if os.path.isfile(os.path.expanduser(os.path.normcase(settings['macrofile']))):
    f = open(os.path.expanduser(os.path.normcase(settings['macrofile'])), 'r', encoding=encoding)
    macros = f.readlines()
    f.close()
else:
    print('* DePythonTeX error:')
    print('    The macro file could not be found:')
    print('      "' + settings['macrofile'] + '"')
    print('    Run PythonTeX to create it')
    sys.exit(1)
# Create a dict for storing macros
macrodict = defaultdict(list)
# Create variables for keeping track of whether we're inside a macro or
# environment
# These must exist before we begin processing
inside_macro = False
inside_environment = False
# Loop through the macros, and extract everything
# We just extract content; we get content wrappers later, when we process all
# substituted content
for line in macros:
    if inside_macro:
        # If we're in a macro, look for the end-of-macro command
        if r'\endpytx@SVMCR' in line:
            # If the current line contains the end-of-macro command, split
            # off any content that comes before it.  Also reset
            # `inside_macro`.
            macrodict[current_macro].append(line.rsplit(r'\endpytx@SVMCR', 1)[0])
            inside_macro = False
        else:
            # If the current line doesn't end the macro, we add the whole
            # line to the macro dict
            macrodict[current_macro].append(line)
    elif inside_environment:
        if line.startswith(end_environment):
            # If the environment is ending, we reset inside_environment
            inside_environment = False
        else:
            # If we're still in the environment, add the current line to the
            # macro dict
            macrodict[current_macro].append(line)
    else:
        # If we're not in a macro or environment, we need to figure out which
        # we are dealing with (if either; there are blank lines in the macro
        # file to increase readability).  Once we've determined which one,
        # we need to get its name and extract any content.
        if line.startswith(r'\begin{'):
            # Any \begin will indicate a use of fancyvrb to save verbatim
            # content, since that is the only time an environment is used in
            # the macro file.  All other content is saved in a standard macro.
            # We extract the name of the macro in which the verbatim content
            # is saved.
            current_macro = line.rsplit('{', 1)[1].rstrip('}\n')
            inside_environment = True
            # We assemble the end-of-environment string we will need to look
            # for.  We don't assume any particular name, for generality.
            end_environment = r'\end{' + line.split('}', 1)[0].split('{', 1)[1] + '}'
            # Code typset in an environment needs to have a leading newline,
            # because the content of a normal verbatim environment keeps its
            # leading newline.
            macrodict[current_macro].append('\n')
        elif line.startswith(r'\pytx@SVMCR{'):
            # Any regular macro will use `\pytx@SVMCR`
            current_macro = line.split('{', 1)[1].split('}', 1)[0]
            inside_macro = True
            # Any content will always be on the next line, so we don't need
            # to check for it




# Do the actual processing
# Create a variable for keeping track of the current line in the LaTeX file
# Start at 1, since the first entry in the tex list is `''`
texlinenum = 1
# Create a variable for storing the current line(s) we are processing.
# This contains all lines from immediately after the last successfully
# processed line up to and including texlinenum.  We may have to process
# multiple lines at once if a macro is split over multiple lines, etc.
texcontent = tex[texlinenum]
# Create a list for storing processed content.
texout = list()
# Loop through the depytx and process
for n, depytxline in enumerate(depytx):
    if depytxline.startswith('=>DEPYTHONTEX#'):
        # Process info
        depytxcontent = depytxline.split('#', 1)[1].rstrip('#\n')
        depy_type, depy_name, depy_args, depy_typeset, depy_linenum, depy_lexer = depytxcontent.split(':')
        if depy_lexer == '':
            depy_lexer = None

        # Do a quick check on validity of info
        # #### Eventually add 'cp' and 'pc'
        if not (depy_type in ('cmd', 'env') and
                all([letter in ('o', 'm', 'v', 'n', '|') for letter in depy_args]) and
                ('|' not in depy_args or (depy_args.count('|') == 1 and depy_args.endswith('|'))) and
                depy_typeset in ('c', 'p', 'n')):
            print('* PythonTeX error:')
            print('    Invalid \\Depythontex string for operation on line ' + str(depy_linenum))
            print('    The offending string was ' + depytxcontent)
            sys.exit(1)
        # If depy_args contains a `|` to indicate `\obeylines`, strip it and
        # store in a variable.  Create a bool to keep track of obeylines
        # status, which governs whether we can look on the next line for
        # arguments.  (If obeylines is active, a newline terminates the
        # argument search.)
        if depy_args.endswith('|'):
            obeylines = True
            depy_args = depy_args.rstrip('|')
        else:
            obeylines = False
        # Get the line number as an integer
        # We don't have to adjust for zero indexing in tex
        depy_linenum = int(depy_linenum)


        # Check for information passed from LaTeX
        # This will be extra listings information, or replacements to plug in
        code_replacement = None
        code_replacement_mode = None
        print_replacement = None
        print_replacement_mode = None
        firstnumber = None
        source = None
        scan_ahead_line = n + 1
        nextdepytxline = depytx[scan_ahead_line]
        while not nextdepytxline.startswith('=>DEPYTHONTEX#'):
            if nextdepytxline.startswith('LISTING:'):
                listingcontent = nextdepytxline.split(':', 1)[1].rstrip('\n')
                if bool(match(r'firstnumber=\d+$', listingcontent)):
                    firstnumber = listingcontent.split('=', 1)[1]
                else:
                    print('* DePythonTeX error:')
                    print('    Unknown information in listings data on line ' + str(depy_linenum))
                    print('    The listings content was "' + listingcontent + '"')
                    sys.exit(1)
            elif nextdepytxline.startswith('MACRO:'):
                source = 'macro'
                try:
                    typeset, macro = nextdepytxline.rstrip('\n').split(':', 2)[1:]
                except:
                    print('* DePythonTeX error:')
                    print('    Improperly formatted macro information on line ' + str(depy_linenum))
                    print('    The macro information was "' + nextdepytxline + '"')
                    sys.exit(1)
                if macro not in macrodict:
                    print('* DePythonTeX error:')
                    print('    Could not find replacement content for macro "' + macro + '"')
                    print('    This is probably because the document needs to be recompiled')
                    sys.exit(1)
                if typeset == 'c':
                    if depy_type == 'cmd':
                        code_replacement = ''.join(macrodict[macro]).strip('\n')
                    else:
                        code_replacement = ''.join(macrodict[macro])
                elif typeset == 'p':
                    print_replacement = ''.join(macrodict[macro])
                else:
                    print('* DePythonTeX error:')
                    print('    Improper typesetting information for macro information on line ' + str(depy_linenum))
                    print('    The macro information was "' + nextdepytxline + '"')
                    sys.exit(1)
            elif nextdepytxline.startswith('FILE:'):
                source = 'file'
                try:
                    typeset, f_name = nextdepytxline.rstrip('\n').split(':', 2)[1:]
                except:
                    print('* DePythonTeX error:')
                    print('    Improperly formatted file information on line ' + str(depy_linenum))
                    print('    The file information was "' + nextdepytxline + '"')
                    sys.exit(1)
                # Files that are brought in have an optional mode that
                # determines if they need special handling (for example, verbatim)
                if ':mode=' in f_name:
                    f_name, mode = f_name.split(':mode=')
                else:
                    mode = None
                f = open(os.path.expanduser(os.path.normcase(f_name)), 'r', encoding=encoding)
                replacement = f.read()
                f.close()
                if typeset == 'c':
                    code_replacement_mode = mode
                    if depy_type == 'cmd' and code_replacement_mode != 'verbatim':
                        # Usually, code from commands is typeset with commands
                        # and code from environments is typeset in
                        # environments.  The except is code from commands
                        # that bring in external files, like `\inputpygments`
                        code_replacement = replacement
                    else:
                        # If we're replacing an environment of code with a
                        # file, then we lose the newline at the beginning
                        # of the environment, and need to get it back.
                        code_replacement = '\n' + replacement
                elif typeset == 'p':
                    print_replacement_mode = mode
                    print_replacement = replacement
                else:
                    print('* DePythonTeX error:')
                    print('    Improper typesetting information for file information on line ' + str(depy_linenum))
                    print('    The file information was "' + nextdepytxline + '"')
                    sys.exit(1)
            # Increment the line in depytx to check for more information
            # from LaTeX
            scan_ahead_line += 1
            if scan_ahead_line == len(depytx):
                break
            else:
                nextdepytxline = depytx[scan_ahead_line]


        # If the line we're looking for is within the range currently held by
        # texcontent, do nothing.  Otherwise, transfer content from tex
        # to texout until we get to the line of tex that we're looking for
        if depy_linenum > texlinenum:
            texout.append(texcontent)
            texlinenum += 1
            while texlinenum < depy_linenum:
                texout.append(tex[texlinenum])
                texlinenum += 1
            texcontent = tex[texlinenum]


        # Deal with arguments
        # All arguments are parsed and stored in a list variables, even if
        # they are not used, for completeness; this makes it easy to add
        # functionality
        # Start by splitting the current line into what comes before the
        # command or environment, and what is after it
        if depy_type == 'cmd':
            try:
                before, after = texcontent.split('\\' + depy_name, 1)
            except:
                print('* DePythonTeX error:')
                print('    Could not find command "' + depy_name + '" on line ' + str(depy_linenum))
                sys.exit(1)
        else:  # depy_type == 'env':
            try:
                before, after = texcontent.split(r'\begin{' + depy_name + '}', 1)
            except:
                print('* DePythonTeX error:')
                print('    Could not find environment "' + depy_name + '" on line ' + str(depy_linenum))
                sys.exit(1)
        # We won't need the content from before the command or environment
        # again, so we go ahead and store it
        texout.append(before)

        # Parse the arguments
        # Create a list for storing the recovered arguments
        arglist = list()
        for argindex, arg in enumerate(depy_args):
            if arg == 'n':
                pass
            elif arg == 'o':
                if after[0] == '[':
                    # Account for possible line breaks before end of arg
                    while ']' not in after:
                        texlinenum += 1
                        after += tex[texlinenum]
                    optarg, after = after[1:].split(']', 1)
                else:
                    if obeylines:
                        # Take into account possible whitespace before arg
                        if bool(match('[ \t]*\[', after)):
                            after = after.split('[', 1)[1]
                            while ']' not in after:
                                texlinenum += 1
                                after += tex[texlinenum]
                            optarg, after = after.split(']', 1)
                        else:
                            optarg = None
                            # If this is the last arg, and it wasn't found,
                            # the macro should eat all whitespace following it
                            if argindex == len(depy_args) - 1:
                                after = sub('^[ \t]*', '', after)
                    else:
                        # Allow peeking ahead a line for the argument
                        if bool(match('\s*$', after)) and after.count('\n') < 2:
                            texlinenum += 1
                            after += tex[texlinenum]
                        # Take into account possible whitespace before arg
                        if bool(match('\s*\[', after)):
                            after = after.split('[', 1)[1]
                            while ']' not in after:
                                texlinenum += 1
                                after += tex[texlinenum]
                            optarg, after = after.split(']', 1)
                        else:
                            optarg = None
                            # Account for eating whitespace afterward, if arg not found
                            if argindex == len(depy_args) - 1:
                                if bool(match('\s*$', after)) and after.count('\n') < 2:
                                    texlinenum += 1
                                    after += tex[texlinenum]
                                if not bool(match('\s*$', after)):
                                    after = sub('^\s*', '', after)
                arglist.append(optarg)
            elif arg == 'm':
                # Account for possible line breaks or spaces before arg
                if after[0] == '{':
                    after = after[1:]
                else:
                    if obeylines:
                        # Account for possible leading whitespace
                        if bool(match('[ \t\f\v]*\{', after)):
                            after = after.split('{', 1)[1]
                        else:
                            print('* DePythonTeX error:')
                            print('    Flawed mandatory argument for "' + depy_name + '" on line ' + str(depy_linenum))
                            sys.exit(1)
                    else:
                        # Peek ahead a line if needed
                        if bool(match('\s*$', after)) and after.count('\n') < 2:
                            texlinenum += 1
                            after += tex[texlinenum]
                        if bool(match('\s*\{', after)):
                            after = after.split('{', 1)[1]
                        else:
                            print('* DePythonTeX error:')
                            print('    Flawed mandatory argument for "' + depy_name + '" on line ' + str(depy_linenum))
                            sys.exit(1)
                # Go through the argument character by character to find the
                # closing brace.
                # If possible, use a very simple approach
                if (r'\{' not in after and r'\}' not in after and
                        r'\string' not in after and
                        after.count('{') + 1 == after.count('}')):
                    pos = 0
                    lbraces = 1
                    rbraces = 0
                    while True:
                        if after[pos] == '{':
                            lbraces += 1
                        elif after[pos] == '}':
                            rbraces += 1
                        if lbraces == rbraces:
                            break
                        pos += 1
                        if pos == len(after):
                            texlinenum += 1
                            after += tex[texlinenum]
                # If a simple parsing approach won't work, parse in much
                # greater depth
                else:
                    pos = 0
                    lbraces = 1
                    rbraces = 0
                    while True:
                        if after[pos] == '{':
                            # If the current character is a brace, we count it
                            lbraces += 1
                            if lbraces == rbraces:
                                break
                            pos += 1
                        elif after[pos] == '}':
                            # If the current character is a brace, we count it
                            rbraces += 1
                            if lbraces == rbraces:
                                break
                            pos += 1
                        elif after[pos:].startswith(r'\string'):
                            # If the current position marks the beginning of `\string`, we
                            # resolve the `\string` command
                            # First, jump ahead to after `\string`
                            pos += 7 #+= len(r'\string')
                            # See if `\string` is followed by a regular macro
                            # If so, jump past it; otherwise, figure out if a
                            # single-character macro, or just a single character, is next,
                            # and jump past it
                            standard_macro = match(r'\\[a-zA-Z]+', line[pos:])
                            if bool(standard_macro):
                                pos += standard_macro.end()
                            elif line[pos] == '\\':
                                pos += 2
                            else:
                                pos += 1
                        elif line[pos] == '\\':
                            # If the current position is a backslash, figure out what
                            # macro is used, and jump past it
                            # The macro must either be a standard alphabetic macro,
                            # or a single-character macro
                            standard_macro = match(r'\\[a-zA-Z]+', line[pos:])
                            if bool(standard_macro):
                                pos += standard_macro.end()
                            else:
                                pos += 2
                        else:
                            pos += 1
                        if pos == len(after):
                            texlinenum += 1
                            after += tex[texlinenum]
                mainarg = after[:pos]
                after = after[pos+1:]
                arglist.append(mainarg)
            elif arg == 'v':
                if after[0] == '{':
                    # Account for the possibility of matched brace delimiters
                    # Not all verbatim commands allow for these
                    pos = 1
                    lbraces = 1
                    rbraces = 0
                    while True:
                        if after[pos] == '{':
                            lbraces += 1
                        elif after[pos] == '}':
                            rbraces += 1
                        if lbraces == rbraces:
                            break
                        pos += 1
                        if pos == len(after):
                            texlinenum += 1
                            after += tex[texlinenum]
                    mainarg = after[1:pos]
                    after = after[pos+1:]
                else:
                    # Deal with matched character delims
                    delim = after[0]
                    while after.count(delim) < 2:
                        texlinenum += 1
                        after += tex[texlinenum]
                    mainarg, after = after[1:].split(delim, 1)
                arglist.append(mainarg)


        # Do substitution, depending on what is required
        # Need a variable for processed content to be added to texout
        processed = None
        if depy_typeset == 'c':
            if depy_type == 'cmd':
                # Make sure that `after` contains two lines of content
                # This is needed for some replacements that need to look ahead
                if after.count('\n') < 2:
                    texlinenum += 1
                    after += tex[texlinenum]
                processed, texcontent = replace_code_cmd(depy_name, arglist,
                                                         depy_linenum,
                                                         code_replacement,
                                                         code_replacement_mode,
                                                         after, depy_lexer,
                                                         firstnumber)
            else:  # depy_type == 'env'
                end_environment = r'\end{' + depy_name + '}'
                if code_replacement is None:
                    if end_environment not in after:
                        while True:
                            texlinenum += 1
                            after += tex[texlinenum]
                            if end_environment in tex[texlinenum]:
                                break
                    code_replacement, after = after.split(end_environment, 1)
                    # If there's content on the line with the end-environment
                    # command, it should be discarded, to imitate TeX
                    if not code_replacement.endswith('\n'):
                        code_replacement = code_replacement.rsplit('\n', 1)[0] + '\n'
                    # Take care of `gobble`
                    if settings['gobble'] == 'auto':
                        code_replacement = textwrap.dedent(code_replacement)
                else:
                    if end_environment not in after:
                        while True:
                            texlinenum += 1
                            if end_environment in tex[texlinenum]:
                                after = tex[texlinenum]
                                break
                    after = after.split(end_environment, 1)[1]
                # Make sure that `after` contains two lines of content
                # This is needed for some replacements that need to look ahead
                if after.count('\n') < 2:
                    texlinenum += 1
                    after += tex[texlinenum]
                processed, texcontent = replace_code_env(depy_name, arglist,
                                                         depy_linenum,
                                                         code_replacement,
                                                         code_replacement_mode,
                                                         after, depy_lexer,
                                                         firstnumber)
        elif depy_typeset == 'p' and print_replacement is not None:
            if depy_type == 'cmd':
                # Make sure that `after` contains two lines of content
                # This is needed for some replacements that need to look ahead
                if after.count('\n') < 2:
                    texlinenum += 1
                    after += tex[texlinenum]
                processed, texcontent = replace_print_cmd(depy_name, arglist,
                                                          depy_linenum,
                                                          print_replacement,
                                                          print_replacement_mode,
                                                          source,
                                                          after)
            else:  # depy_type == 'env'
                end_environment = r'\end{' + depy_name + '}'
                if end_environment not in after:
                    while True:
                        texlinenum += 1
                        if end_environment in tex[texlinenum]:
                            after = tex[texlinenum]
                            break
                after = after.split(end_environment, 1)[1]
                # Make sure that `after` contains two lines of content
                # This is needed for some replacements that need to look ahead
                if after.count('\n') < 2:
                    texlinenum += 1
                    after += tex[texlinenum]
                processed, texcontent = replace_print_env(depy_name, arglist,
                                                          depy_linenum,
                                                          print_replacement,
                                                          print_replacement_mode,
                                                          source,
                                                          after)
        else:  # depy_typeset == 'n' or (depy_typeset == 'p' and print_replacement is None):
            if depy_type == 'cmd':
                texcontent = after
            else:  # depy_type == 'env'
                end_environment = r'\end{' + depy_name + '}'
                if end_environment not in after:
                    while True:
                        texlinenum += 1
                        if end_environment in tex[texlinenum]:
                            after = tex[texlinenum]
                            break
                after = after.split(end_environment, 1)[1]
                if bool(match('\s*\n', after)):
                    # If the line following `after` is whitespace, it should
                    # be stripped, since most environments throw away
                    # anything after the end of the environment
                    after = after.split('\n')[1]
                texcontent = after
        # #### Once it's supported on the TeX side, need to add support for
        # pc and cp


        # Store any processed content
        if processed is not None:
            texout.append(processed)


# Transfer anything that's left in tex to texout
texout.append(texcontent)
texout.extend(tex[texlinenum+1:])




# Replace the `\usepackage{pythontex}`
for n, line in enumerate(texout):
    if '{pythontex}' in line:
        startline = n
        while '\\usepackage' not in texout[startline] and startline >= 0:
            startline -= 1
        if startline == n:
            if bool(search(r'\\usepackage(?:\[.*?\]){0,1}\{pythontex\}', line)):
                texout[n] = sub(r'\\usepackage(?:\[.*?\]){0,1}\{pythontex\}', '', line)
                if texout[n].isspace():
                    texout[n] = ''
                break
        else:
            content = ''.join(texout[startline:n+1])
            if bool(search(r'(?s)\\usepackage(?:\[.*?\]\s*){0,1}\{pythontex\}', content)):
                replacement = sub(r'(?s)\\usepackage(?:\[.*?\]\s*){0,1}\{pythontex\}', '', content)
                if replacement.isspace():
                    replacement = ''
                texout[startline] = replacement
                for l in range(startline+1, n+1):
                    texout[l] = ''
                break
    elif line.startswith(r'\begin{document}'):
        break
if preamble_additions:
    texout[n] += '\n'.join(preamble_additions) + '\n'
# Take care of graphicspath
if args.graphicspath and settings['graphicx']:
    for n, line in enumerate(texout):
        if '\\graphicspath' in line and not bool(match('\s*%', line)):
            texout[n] = line.replace('\\graphicspath{', '\\graphicspath{{' + settings['outputdir'] +'/}')
            break
        elif line.startswith(r'\begin{document}'):
            texout[n] = '\\graphicspath{{' + settings['outputdir'] + '/}}\n' + line
            break




# Print any final messages
if forced_double_space_list:
    print('* DePythonTeX warning:')
    print('    A trailing double space was forced with "\\space{}" for the following')
    print('    This can happen when printed content is included inline')
    print('    The forced double space is only an issue if it is not intentional')
    for name, linenum in forced_double_space_list:
        print('      "' + name + '" near line ' + str(linenum))




# Write output
if args.output is not None:
    for line in texout:
        outfile.write(line)
    outfile.close()
else:
    if sys.version_info[0] == 2:
        sys.stdout = codecs.getwriter(encoding)(sys.stdout, 'strict')
        sys.stderr = codecs.getwriter(encoding)(sys.stderr, 'strict')
    else:
        sys.stdout = codecs.getwriter(encoding)(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter(encoding)(sys.stderr.buffer, 'strict')
    for line in texout:
        sys.stdout.write(line)
