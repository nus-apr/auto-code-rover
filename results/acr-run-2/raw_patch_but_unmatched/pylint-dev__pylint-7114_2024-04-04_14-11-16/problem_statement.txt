Linting fails if module contains module of the same name
### Steps to reproduce

Given multiple files:
```
.
`-- a/
    |-- a.py
    `-- b.py
```
Which are all empty, running `pylint a` fails:

```
$ pylint a
************* Module a
a/__init__.py:1:0: F0010: error while code parsing: Unable to load file a/__init__.py:
[Errno 2] No such file or directory: 'a/__init__.py' (parse-error)
$
```

However, if I rename `a.py`, `pylint a` succeeds:

```
$ mv a/a.py a/c.py
$ pylint a
$
```
Alternatively, I can also `touch a/__init__.py`, but that shouldn't be necessary anymore.

### Current behavior

Running `pylint a` if `a/a.py` is present fails while searching for an `__init__.py` file.

### Expected behavior

Running `pylint a` if `a/a.py` is present should succeed.

### pylint --version output

Result of `pylint --version` output:

```
pylint 3.0.0a3
astroid 2.5.6
Python 3.8.5 (default, Jan 27 2021, 15:41:15) 
[GCC 9.3.0]
```

### Additional info

This also has some side-effects in module resolution. For example, if I create another file `r.py`:

```
.
|-- a
|   |-- a.py
|   `-- b.py
`-- r.py
```

With the content:

```
from a import b
```

Running `pylint -E r` will run fine, but `pylint -E r a` will fail. Not just for module a, but for module r as well.

```
************* Module r
r.py:1:0: E0611: No name 'b' in module 'a' (no-name-in-module)
************* Module a
a/__init__.py:1:0: F0010: error while code parsing: Unable to load file a/__init__.py:
[Errno 2] No such file or directory: 'a/__init__.py' (parse-error)
```

Again, if I rename `a.py` to `c.py`, `pylint -E r a` will work perfectly.
