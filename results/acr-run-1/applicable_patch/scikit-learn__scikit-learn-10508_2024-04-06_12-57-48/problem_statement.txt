LabelEncoder transform fails for empty lists (for certain inputs)
Python 3.6.3, scikit_learn 0.19.1

Depending on which datatypes were used to fit the LabelEncoder, transforming empty lists works or not. Expected behavior would be that empty arrays are returned in both cases.

```python
>>> from sklearn.preprocessing import LabelEncoder
>>> le = LabelEncoder()
>>> le.fit([1,2])
LabelEncoder()
>>> le.transform([])
array([], dtype=int64)
>>> le.fit(["a","b"])
LabelEncoder()
>>> le.transform([])
Traceback (most recent call last):
  File "[...]\Python36\lib\site-packages\numpy\core\fromnumeric.py", line 57, in _wrapfunc
    return getattr(obj, method)(*args, **kwds)
TypeError: Cannot cast array data from dtype('float64') to dtype('<U32') according to the rule 'safe'

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "[...]\Python36\lib\site-packages\sklearn\preprocessing\label.py", line 134, in transform
    return np.searchsorted(self.classes_, y)
  File "[...]\Python36\lib\site-packages\numpy\core\fromnumeric.py", line 1075, in searchsorted
    return _wrapfunc(a, 'searchsorted', v, side=side, sorter=sorter)
  File "[...]\Python36\lib\site-packages\numpy\core\fromnumeric.py", line 67, in _wrapfunc
    return _wrapit(obj, method, *args, **kwds)
  File "[...]\Python36\lib\site-packages\numpy\core\fromnumeric.py", line 47, in _wrapit
    result = getattr(asarray(obj), method)(*args, **kwds)
TypeError: Cannot cast array data from dtype('float64') to dtype('<U32') according to the rule 'safe'
```
