Module imported twice under import-mode=importlib
In pmxbot/pmxbot@7f189ad, I'm attempting to switch pmxbot off of pkg_resources style namespace packaging to PEP 420 namespace packages. To do so, I've needed to switch to `importlib` for the `import-mode` and re-organize the tests to avoid import errors on the tests.

Yet even after working around these issues, the tests are failing when the effect of `core.initialize()` doesn't seem to have had any effect.

Investigating deeper, I see that initializer is executed and performs its actions (setting a class variable `pmxbot.logging.Logger.store`), but when that happens, there are two different versions of `pmxbot.logging` present, one in `sys.modules` and another found in `tests.unit.test_commands.logging`:

```
=========================================================================== test session starts ===========================================================================
platform darwin -- Python 3.11.1, pytest-7.2.0, pluggy-1.0.0
cachedir: .tox/python/.pytest_cache
rootdir: /Users/jaraco/code/pmxbot/pmxbot, configfile: pytest.ini
plugins: black-0.3.12, mypy-0.10.3, jaraco.test-5.3.0, checkdocs-2.9.0, flake8-1.1.1, enabler-2.0.0, jaraco.mongodb-11.2.1, pmxbot-1122.14.3.dev13+g7f189ad
collected 421 items / 180 deselected / 241 selected                                                                                                                       
run-last-failure: rerun previous 240 failures (skipped 14 files)

tests/unit/test_commands.py E
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> traceback >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

cls = <class 'tests.unit.test_commands.TestCommands'>

    @classmethod
    def setup_class(cls):
        path = os.path.dirname(os.path.abspath(__file__))
        configfile = os.path.join(path, 'testconf.yaml')
        config = pmxbot.dictlib.ConfigDict.from_yaml(configfile)
        cls.bot = core.initialize(config)
>       logging.Logger.store.message("logged", "testrunner", "some text")
E       AttributeError: type object 'Logger' has no attribute 'store'

tests/unit/test_commands.py:37: AttributeError
>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> entering PDB >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> PDB post_mortem (IO-capturing turned off) >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
> /Users/jaraco/code/pmxbot/pmxbot/tests/unit/test_commands.py(37)setup_class()
-> logging.Logger.store.message("logged", "testrunner", "some text")
(Pdb) logging.Logger
<class 'pmxbot.logging.Logger'>
(Pdb) logging
<module 'pmxbot.logging' from '/Users/jaraco/code/pmxbot/pmxbot/pmxbot/logging.py'>
(Pdb) import sys
(Pdb) sys.modules['pmxbot.logging']
<module 'pmxbot.logging' from '/Users/jaraco/code/pmxbot/pmxbot/pmxbot/logging.py'>
(Pdb) sys.modules['pmxbot.logging'] is logging
False
```

I haven't yet made a minimal reproducer, but I wanted to first capture this condition.

