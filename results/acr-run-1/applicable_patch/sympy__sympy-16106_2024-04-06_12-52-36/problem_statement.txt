mathml printer for IndexedBase required
Writing an `Indexed` object to MathML fails with a `TypeError` exception: `TypeError: 'Indexed' object is not iterable`:

```
In [340]: sympy.__version__
Out[340]: '1.0.1.dev'

In [341]: from sympy.abc import (a, b)

In [342]: sympy.printing.mathml(sympy.IndexedBase(a)[b])
---------------------------------------------------------------------------
TypeError                                 Traceback (most recent call last)
<ipython-input-342-b32e493b70d3> in <module>()
----> 1 sympy.printing.mathml(sympy.IndexedBase(a)[b])

/dev/shm/gerrit/venv/stable-3.5/lib/python3.5/site-packages/sympy/printing/mathml.py in mathml(expr, **settings)
    442 def mathml(expr, **settings):
    443     """Returns the MathML representation of expr"""
--> 444     return MathMLPrinter(settings).doprint(expr)
    445 
    446 

/dev/shm/gerrit/venv/stable-3.5/lib/python3.5/site-packages/sympy/printing/mathml.py in doprint(self, expr)
     36         Prints the expression as MathML.
     37         """
---> 38         mathML = Printer._print(self, expr)
     39         unistr = mathML.toxml()
     40         xmlbstr = unistr.encode('ascii', 'xmlcharrefreplace')

/dev/shm/gerrit/venv/stable-3.5/lib/python3.5/site-packages/sympy/printing/printer.py in _print(self, expr, *args, **kwargs)
    255                 printmethod = '_print_' + cls.__name__
    256                 if hasattr(self, printmethod):
--> 257                     return getattr(self, printmethod)(expr, *args, **kwargs)
    258             # Unknown object, fall back to the emptyPrinter.
    259             return self.emptyPrinter(expr)

/dev/shm/gerrit/venv/stable-3.5/lib/python3.5/site-packages/sympy/printing/mathml.py in _print_Basic(self, e)
    356     def _print_Basic(self, e):
    357         x = self.dom.createElement(self.mathml_tag(e))
--> 358         for arg in e:
    359             x.appendChild(self._print(arg))
    360         return x

TypeError: 'Indexed' object is not iterable
```

It also fails for more complex expressions where at least one element is Indexed.
