Python 2->3 pickle fails with float-containing expressions
Dumping a pickled sympy expression containing a float in Python 2, then loading it in Python 3 generates an error.

Here is a minimum working example, verified with sympy git commit 3546ac7 (master at time of writing), Python 2.7 and Python 3.6:

```python
python2 -c 'import pickle; import sympy; x = sympy.symbols("x"); print pickle.dumps(x + 1.0, 2)' | python3 -c 'import pickle; import sys; print(pickle.loads(sys.stdin.buffer.read()))'
```

and the result:

```
Traceback (most recent call last):
  File "<string>", line 1, in <module>
  File "/Users/alex/git/VU/sympy/sympy/core/numbers.py", line 1045, in __new__
    num[1] = long(num[1], 16)
ValueError: invalid literal for int() with base 16: '1L'
```
