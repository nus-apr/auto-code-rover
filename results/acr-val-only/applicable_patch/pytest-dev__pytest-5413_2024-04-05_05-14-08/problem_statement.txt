str() on the pytest.raises context variable doesn't behave same as normal exception catch
Pytest 4.6.2, macOS 10.14.5

```Python
try:
    raise LookupError(
        f"A\n"
        f"B\n"
        f"C"
    )
except LookupError as e:
    print(str(e))
```
prints

> A
> B
> C

But

```Python
with pytest.raises(LookupError) as e:
    raise LookupError(
        f"A\n"
        f"B\n"
        f"C"
    )

print(str(e))
```

prints

> <console>:3: LookupError: A

In order to get the full error message, one must do `str(e.value)`, which is documented, but this is a different interaction. Any chance the behavior could be changed to eliminate this gotcha?

-----

Pip list gives

```
Package            Version  Location
------------------ -------- ------------------------------------------------------
apipkg             1.5
asn1crypto         0.24.0
atomicwrites       1.3.0
attrs              19.1.0
aws-xray-sdk       0.95
boto               2.49.0
boto3              1.9.51
botocore           1.12.144
certifi            2019.3.9
cffi               1.12.3
chardet            3.0.4
Click              7.0
codacy-coverage    1.3.11
colorama           0.4.1
coverage           4.5.3
cryptography       2.6.1
decorator          4.4.0
docker             3.7.2
docker-pycreds     0.4.0
docutils           0.14
ecdsa              0.13.2
execnet            1.6.0
future             0.17.1
idna               2.8
importlib-metadata 0.17
ipaddress          1.0.22
Jinja2             2.10.1
jmespath           0.9.4
jsondiff           1.1.1
jsonpickle         1.1
jsonschema         2.6.0
MarkupSafe         1.1.1
mock               3.0.4
more-itertools     7.0.0
moto               1.3.7
neobolt            1.7.10
neotime            1.7.4
networkx           2.1
numpy              1.15.0
packaging          19.0
pandas             0.24.2
pip                19.1.1
pluggy             0.12.0
prompt-toolkit     2.0.9
py                 1.8.0
py2neo             4.2.0
pyaml              19.4.1
pycodestyle        2.5.0
pycparser          2.19
pycryptodome       3.8.1
Pygments           2.3.1
pyOpenSSL          19.0.0
pyparsing          2.4.0
pytest             4.6.2
pytest-cache       1.0
pytest-codestyle   1.4.0
pytest-cov         2.6.1
pytest-forked      1.0.2
python-dateutil    2.7.3
python-jose        2.0.2
pytz               2018.5
PyYAML             5.1
requests           2.21.0
requests-mock      1.5.2
responses          0.10.6
s3transfer         0.1.13
setuptools         41.0.1
six                1.11.0
sqlite3worker      1.1.7
tabulate           0.8.3
urllib3            1.24.3
wcwidth            0.1.7
websocket-client   0.56.0
Werkzeug           0.15.2
wheel              0.33.1
wrapt              1.11.1
xlrd               1.1.0
xmltodict          0.12.0
zipp               0.5.1
```
