overescaped trailing underscore on attribute with napoleon
**Describe the bug**
Attribute name `hello_` shows up as `hello\_` in the html (visible backslash) with napoleon.

**To Reproduce**
Steps to reproduce the behavior:

empty `__init__.py`
`a.py` contains
```python
class A:
    """
    Attributes
    ----------
    hello_: int
        hi
    """
    pass
```
run `sphinx-quickstart`
add `'sphinx.ext.autodoc', 'sphinx.ext.napoleon'` to extensions in conf.py.
add `.. autoclass:: a.A` to index.rst
PYTHONPATH=. make clean html
open _build/html/index.html in web browser and see the ugly backslash.

**Expected behavior**
No backslash, a similar output to what I get for
```rst
    .. attribute:: hello_
        :type: int

        hi
```
(the type shows up differently as well, but that's not the point here)
Older versions like 2.4.3 look ok to me.

**Environment info**
- OS: Linux debian testing
- Python version: 3.8.3
- Sphinx version: 3.0.4
- Sphinx extensions:  sphinx.ext.autodoc, sphinx.ext.napoleon
- Extra tools:
