autodoc_type_aliases does not effect to variables and attributes
**Describe the bug**
autodoc_type_aliases does not effect to variables and attributes

**To Reproduce**

```
# example.py
from __future__ import annotations


#: blah blah blah
var: String


class MyString:
    "mystring"

    #: blah blah blah
    var: String
```
```
# index.rst
.. automodule:: example
   :members:
   :undoc-members:
```
```
# conf.py
autodoc_type_aliases = {
    'String': 'example.MyString'
}
```

**Expected behavior**
`autodoc_type_aliases` should be applied to `example.var` and `example.MyString.var`.

**Your project**
N/A

**Screenshots**
N/A

**Environment info**
- OS: Mac
- Python version: 3.9.0
- Sphinx version: HEAD of 3.x branch
- Sphinx extensions: sphinx.ext.autodoc
- Extra tools: Nothing

**Additional context**
N/A
