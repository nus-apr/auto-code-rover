Improve handling of skip for module level
This is potentially about updating docs, updating error messages or introducing a new API.

Consider the following scenario:

`pos_only.py` is using Python 3,8 syntax:
```python
def foo(a, /, b):
    return a + b
```

It should not be tested under Python 3.6 and 3.7.
This is a proper way to skip the test in Python older than 3.8:
```python
from pytest import raises, skip
import sys
if sys.version_info < (3, 8):
    skip(msg="Requires Python >= 3.8", allow_module_level=True)

# import must be after the module level skip:
from pos_only import *

def test_foo():
    assert foo(10, 20) == 30
    assert foo(10, b=20) == 30
    with raises(TypeError):
        assert foo(a=10, b=20)
```

My actual test involves parameterize and a 3.8 only class, so skipping the test itself is not sufficient because the 3.8 class was used in the parameterization.

A naive user will try to initially skip the module like:

```python
if sys.version_info < (3, 8):
    skip(msg="Requires Python >= 3.8")
```
This issues this error:

>Using pytest.skip outside of a test is not allowed. To decorate a test function, use the @pytest.mark.skip or @pytest.mark.skipif decorators instead, and to skip a module use `pytestmark = pytest.mark.{skip,skipif}.

The proposed solution `pytestmark = pytest.mark.{skip,skipif}`, does not work  in my case: pytest continues to process the file and fail when it hits the 3.8 syntax (when running with an older version of Python).

The correct solution, to use skip as a function is actively discouraged by the error message.

This area feels a bit unpolished.
A few ideas to improve:

1. Explain skip with  `allow_module_level` in the error message. this seems in conflict with the spirit of the message.
2. Create an alternative API to skip a module to make things easier: `skip_module("reason")`, which can call `_skip(msg=msg, allow_module_level=True)`.


