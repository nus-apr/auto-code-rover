LaTeX printer does not use the same order of monomials as pretty and str 
When printing a Poly, the str and pretty printers use the logical order of monomials, from highest to lowest degrees. But latex printer does not. 
```
>>> var('a b c x')
>>> p = Poly([a, 1, b, 2, c, 3], x)
>>> p
Poly(a*x**5 + x**4 + b*x**3 + 2*x**2 + c*x + 3, x, domain='ZZ[a,b,c]')
>>> pretty(p)
"Poly(a*x**5 + x**4 + b*x**3 + 2*x**2 + c*x + 3, x, domain='ZZ[a,b,c]')"
>>> latex(p)
'\\operatorname{Poly}{\\left( a x^{5} + b x^{3} + c x + x^{4} + 2 x^{2} + 3, x, domain=\\mathbb{Z}\\left[a, b, c\\right] \\right)}'
```
