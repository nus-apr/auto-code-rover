Sum of the elements of an identity matrix is zero
I think this is a bug.

I created a matrix by M.T * M under an assumption that M is orthogonal.  SymPy successfully recognized that the result is an identity matrix.  I tested its identity-ness by element-wise, queries, and sum of the diagonal elements and received expected results.

However, when I attempt to evaluate the total sum of the elements the result was 0 while 'n' is expected.

```
from sympy import *
from sympy import Q as Query

n = Symbol('n', integer=True, positive=True)
i, j = symbols('i j', integer=True)
M = MatrixSymbol('M', n, n)

e = None
with assuming(Query.orthogonal(M)):
    e = refine((M.T * M).doit())

# Correct: M.T * M is an identity matrix.
print(e, e[0, 0], e[0, 1], e[1, 0], e[1, 1])

# Correct: The output is True True
print(ask(Query.diagonal(e)), ask(Query.integer_elements(e)))

# Correct: The sum of the diagonal elements is n
print(Sum(e[i, i], (i, 0, n-1)).doit())

# So far so good
# Total sum of the elements is expected to be 'n' but the answer is 0!
print(Sum(Sum(e[i, j], (i, 0, n-1)), (j, 0, n-1)).doit())
```
