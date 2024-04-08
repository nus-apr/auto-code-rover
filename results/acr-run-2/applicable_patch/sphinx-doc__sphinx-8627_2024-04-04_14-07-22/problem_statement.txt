autodoc isn't able to resolve struct.Struct type annotations
**Describe the bug**
If `struct.Struct` is declared in any type annotations, I get `class reference target not found: Struct`

**To Reproduce**
Simple `index.rst`
```
Hello World
===========

code docs
=========

.. automodule:: helloworld.helloworld
```

Simple `helloworld.py`
```
import struct
import pathlib

def consume_struct(_: struct.Struct) -> None:
    pass

def make_struct() -> struct.Struct:
    mystruct = struct.Struct('HH')
    return mystruct

def make_path() -> pathlib.Path:
    return pathlib.Path()
```

Command line:
```
python3 -m sphinx -b html docs/ doc-out -nvWT
```

**Expected behavior**
If you comment out the 2 functions that have `Struct` type annotations, you'll see that `pathlib.Path` resolves fine and shows up in the resulting documentation. I'd expect that `Struct` would also resolve correctly.

**Your project**
n/a

**Screenshots**
n/a

**Environment info**
- OS: Ubuntu 18.04, 20.04
- Python version: 3.8.2
- Sphinx version: 3.2.1
- Sphinx extensions:  'sphinx.ext.autodoc',
              'sphinx.ext.autosectionlabel',
              'sphinx.ext.intersphinx',
              'sphinx.ext.doctest',
              'sphinx.ext.todo'
- Extra tools: 

**Additional context**


- [e.g. URL or Ticket]


