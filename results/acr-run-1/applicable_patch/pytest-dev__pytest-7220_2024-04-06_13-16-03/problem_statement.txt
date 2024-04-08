Wrong path to test file when directory changed in fixture
Files are shown as relative to new directory when working directory is changed in a fixture. This makes it impossible to jump to the error as the editor is unaware of the directory change. The displayed directory should stay relative to the original directory.

test_path_error.py:
```python
import os
import errno
import shutil

import pytest


@pytest.fixture
def private_dir():  # or (monkeypatch)
    out_dir = 'ddd'

    try:
        shutil.rmtree(out_dir)
    except OSError as ex:
        if ex.errno != errno.ENOENT:
            raise
    os.mkdir(out_dir)

    old_dir = os.getcwd()
    os.chdir(out_dir)
    yield out_dir
    os.chdir(old_dir)

    # Same issue if using:
    # monkeypatch.chdir(out_dir)


def test_show_wrong_path(private_dir):
    assert False
```

```diff
+ Expected: test_path_error.py:29: AssertionError
- Displayed: ../test_path_error.py:29: AssertionError
```

The full output is:
```
-*- mode: compilation; default-directory: "~/src/pytest_path_error/" -*-
Compilation started at Fri Jan 10 00:05:52

nox
nox > Running session test
nox > Creating virtual environment (virtualenv) using python3.7 in .nox/test
nox > pip install pytest>=5.3
nox > pip freeze
attrs==19.3.0
importlib-metadata==1.3.0
more-itertools==8.0.2
packaging==20.0
pluggy==0.13.1
py==1.8.1
pyparsing==2.4.6
pytest==5.3.2
six==1.13.0
wcwidth==0.1.8
zipp==0.6.0
nox > pytest 
================================= test session starts =================================
platform linux -- Python 3.7.5, pytest-5.3.2, py-1.8.1, pluggy-0.13.1
rootdir: /home/lhn/src/pytest_path_error
collected 1 item                                                                      

test_path_error.py F                                                            [100%]

====================================== FAILURES =======================================
________________________________ test_show_wrong_path _________________________________

private_dir = 'ddd'

    def test_show_wrong_path(private_dir):
>       assert False
E       assert False

../test_path_error.py:29: AssertionError
================================== 1 failed in 0.03s ==================================
nox > Command pytest  failed with exit code 1
nox > Session test failed.

Compilation exited abnormally with code 1 at Fri Jan 10 00:06:01
```

noxfile.py:
```python
import nox

@nox.session(python='3.7')
def test(session):
    session.install('pytest>=5.3')
    session.run('pip', 'freeze')
    session.run('pytest')
```
