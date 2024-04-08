Rewrite fails when first expression of file is a number and mistaken as docstring 
<!--
Thanks for submitting an issue!

Quick check-list while reporting bugs:
-->

- [x] a detailed description of the bug or problem you are having
- [x] output of `pip list` from the virtual environment you are using
- [x] pytest and operating system versions
- [x] minimal example if possible
```
Installing collected packages: zipp, six, PyYAML, python-dateutil, MarkupSafe, importlib-metadata, watchdog, tomli, soupsieve, pyyaml-env-tag, pycparser, pluggy, packaging, mergedeep, Markdown, jinja2, iniconfig, ghp-import, exceptiongroup, click, websockets, urllib3, tqdm, smmap, pytest, pyee, mkdocs, lxml, importlib-resources, idna, cssselect, charset-normalizer, cffi, certifi, beautifulsoup4, attrs, appdirs, w3lib, typing-extensions, texttable, requests, pyzstd, pytest-metadata, pyquery, pyppmd, pyppeteer, pynacl, pymdown-extensions, pycryptodomex, pybcj, pyasn1, py, psutil, parse, multivolumefile, mkdocs-autorefs, inflate64, gitdb, fake-useragent, cryptography, comtypes, bs4, brotli, bcrypt, allure-python-commons, xlwt, xlrd, rsa, requests-html, pywinauto, python-i18n, python-dotenv, pytest-rerunfailures, pytest-html, pytest-check, PySocks, py7zr, paramiko, mkdocstrings, loguru, GitPython, ftputil, crcmod, chardet, brotlicffi, allure-pytest
Successfully installed GitPython-3.1.31 Markdown-3.3.7 MarkupSafe-2.1.3 PySocks-1.7.1 PyYAML-6.0 allure-pytest-2.13.2 allure-python-commons-2.13.2 appdirs-1.4.4 attrs-23.1.0 bcrypt-4.0.1 beautifulsoup4-4.12.2 brotli-1.0.9 brotlicffi-1.0.9.2 bs4-0.0.1 certifi-2023.5.7 cffi-1.15.1 chardet-5.1.0 charset-normalizer-3.1.0 click-8.1.3 comtypes-1.2.0 crcmod-1.7 cryptography-41.0.1 cssselect-1.2.0 exceptiongroup-1.1.1 fake-useragent-1.1.3 ftputil-5.0.4 ghp-import-2.1.0 gitdb-4.0.10 idna-3.4 importlib-metadata-6.7.0 importlib-resources-5.12.0 inflate64-0.3.1 iniconfig-2.0.0 jinja2-3.1.2 loguru-0.7.0 lxml-4.9.2 mergedeep-1.3.4 mkdocs-1.4.3 mkdocs-autorefs-0.4.1 mkdocstrings-0.22.0 multivolumefile-0.2.3 packaging-23.1 paramiko-3.2.0 parse-1.19.1 pluggy-1.2.0 psutil-5.9.5 py-1.11.0 py7zr-0.20.5 pyasn1-0.5.0 pybcj-1.0.1 pycparser-2.21 pycryptodomex-3.18.0 pyee-8.2.2 pymdown-extensions-10.0.1 pynacl-1.5.0 pyppeteer-1.0.2 pyppmd-1.0.0 pyquery-2.0.0 pytest-7.4.0 pytest-check-2.1.5 pytest-html-3.2.0 pytest-metadata-3.0.0 pytest-rerunfailures-11.1.2 python-dateutil-2.8.2 python-dotenv-1.0.0 python-i18n-0.3.9 pywinauto-0.6.6 pyyaml-env-tag-0.1 pyzstd-0.15.9 requests-2.31.0 requests-html-0.10.0 rsa-4.9 six-1.16.0 smmap-5.0.0 soupsieve-2.4.1 texttable-1.6.7 tomli-2.0.1 tqdm-4.65.0 typing-extensions-4.6.3 urllib3-1.26.16 w3lib-2.1.1 watchdog-3.0.0 websockets-10.4 xlrd-2.0.1 xlwt-1.3.0 zipp-3.15.0
```
use `pytest -k xxx`， report an error：`TypeError: argument of type 'int' is not iterable`

it seems a error in collecting testcase
```
==================================== ERRORS ====================================
_ ERROR collecting testcases/基线/代理策略/SOCKS二级代理迭代二/在线用户/在线用户更新/上线用户/test_socks_user_011.py _
/usr/local/lib/python3.8/site-packages/_pytest/runner.py:341: in from_call
    result: Optional[TResult] = func()
/usr/local/lib/python3.8/site-packages/_pytest/runner.py:372: in <lambda>
    call = CallInfo.from_call(lambda: list(collector.collect()), "collect")
/usr/local/lib/python3.8/site-packages/_pytest/python.py:531: in collect
    self._inject_setup_module_fixture()
/usr/local/lib/python3.8/site-packages/_pytest/python.py:545: in _inject_setup_module_fixture
    self.obj, ("setUpModule", "setup_module")
/usr/local/lib/python3.8/site-packages/_pytest/python.py:310: in obj
    self._obj = obj = self._getobj()
/usr/local/lib/python3.8/site-packages/_pytest/python.py:528: in _getobj
    return self._importtestmodule()
/usr/local/lib/python3.8/site-packages/_pytest/python.py:617: in _importtestmodule
    mod = import_path(self.path, mode=importmode, root=self.config.rootpath)
/usr/local/lib/python3.8/site-packages/_pytest/pathlib.py:565: in import_path
    importlib.import_module(module_name)
/usr/local/lib/python3.8/importlib/__init__.py:127: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
<frozen importlib._bootstrap>:1014: in _gcd_import
    ???
<frozen importlib._bootstrap>:991: in _find_and_load
    ???
<frozen importlib._bootstrap>:975: in _find_and_load_unlocked
    ???
<frozen importlib._bootstrap>:671: in _load_unlocked
    ???
/usr/local/lib/python3.8/site-packages/_pytest/assertion/rewrite.py:169: in exec_module
    source_stat, co = _rewrite_test(fn, self.config)
/usr/local/lib/python3.8/site-packages/_pytest/assertion/rewrite.py:352: in _rewrite_test
    rewrite_asserts(tree, source, strfn, config)
/usr/local/lib/python3.8/site-packages/_pytest/assertion/rewrite.py:413: in rewrite_asserts
    AssertionRewriter(module_path, config, source).run(mod)
/usr/local/lib/python3.8/site-packages/_pytest/assertion/rewrite.py:695: in run
    if self.is_rewrite_disabled(doc):
/usr/local/lib/python3.8/site-packages/_pytest/assertion/rewrite.py:760: in is_rewrite_disabled
    return "PYTEST_DONT_REWRITE" in docstring
E   TypeError: argument of type 'int' is not iterable
```
