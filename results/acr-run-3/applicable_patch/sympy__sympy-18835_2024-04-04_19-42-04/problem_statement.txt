uniq modifies list argument
When you iterate over a dictionary or set and try to modify it while doing so you get an error from Python:
```python
>>> multiset('THISTLE')
{'T': 2, 'H': 1, 'I': 1, 'S': 1, 'L': 1, 'E': 1}
>>> for i in _:
...   _.pop(i)
...
2
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
RuntimeError: dictionary changed size during iteration
```
It would be good to do the same thing from within `uniq` because the output will silently be wrong if you modify a passed list:
```python
>>> f=list('THISTLE')
>>> for i in uniq(f):
...   f.remove(i)
...   i
...
'T'
'I'
'L'
```
I think this would entail recording the size at the start and then checking the size and raising a similar RuntimeError if the size changes.
