autowrap with cython backend fails when array arguments do not appear in wrapped expr
When using the cython backend for autowrap, it appears that the code is not correctly generated when the function in question has array arguments that do not appear in the final expression. A minimal counterexample is:

```python
from sympy.utilities.autowrap import autowrap
from sympy import MatrixSymbol
import numpy as np

x = MatrixSymbol('x', 2, 1)
expr = 1.0
f = autowrap(expr, args=(x,), backend='cython')

f(np.array([[1.0, 2.0]]))
```

This should of course return `1.0` but instead fails with:
```python
TypeError: only size-1 arrays can be converted to Python scalars
```

A little inspection reveals that this is because the corresponding C function is generated with an incorrect signature:

```C
double autofunc(double x) {

   double autofunc_result;
   autofunc_result = 1.0;
   return autofunc_result;

}
```

(`x` should be `double *`, not `double` in this case)

I've found that this error won't occur so long as `expr` depends at least in part on each argument. For example this slight modification of the above counterexample works perfectly:

```python
from sympy.utilities.autowrap import autowrap
from sympy import MatrixSymbol
import numpy as np

x = MatrixSymbol('x', 2, 1)
# now output depends on x
expr = x[0,0]
f = autowrap(expr, args=(x,), backend='cython')

# returns 1.0 as expected, without failure
f(np.array([[1.0, 2.0]]))
```

This may seem like a silly issue ("why even have `x` as an argument if it doesn't appear in the expression you're trying to evaluate?"). But of course in interfacing with external libraries (e.g. for numerical integration), one often needs functions to have a pre-defined signature regardless of whether a given argument contributes to the output.

I think I've identified the problem in `codegen` and will suggest a PR shortly.
