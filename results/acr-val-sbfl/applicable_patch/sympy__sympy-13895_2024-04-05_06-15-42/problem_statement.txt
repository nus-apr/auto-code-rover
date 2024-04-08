(-x/4 - S(1)/12)**x - 1 simplifies to an inequivalent expression
    >>> from sympy import *
    >>> x = Symbol('x')
    >>> e = (-x/4 - S(1)/12)**x - 1
    >>> e
    (-x/4 - 1/12)**x - 1
    >>> f = simplify(e)
    >>> f
    12**(-x)*(-12**x + (-3*x - 1)**x)
    >>> a = S(9)/5
    >>> simplify(e.subs(x,a))
    -1 - 32*15**(1/5)*2**(2/5)/225
    >>> simplify(f.subs(x,a))
    -1 - 32*(-1)**(4/5)*60**(1/5)/225
    >>> N(e.subs(x,a))
    -1.32255049319339
    >>> N(f.subs(x,a))
    -0.739051169462523 - 0.189590423018741*I


