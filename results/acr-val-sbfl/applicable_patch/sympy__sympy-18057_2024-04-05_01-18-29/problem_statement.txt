Sympy incorrectly attempts to eval reprs in its __eq__ method
Passing strings produced by unknown objects into eval is **very bad**. It is especially surprising for an equality check to trigger that kind of behavior. This should be fixed ASAP.

Repro code:

```
import sympy
class C:
    def __repr__(self):
        return 'x.y'
_ = sympy.Symbol('x') == C()
```

Results in:

```
E   AttributeError: 'Symbol' object has no attribute 'y'
```

On the line:

```
    expr = eval(
        code, global_dict, local_dict)  # take local objects in preference
```

Where code is:

```
Symbol ('x' ).y
```

Full trace:

```
FAILED                   [100%]
        class C:
            def __repr__(self):
                return 'x.y'
    
>       _ = sympy.Symbol('x') == C()

_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
sympy/core/expr.py:124: in __eq__
    other = sympify(other)
sympy/core/sympify.py:385: in sympify
    expr = parse_expr(a, local_dict=locals, transformations=transformations, evaluate=evaluate)
sympy/parsing/sympy_parser.py:1011: in parse_expr
    return eval_expr(code, local_dict, global_dict)
sympy/parsing/sympy_parser.py:906: in eval_expr
    code, global_dict, local_dict)  # take local objects in preference
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

>   ???
E   AttributeError: 'Symbol' object has no attribute 'y'

<string>:1: AttributeError
```

Related issue: an unknown object whose repr is `x` will incorrectly compare as equal to a sympy symbol x:

```
    class C:
        def __repr__(self):
            return 'x'

    assert sympy.Symbol('x') != C()  # fails
```
