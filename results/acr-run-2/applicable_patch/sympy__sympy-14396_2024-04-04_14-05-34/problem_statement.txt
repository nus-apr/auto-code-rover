Poly(domain='RR[y,z]') doesn't work
``` py
In [14]: Poly(1.2*x*y*z, x)
Out[14]: Poly(1.2*y*z*x, x, domain='RR[y,z]')

In [15]: Poly(1.2*x*y*z, x, domain='RR[y,z]')
---------------------------------------------------------------------------
OptionError                               Traceback (most recent call last)
<ipython-input-15-d83389519ae1> in <module>()
----> 1 Poly(1.2*x*y*z, x, domain='RR[y,z]')

/Users/aaronmeurer/Documents/Python/sympy/sympy-scratch/sympy/polys/polytools.py in __new__(cls, rep, *gens, **args)
     69     def __new__(cls, rep, *gens, **args):
     70         """Create a new polynomial instance out of something useful. """
---> 71         opt = options.build_options(gens, args)
     72
     73         if 'order' in opt:

/Users/aaronmeurer/Documents/Python/sympy/sympy-scratch/sympy/polys/polyoptions.py in build_options(gens, args)
    718
    719     if len(args) != 1 or 'opt' not in args or gens:
--> 720         return Options(gens, args)
    721     else:
    722         return args['opt']

/Users/aaronmeurer/Documents/Python/sympy/sympy-scratch/sympy/polys/polyoptions.py in __init__(self, gens, args, flags, strict)
    151                     self[option] = cls.preprocess(value)
    152
--> 153         preprocess_options(args)
    154
    155         for key, value in dict(defaults).items():

/Users/aaronmeurer/Documents/Python/sympy/sympy-scratch/sympy/polys/polyoptions.py in preprocess_options(args)
    149
    150                 if value is not None:
--> 151                     self[option] = cls.preprocess(value)
    152
    153         preprocess_options(args)

/Users/aaronmeurer/Documents/Python/sympy/sympy-scratch/sympy/polys/polyoptions.py in preprocess(cls, domain)
    480                 return sympy.polys.domains.QQ.algebraic_field(*gens)
    481
--> 482         raise OptionError('expected a valid domain specification, got %s' % domain)
    483
    484     @classmethod

OptionError: expected a valid domain specification, got RR[y,z]
```

Also, the wording of error message could be improved

