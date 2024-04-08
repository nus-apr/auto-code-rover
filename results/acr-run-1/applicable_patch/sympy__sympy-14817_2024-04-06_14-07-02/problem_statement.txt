Error pretty printing MatAdd
```py
>>> pprint(MatrixSymbol('x', n, n) + MatrixSymbol('y*', n, n))
Traceback (most recent call last):
  File "./sympy/core/sympify.py", line 368, in sympify
    expr = parse_expr(a, local_dict=locals, transformations=transformations, evaluate=evaluate)
  File "./sympy/parsing/sympy_parser.py", line 950, in parse_expr
    return eval_expr(code, local_dict, global_dict)
  File "./sympy/parsing/sympy_parser.py", line 863, in eval_expr
    code, global_dict, local_dict)  # take local objects in preference
  File "<string>", line 1
    Symbol ('y' )*
                 ^
SyntaxError: unexpected EOF while parsing

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "./sympy/printing/pretty/pretty.py", line 2371, in pretty_print
    use_unicode_sqrt_char=use_unicode_sqrt_char))
  File "./sympy/printing/pretty/pretty.py", line 2331, in pretty
    return pp.doprint(expr)
  File "./sympy/printing/pretty/pretty.py", line 62, in doprint
    return self._print(expr).render(**self._settings)
  File "./sympy/printing/printer.py", line 274, in _print
    return getattr(self, printmethod)(expr, *args, **kwargs)
  File "./sympy/printing/pretty/pretty.py", line 828, in _print_MatAdd
    if S(item.args[0]).is_negative:
  File "./sympy/core/sympify.py", line 370, in sympify
    raise SympifyError('could not parse %r' % a, exc)
sympy.core.sympify.SympifyError: Sympify of expression 'could not parse 'y*'' failed, because of exception being raised:
SyntaxError: unexpected EOF while parsing (<string>, line 1)
```

The code shouldn't be using sympify to handle string arguments from MatrixSymbol.

I don't even understand what the code is doing. Why does it omit the `+` when the first argument is negative? This seems to assume that the arguments of MatAdd have a certain form, and that they will always print a certain way if they are negative. 
