Error creating AxisGrid with non-default axis class
<!--To help us understand and resolve your issue, please fill out the form to the best of your ability.-->
<!--You can feel free to delete the sections that do not apply.-->

### Bug report

**Bug summary**

Creating `AxesGrid` using cartopy `GeoAxes` as `axis_class` raises `TypeError: 'method' object is not subscriptable`. Seems to be due to different behaviour of `axis` attr. for `mpl_toolkits.axes_grid1.mpl_axes.Axes` and other axes instances (like `GeoAxes`) where `axis` is only a callable. The error is raised in method `mpl_toolkits.axes_grid1.axes_grid._tick_only` when trying to access keys from `axis` attr.

**Code for reproduction**

<!--A minimum code snippet required to reproduce the bug.
Please make sure to minimize the number of dependencies required, and provide
any necessary plotted data.
Avoid using threads, as Matplotlib is (explicitly) not thread-safe.-->

```python
import matplotlib.pyplot as plt
from cartopy.crs import PlateCarree
from cartopy.mpl.geoaxes import GeoAxes
from mpl_toolkits.axes_grid1 import AxesGrid

fig = plt.figure()
axes_class = (GeoAxes, dict(map_projection=PlateCarree()))
gr = AxesGrid(fig, 111, nrows_ncols=(1,1),
              axes_class=axes_class)
```

**Actual outcome**

<!--The output produced by the above code, which may be a screenshot, console output, etc.-->

```
Traceback (most recent call last):

  File "/home/jonasg/stuff/bugreport_mpl_toolkits_AxesGrid.py", line 16, in <module>
    axes_class=axes_class)

  File "/home/jonasg/miniconda3/envs/pya/lib/python3.7/site-packages/mpl_toolkits/axes_grid1/axes_grid.py", line 618, in __init__
    self.set_label_mode(label_mode)

  File "/home/jonasg/miniconda3/envs/pya/lib/python3.7/site-packages/mpl_toolkits/axes_grid1/axes_grid.py", line 389, in set_label_mode
    _tick_only(ax, bottom_on=False, left_on=False)

  File "/home/jonasg/miniconda3/envs/pya/lib/python3.7/site-packages/mpl_toolkits/axes_grid1/axes_grid.py", line 27, in _tick_only
    ax.axis["bottom"].toggle(ticklabels=bottom_off, label=bottom_off)

TypeError: 'method' object is not subscriptable
```

**Expected outcome**

<!--A description of the expected outcome from the code snippet-->
<!--If this used to work in an earlier version of Matplotlib, please note the version it used to work on-->

**Matplotlib version**
<!--Please specify your platform and versions of the relevant libraries you are using:-->
  * Operating system: Ubuntu 18.04.4 LTS
  * Matplotlib version: 3.1.2 (conda-forge)
  * Matplotlib backend: Qt5Agg 
  * Python version: 3.7.6
  * Jupyter version (if applicable):
  * Other libraries: 

```
# Name                    Version                   Build  Channel
_libgcc_mutex             0.1                 conda_forge    conda-forge
_openmp_mutex             4.5                       0_gnu    conda-forge
alabaster                 0.7.12                   py37_0  
antlr-python-runtime      4.7.2                 py37_1001    conda-forge
argh                      0.26.2                   py37_0  
astroid                   2.3.3                    py37_0  
atomicwrites              1.3.0                    py37_1  
attrs                     19.3.0                     py_0    conda-forge
autopep8                  1.4.4                      py_0  
babel                     2.8.0                      py_0  
backcall                  0.1.0                    py37_0  
basemap                   1.2.1            py37hd759880_1    conda-forge
bleach                    3.1.0                    py37_0  
bokeh                     1.4.0                    py37_0    conda-forge
bzip2                     1.0.8                h516909a_2    conda-forge
ca-certificates           2019.11.28           hecc5488_0    conda-forge
cartopy                   0.17.0          py37hd759880_1006    conda-forge
certifi                   2019.11.28               py37_0    conda-forge
cf-units                  2.1.3            py37hc1659b7_0    conda-forge
cf_units                  2.0.1           py37h3010b51_1002    conda-forge
cffi                      1.13.2           py37h8022711_0    conda-forge
cftime                    1.0.4.2          py37hc1659b7_0    conda-forge
chardet                   3.0.4                 py37_1003    conda-forge
click                     7.0                        py_0    conda-forge
cloudpickle               1.2.2                      py_1    conda-forge
cryptography              2.8              py37h72c5cf5_1    conda-forge
curl                      7.65.3               hf8cf82a_0    conda-forge
cycler                    0.10.0                     py_2    conda-forge
cytoolz                   0.10.1           py37h516909a_0    conda-forge
dask                      2.9.2                      py_0    conda-forge
dask-core                 2.9.2                      py_0    conda-forge
dbus                      1.13.6               he372182_0    conda-forge
decorator                 4.4.1                      py_0  
defusedxml                0.6.0                      py_0  
diff-match-patch          20181111                   py_0  
distributed               2.9.3                      py_0    conda-forge
docutils                  0.16                     py37_0  
entrypoints               0.3                      py37_0  
expat                     2.2.5             he1b5a44_1004    conda-forge
flake8                    3.7.9                    py37_0  
fontconfig                2.13.1            h86ecdb6_1001    conda-forge
freetype                  2.10.0               he983fc9_1    conda-forge
fsspec                    0.6.2                      py_0    conda-forge
future                    0.18.2                   py37_0  
geonum                    1.4.4                      py_0    conda-forge
geos                      3.7.2                he1b5a44_2    conda-forge
gettext                   0.19.8.1          hc5be6a0_1002    conda-forge
glib                      2.58.3          py37h6f030ca_1002    conda-forge
gmp                       6.1.2                h6c8ec71_1  
gpxpy                     1.4.0                      py_0    conda-forge
gst-plugins-base          1.14.5               h0935bb2_0    conda-forge
gstreamer                 1.14.5               h36ae1b5_0    conda-forge
hdf4                      4.2.13            hf30be14_1003    conda-forge
hdf5                      1.10.5          nompi_h3c11f04_1104    conda-forge
heapdict                  1.0.1                      py_0    conda-forge
icu                       64.2                 he1b5a44_1    conda-forge
idna                      2.8                   py37_1000    conda-forge
imagesize                 1.2.0                      py_0  
importlib_metadata        1.4.0                    py37_0    conda-forge
intervaltree              3.0.2                      py_0  
ipykernel                 5.1.4            py37h39e3cac_0  
ipython                   7.11.1           py37h39e3cac_0  
ipython_genutils          0.2.0                    py37_0  
iris                      2.2.0                 py37_1003    conda-forge
isort                     4.3.21                   py37_0  
jedi                      0.14.1                   py37_0  
jeepney                   0.4.2                      py_0  
jinja2                    2.10.3                     py_0    conda-forge
jpeg                      9c                h14c3975_1001    conda-forge
json5                     0.8.5                      py_0  
jsonschema                3.2.0                    py37_0  
jupyter_client            5.3.4                    py37_0  
jupyter_core              4.6.1                    py37_0  
jupyterlab                1.2.5              pyhf63ae98_0  
jupyterlab_server         1.0.6                      py_0  
keyring                   21.1.0                   py37_0  
kiwisolver                1.1.0            py37hc9558a2_0    conda-forge
krb5                      1.16.4               h2fd8d38_0    conda-forge
latlon23                  1.0.7                      py_0    conda-forge
lazy-object-proxy         1.4.3            py37h7b6447c_0  
ld_impl_linux-64          2.33.1               h53a641e_7    conda-forge
libblas                   3.8.0               14_openblas    conda-forge
libcblas                  3.8.0               14_openblas    conda-forge
libclang                  9.0.1           default_hde54327_0    conda-forge
libcurl                   7.65.3               hda55be3_0    conda-forge
libedit                   3.1.20170329      hf8c457e_1001    conda-forge
libffi                    3.2.1             he1b5a44_1006    conda-forge
libgcc-ng                 9.2.0                h24d8f2e_2    conda-forge
libgfortran-ng            7.3.0                hdf63c60_4    conda-forge
libgomp                   9.2.0                h24d8f2e_2    conda-forge
libiconv                  1.15              h516909a_1005    conda-forge
liblapack                 3.8.0               14_openblas    conda-forge
libllvm9                  9.0.1                hc9558a2_0    conda-forge
libnetcdf                 4.7.3           nompi_h94020b1_100    conda-forge
libopenblas               0.3.7                h5ec1e0e_6    conda-forge
libpng                    1.6.37               hed695b0_0    conda-forge
libsodium                 1.0.16               h1bed415_0  
libspatialindex           1.9.3                he6710b0_0  
libssh2                   1.8.2                h22169c7_2    conda-forge
libstdcxx-ng              9.2.0                hdf63c60_2    conda-forge
libtiff                   4.1.0                hc3755c2_3    conda-forge
libuuid                   2.32.1            h14c3975_1000    conda-forge
libxcb                    1.13              h14c3975_1002    conda-forge
libxkbcommon              0.9.1                hebb1f50_0    conda-forge
libxml2                   2.9.10               hee79883_0    conda-forge
locket                    0.2.0                      py_2    conda-forge
lz4-c                     1.8.3             he1b5a44_1001    conda-forge
markupsafe                1.1.1            py37h516909a_0    conda-forge
matplotlib                3.1.2                    py37_1    conda-forge
matplotlib-base           3.1.2            py37h250f245_1    conda-forge
mccabe                    0.6.1                    py37_1  
mistune                   0.8.4            py37h7b6447c_0  
more-itertools            8.1.0                      py_0    conda-forge
msgpack-python            0.6.2            py37hc9558a2_0    conda-forge
nbconvert                 5.6.1                    py37_0  
nbformat                  5.0.4                      py_0  
nbsphinx                  0.5.1                      py_0    conda-forge
ncurses                   6.1               hf484d3e_1002    conda-forge
netcdf4                   1.5.3           nompi_py37hd35fb8e_102    conda-forge
notebook                  6.0.3                    py37_0  
nspr                      4.24                 he1b5a44_0    conda-forge
nss                       3.47                 he751ad9_0    conda-forge
numpy                     1.17.5           py37h95a1406_0    conda-forge
numpydoc                  0.9.2                      py_0  
olefile                   0.46                       py_0    conda-forge
openssl                   1.1.1d               h516909a_0    conda-forge
owslib                    0.19.0                     py_2    conda-forge
packaging                 20.0                       py_0    conda-forge
pandas                    0.25.3           py37hb3f55d8_0    conda-forge
pandoc                    2.2.3.2                       0  
pandocfilters             1.4.2                    py37_1  
parso                     0.6.0                      py_0  
partd                     1.1.0                      py_0    conda-forge
pathtools                 0.1.2                      py_1  
patsy                     0.5.1                      py_0    conda-forge
pcre                      8.43                 he1b5a44_0    conda-forge
pexpect                   4.8.0                    py37_0  
pickleshare               0.7.5                    py37_0  
pillow                    7.0.0            py37hefe7db6_0    conda-forge
pip                       20.0.1                   py37_0    conda-forge
pluggy                    0.13.0                   py37_0    conda-forge
proj4                     5.2.0             he1b5a44_1006    conda-forge
prometheus_client         0.7.1                      py_0  
prompt_toolkit            3.0.3                      py_0  
psutil                    5.6.7            py37h516909a_0    conda-forge
pthread-stubs             0.4               h14c3975_1001    conda-forge
ptyprocess                0.6.0                    py37_0  
py                        1.8.1                      py_0    conda-forge
pyaerocom                 0.9.0.dev5                dev_0    <develop>
pycodestyle               2.5.0                    py37_0  
pycparser                 2.19                     py37_1    conda-forge
pydocstyle                4.0.1                      py_0  
pyepsg                    0.4.0                      py_0    conda-forge
pyflakes                  2.1.1                    py37_0  
pygments                  2.5.2                      py_0  
pyinstrument              3.1.2                    pypi_0    pypi
pyinstrument-cext         0.2.2                    pypi_0    pypi
pykdtree                  1.3.1           py37hc1659b7_1002    conda-forge
pyke                      1.1.1                 py37_1001    conda-forge
pylint                    2.4.4                    py37_0  
pyopenssl                 19.1.0                   py37_0    conda-forge
pyparsing                 2.4.6                      py_0    conda-forge
pyproj                    1.9.6           py37h516909a_1002    conda-forge
pyqt                      5.12.3           py37hcca6a23_1    conda-forge
pyqt5-sip                 4.19.18                  pypi_0    pypi
pyqtwebengine             5.12.1                   pypi_0    pypi
pyrsistent                0.15.7           py37h7b6447c_0  
pyshp                     2.1.0                      py_0    conda-forge
pysocks                   1.7.1                    py37_0    conda-forge
pytest                    5.3.4                    py37_0    conda-forge
python                    3.7.6                h357f687_2    conda-forge
python-dateutil           2.8.1                      py_0    conda-forge
python-jsonrpc-server     0.3.4                      py_0  
python-language-server    0.31.7                   py37_0  
pytz                      2019.3                     py_0    conda-forge
pyxdg                     0.26                       py_0  
pyyaml                    5.3              py37h516909a_0    conda-forge
pyzmq                     18.1.0           py37he6710b0_0  
qdarkstyle                2.8                        py_0  
qt                        5.12.5               hd8c4c69_1    conda-forge
qtawesome                 0.6.1                      py_0  
qtconsole                 4.6.0                      py_1  
qtpy                      1.9.0                      py_0  
readline                  8.0                  hf8c457e_0    conda-forge
requests                  2.22.0                   py37_1    conda-forge
rope                      0.16.0                     py_0  
rtree                     0.9.3                    py37_0  
scipy                     1.4.1            py37h921218d_0    conda-forge
seaborn                   0.9.0                      py_2    conda-forge
secretstorage             3.1.2                    py37_0  
send2trash                1.5.0                    py37_0  
setuptools                45.1.0                   py37_0    conda-forge
shapely                   1.6.4           py37hec07ddf_1006    conda-forge
simplejson                3.17.0           py37h516909a_0    conda-forge
six                       1.14.0                   py37_0    conda-forge
snowballstemmer           2.0.0                      py_0  
sortedcontainers          2.1.0                      py_0    conda-forge
sphinx                    2.3.1                      py_0  
sphinx-rtd-theme          0.4.3                    pypi_0    pypi
sphinxcontrib-applehelp   1.0.1                      py_0  
sphinxcontrib-devhelp     1.0.1                      py_0  
sphinxcontrib-htmlhelp    1.0.2                      py_0  
sphinxcontrib-jsmath      1.0.1                      py_0  
sphinxcontrib-qthelp      1.0.2                      py_0  
sphinxcontrib-serializinghtml 1.1.3                      py_0  
spyder                    4.0.1                    py37_0  
spyder-kernels            1.8.1                    py37_0  
sqlite                    3.30.1               hcee41ef_0    conda-forge
srtm.py                   0.3.4                      py_0    conda-forge
statsmodels               0.11.0           py37h516909a_0    conda-forge
tblib                     1.6.0                      py_0    conda-forge
terminado                 0.8.3                    py37_0  
testpath                  0.4.4                      py_0  
tk                        8.6.10               hed695b0_0    conda-forge
toolz                     0.10.0                     py_0    conda-forge
tornado                   6.0.3            py37h516909a_0    conda-forge
tqdm                      4.43.0                   pypi_0    pypi
traitlets                 4.3.3                    py37_0  
udunits2                  2.2.27.6          h4e0c4b3_1001    conda-forge
ujson                     1.35             py37h14c3975_0  
urllib3                   1.25.7                   py37_0    conda-forge
watchdog                  0.9.0                    py37_1  
wcwidth                   0.1.8                      py_0    conda-forge
webencodings              0.5.1                    py37_1  
wheel                     0.33.6                   py37_0    conda-forge
wrapt                     1.11.2           py37h7b6447c_0  
wurlitzer                 2.0.0                    py37_0  
xarray                    0.14.1                     py_1    conda-forge
xorg-libxau               1.0.9                h14c3975_0    conda-forge
xorg-libxdmcp             1.1.3                h516909a_0    conda-forge
xz                        5.2.4             h14c3975_1001    conda-forge
yaml                      0.2.2                h516909a_1    conda-forge
yapf                      0.28.0                     py_0  
zeromq                    4.3.1                he6710b0_3  
zict                      1.0.0                      py_0    conda-forge
zipp                      2.0.0                      py_2    conda-forge
zlib                      1.2.11            h516909a_1006    conda-forge
zstd                      1.4.4                h3b9ef0a_1    conda-forge
```

