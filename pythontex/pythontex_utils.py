# -*- coding: utf-8 -*-
'''
PythonTeX utilities class for Python scripts.

The utilities class provides variables and methods for the individual 
Python scripts created and executed by PythonTeX.  An instance of the class 
named "pytex" is automatically created in each individual script.

Copyright (c) 2012-2014, Geoffrey M. Poore
All rights reserved.
Licensed under the BSD 3-Clause License:
    http://www.opensource.org/licenses/BSD-3-Clause

'''


# Imports
import sys
import warnings
if sys.version_info.major == 2:
    import io

# Most imports are only needed for SymPy; these are brought in via 
# "lazy import."  Importing unicode_literals here shouldn't ever be necessary 
# under Python 2.  If unicode_literals is imported in the main script, then 
# all strings in this script will be treated as bytes, and the main script 
# will try to decode the strings from this script as necessary.  The decoding 
# shouldn't cause any problems, since all strings in this file may be decoded 
# as valid ASCII. (The actual file is encoded in utf-8, but only characters 
# within the ASCII subset are actually used).


class PythonTeXUtils(object):
    '''
    A class of PythonTeX utilities.
    
    Provides variables for keeping track of TeX-side information, and methods
    for formatting and saving data.
    
    The following variables and methods will be created within instances 
    of the class during execution.
    
    String variables for keeping track of TeX information.  Most are 
    actually needed; the rest are included for completeness.
        * family
        * session
        * restart
        * command
        * context
        * args
        * instance
        * line
    
    Future file handle for output that is saved via macros
        * macrofile
    
    Future formatter function that is used to format output
        * formatter
    '''
    
    def __init__(self, fmtr='str'):
        '''
        Initialize
        '''
        self.set_formatter(fmtr)
    
    # We need a function that will process the raw `context` into a 
    # dictionary with attributes
    _context_raw = None
    class _DictWithAttr(dict):
        pass
    def set_context(self, expr):
        '''
        Convert the string `{context}` into a dict with attributes
        '''
        if not expr or expr == self._context_raw:
            pass
        else:
            self._context_raw = expr
            self.context = self._DictWithAttr()
            k_and_v = [map(lambda x: x.strip(), kv.split('=')) for kv in expr.split(',')]
            for k, v in k_and_v:
                if v.startswith('!!int '):
                    v = int(float(v[6:]))
                elif v.startswith('!!float '):
                    v = float(v[8:])
                elif v.startswith('!!str '):
                    v = v[6:]
                self.context[k] = v
                setattr(self.context, k, v)
    
    # A primary use for contextual information is to pass dimensions from the
    # TeX side to the Python side.  To make that as convenient as possible,
    # we need some length conversion functions.
    # Conversion reference:  http://tex.stackexchange.com/questions/41370/what-are-the-possible-dimensions-sizes-units-latex-understands
    def pt_to_in(self, expr):
        '''
        Convert points to inches.  Accepts numbers, strings of digits, and 
        strings of digits that end with `pt`.
        '''
        try:
            ans = expr/72.27
        except:
            if expr.endswith('pt'):
                expr = expr[:-2]
            ans = float(expr)/72.27
        return ans
    def pt_to_cm(self, expr):
        '''
        Convert points to centimeters.
        '''
        return self.pt_to_in(expr)*2.54
    def pt_to_mm(self, expr):
        '''
        Convert points to millimeters.
        '''
        return self.pt_to_in(expr)*25.4
    def pt_to_bp(self, expr):
        '''
        Convert points to big (DTP or PostScript) points.
        '''
        return self.pt_to_in(expr)*72
        
    
    # We need a context-aware interface to SymPy's latex printer.  The 
    # appearance of typeset math should depend on where it appears in a 
    # document.  (We will refer to the latex printer, rather than the LaTeX 
    # printer, because the two are separate.  Compare sympy.printing.latex 
    # and sympy.galgebra.latex_ex.)  
    #
    # Creating this interface takes some work.  We don't want to import 
    # anything from SymPy unless it is actually used, to keep things clean and 
    # fast.
    
    # First we create a tuple containing all LaTeX math styles.  These are 
    # the contexts that SymPy's latex printer must adapt to.
    # The style order doesn't matter, but it corresponds to that of \mathchoice
    _sympy_latex_styles = ('display', 'text', 'script', 'scriptscript')
    
    # Create the public functions for the user, and private functions that 
    # they call.  Two layers are necessary, because we need to be able to 
    # redefine the functions that do the actual work, once things are 
    # initialized.  But we don't want to redefine the public functions, since 
    # that could cause problems if the user defines a new function to be one 
    # of the public functions--the user's function would not change when
    # the method was redefined.
    def _sympy_latex(self, expr, **settings):
        self._init_sympy_latex()
        return self._sympy_latex(expr, **settings)
    
    def sympy_latex(self, expr, **settings):
        return self._sympy_latex(expr, **settings)
    
    def _set_sympy_latex(self, style, **kwargs):
        self._init_sympy_latex()
        self._set_sympy_latex(style, **kwargs)
    
    def set_sympy_latex(self, style, **kwargs):
        self._set_sympy_latex(style, **kwargs)
    # Temporary compatibility with deprecated methods
    def init_sympy_latex(self):
        warnings.warn('Method init_sympy_latex() is deprecated; init is now automatic.')
        self._init_sympy_latex()
    
    # Next we create a method that initializes the actual context-aware 
    # interface to SymPy's latex printer.
    def _init_sympy_latex(self):
        '''
        Initialize a context-aware interface to SymPy's latex printer.
        
        This consists of creating the dictionary of settings and creating the 
        sympy_latex method that serves as an interface to SymPy's 
        LatexPrinter.  This last step is actually performed by calling 
        self._make_sympy_latex().
        '''
        # Create dictionaries of settings for different contexts.
        # 
        # Currently, the main goal is to use pmatrix (or an equivalent) 
        # in \displaystyle contexts, and smallmatrix in \textstyle, 
        # \scriptstyle (superscript or subscript), and \scriptscriptstyle
        # (superscript or subscript of a superscript or subscript) 
        # contexts.  Basically, we want matrix size to automatically 
        # scale based on context.  It is expected that additional 
        # customization may prove useful as SymPy's LatexPrinter is 
        # further developed.
        #
        # The 'fold_frac_powers' option is probably the main other 
        # setting that might sometimes be nice to invoke in a 
        # context-dependent manner.
        #
        # In the default settings below, all matrices are set to use 
        # parentheses rather than square brackets.  This is largely a 
        # matter of personal preference.  The use of parentheses is based 
        # on the rationale that parentheses are less easily confused with 
        # the determinant and are easier to write by hand than are square 
        # brackets.  The settings for 'script' and 'scriptscript' are set
        # to those of 'text', since all of these should in general 
        # require a more compact representation of things.
        self._sympy_latex_settings = {'display': {'mat_str': 'pmatrix', 'mat_delim': None},
                                      'text': {'mat_str': 'smallmatrix', 'mat_delim': '('},
                                      'script': {'mat_str': 'smallmatrix', 'mat_delim': '('},
                                      'scriptscript': {'mat_str': 'smallmatrix', 'mat_delim': '('} }
        # Now we create a function for updating the settings.
        #
        # Note that EVERY time the settings are changed, we must call 
        # self._make_sympy_latex().  This is because the _sympy_latex() 
        # method is defined based on the settings, and every time the 
        # settings change, it may need to be redefined.  It would be 
        # possible to define _sympy_latex() so that its definition remained 
        # constant, simply drawing on the settings.  But most common 
        # combinations of settings allow more efficient versions of 
        # _sympy_latex() to be defined.
        def _set_sympy_latex(style, **kwargs):
            if style in self._sympy_latex_styles:
                self._sympy_latex_settings[style].update(kwargs)
            elif style == 'all':
                for s in self._sympy_latex_styles:
                    self._sympy_latex_settings[s].update(kwargs)
            else:
                warnings.warn('Unknown LaTeX math style ' + str(style))
            self._make_sympy_latex()
        self._set_sympy_latex = _set_sympy_latex
        
        # Now that the dictionaries of settings have been created, and 
        # the function for modifying the settings is in place, we are ready 
        # to create the actual interface.
        self._make_sympy_latex()
            
    # Finally, create the actual interface to SymPy's LatexPrinter
    def _make_sympy_latex(self):
        '''
        Create a context-aware interface to SymPy's LatexPrinter class.
        
        This is an interface to the LatexPrinter class, rather than 
        to the latex function, because the function is simply a 
        wrapper for accessing the class and because settings may be 
        passed to the class more easily.
        
        Context dependence is accomplished via LaTeX's \mathchoice macro.  
        This macros takes four arguments:
            \mathchoice{<display>}{<text>}{<script>}{<scriptscript>}
        All four arguments are typeset by LaTeX, and then the appropriate one 
        is actually typeset in the document based on the current style.  This 
        may seem like a very inefficient way of doing things, but this 
        approach is necessary because LaTeX doesn't know the math style at a 
        given point until after ALL mathematics have been typeset.  This is 
        because macros such as \over and \atop change the math style of things 
        that PRECEDE them.  See the following discussion for more information:
            http://tex.stackexchange.com/questions/1223/is-there-a-test-for-the-different-styles-inside-maths-mode
        
        The interface takes optional settings.  These optional 
        settings override the default context-dependent settings.  
        Accomplishing this mixture of settings requires (deep)copying 
        the default settings, then updating the copies with the optional 
        settings.  This leaves the default settings intact, with their 
        original values, for the next usage.
        
        The interface is created in various ways depending on the specific
        combination of context-specific settings.  While a general, static 
        interface could be created, that would involve invoking LatexPrinter 
        four times, once for each math style.  It would also require that 
        LaTeX process a \mathchoice macro for everything returned by 
        _sympy_latex(), which would add more inefficiency.  In practice, there 
        will generally be enough overlap between the different settings, and 
        the settings will be focused enough, that more efficient 
        implementations of _sympy_latex() are possible.
        
        Note that we perform a "lazy import" here.  We don't want to import
        the LatexPrinter unless we are sure to use it, since the import brings
        along a number of other dependencies from SymPy.  We don't want 
        unnecessary overhead from SymPy imports.
        '''
        # sys has already been imported        
        import copy
        try:
            from sympy.printing.latex import LatexPrinter
        except ImportError:
            sys.exit('Could not import from SymPy')
        
        # Go through a number of possible scenarios, to create an efficient 
        # implementation of sympy_latex()
        if all(self._sympy_latex_settings[style] == {} for style in self._sympy_latex_styles):
            def _sympy_latex(expr, **settings):
                '''            
                Deal with the case where there are no context-specific 
                settings.
                '''
                return LatexPrinter(settings).doprint(expr)
        elif all(self._sympy_latex_settings[style] == self._sympy_latex_settings['display'] for style in self._sympy_latex_styles):
            def _sympy_latex(expr, **settings):
                '''
                Deal with the case where all settings are identical, and thus 
                the settings are really only being used to set defaults, 
                rather than context-specific behavior.
                
                Check for empty settings, so as to avoid deepcopy
                '''
                if not settings:
                    return LatexPrinter(self._sympy_latex_settings['display']).doprint(expr)
                else:
                    final_settings = copy.deepcopy(self._sympy_latex_settings['display'])
                    final_settings.update(settings)
                    return LatexPrinter(final_settings).doprint(expr)
        elif all(self._sympy_latex_settings[style] == self._sympy_latex_settings['text'] for style in ('script', 'scriptscript')):
            def _sympy_latex(expr, **settings):
                '''
                Deal with the case where only 'display' has different settings.
                
                This should be the most common case.
                '''
                if not settings:
                    display = LatexPrinter(self._sympy_latex_settings['display']).doprint(expr)
                    text = LatexPrinter(self._sympy_latex_settings['text']).doprint(expr)
                else:
                    display_settings = copy.deepcopy(self._sympy_latex_settings['display'])
                    display_settings.update(settings)
                    display = LatexPrinter(display_settings).doprint(expr)
                    text_settings = copy.deepcopy(self._sympy_latex_settings['text'])
                    text_settings.update(settings)
                    text = LatexPrinter(text_settings).doprint(expr)
                if display == text:
                    return display
                else:
                    return r'\mathchoice{' + display + '}{' + text + '}{' + text + '}{' + text + '}'
        else:
            def _sympy_latex(expr, **settings):
                '''
                If all attempts at simplification fail, create the most 
                general interface.
                
                The main disadvantage here is that LatexPrinter is invoked 
                four times and we must create many temporary variables.
                '''
                if not settings:
                    display = LatexPrinter(self._sympy_latex_settings['display']).doprint(expr)
                    text = LatexPrinter(self._sympy_latex_settings['text']).doprint(expr)
                    script = LatexPrinter(self._sympy_latex_settings['script']).doprint(expr)
                    scriptscript = LatexPrinter(self._sympy_latex_settings['scriptscript']).doprint(expr)
                else:
                    display_settings = copy.deepcopy(self._sympy_latex_settings['display'])
                    display_settings.update(settings)
                    display = LatexPrinter(display_settings).doprint(expr)
                    text_settings = copy.deepcopy(self._sympy_latex_settings['text'])
                    text_settings.update(settings)
                    text = LatexPrinter(text_settings).doprint(expr)
                    script_settings = copy.deepcopy(self._sympy_latex_settings['script'])
                    script_settings.update(settings)
                    script = LatexPrinter(script_settings).doprint(expr)
                    scriptscript_settings = copy.deepcopy(self._sympy_latex_settings['scripscript'])
                    scriptscript_settings.update(settings)
                    scriptscript = LatexPrinter(scriptscript_settings).doprint(expr)
                if display == text and display == script and display == scriptscript:
                    return display
                else:
                    return r'\mathchoice{' + display + '}{' + text + '}{' + script + '}{' + scriptscript+ '}'
        self._sympy_latex = _sympy_latex
    
    # Now we are ready to create non-SymPy formatters and a method for 
    # setting formatters
    def identity_formatter(self, expr):
        '''
        For generality, we need an identity formatter, a formatter that does
        nothing to its argument and simply returns it unchanged.
        '''
        return expr
    
    def set_formatter(self, fmtr='str'):
        '''
        Set the formatter method.
        
        This is used to process output that is brought in via macros.  It is 
        also available for the user in formatting printed or saved output.
        '''
        if fmtr == 'str':
            if sys.version_info[0] == 2:
                self.formatter = unicode
            else:
                self.formatter = str
        elif fmtr == 'sympy_latex':
            self.formatter = self.sympy_latex
        elif fmtr in ('None', 'none', 'identity') or fmtr is None:
            self.formatter = self.identity_formatter
        else:
            raise ValueError('Unsupported formatter type')
    
    # We need functions that can be executed immediately before and after
    # each chunk of code.  By default, these should do nothing; they are for
    # user customization, or customization via packages.
    def before(self):
        pass
    def after(self):
        pass
    
    
    # We need a way to keep track of dependencies
    # We create a list that stores specified dependencies, and a method that
    # adds dependencies to the list.  The contents of this list must be 
    # written to stdout at the end of the file, to be transmitted back to the 
    # main script.  So we create a method that prints them to stdout.  This is
    # called via a generic cleanup method that is always invoked at the end of 
    # the script.
    _dependencies = list()
    def add_dependencies(self, *args):
        self._dependencies.extend(list(args))
    def _save_dependencies(self):
        print('=>PYTHONTEX:DEPENDENCIES#')
        if self._dependencies:
            for dep in self._dependencies:
                print(dep)
    
    # We need a way to keep track of created files, so that they can be 
    # automatically cleaned up.  By default, all files are created within the
    # pythontex-files_<jobname> folder, and are thus contained.  If a custom
    # working directory is used, or files are otherwise created in a custom
    # location, it may be desirable to track them and keep them cleaned up.
    # Furthermore, even when files are contained in the default directory, it
    # may be desirable to delete files when they are no longer needed due to
    # program changes, renaming, etc.
    _created = list()
    def add_created(self, *args):
        self._created.extend(list(args))
    def _save_created(self):
        print('=>PYTHONTEX:CREATED#')
        if self._created:
            for creation in self._created:
                print(creation)
    
    # A custom version of `open()` is useful for automatically tracking files
    # opened for reading as dependencies and tracking files opened for 
    # writing as created files.
    def open(self, name, mode='r', *args, **kwargs):
        if mode in ('r', 'rt', 'rb'):
            self.add_dependencies(name)
        elif mode in ('w', 'wt', 'wb'):
            self.add_created(name)
        else:
            warnings.warn('Unsupported mode {0} for file tracking'.format(mode))
        if sys.version_info.major == 2 and (len(args) > 1 or 'encoding' in kwargs):
            return io.open(name, mode, *args, **kwargs)
        else:
            return open(name, mode, *args, **kwargs)
    
    def cleanup(self):
        self._save_dependencies()
        self._save_created()
        
