is_upper() raises IndexError for tall matrices
The function Matrix.is_upper raises an IndexError for a 4x2 matrix of zeros.
```
>>> sympy.zeros(4,2).is_upper
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "sympy/matrices/matrices.py", line 1112, in is_upper
    for i in range(1, self.rows)
  File "sympy/matrices/matrices.py", line 1113, in <genexpr>
    for j in range(i))
  File "sympy/matrices/dense.py", line 119, in __getitem__
    return self.extract(i, j)
  File "sympy/matrices/matrices.py", line 352, in extract
    colsList = [a2idx(k, self.cols) for k in colsList]
  File "sympy/matrices/matrices.py", line 5261, in a2idx
    raise IndexError("Index out of range: a[%s]" % (j,))
IndexError: Index out of range: a[2]
```
The code for is_upper() is
```
        return all(self[i, j].is_zero
                   for i in range(1, self.rows)
                   for j in range(i))
```
For a 4x2 matrix, is_upper iterates over the indices:
```
>>> A = sympy.zeros(4, 2)
>>> print tuple([i, j] for i in range(1, A.rows) for j in range(i))
([1, 0], [2, 0], [2, 1], [3, 0], [3, 1], [3, 2])
```
The attempt to index the (3,2) entry appears to be the source of the error. 
