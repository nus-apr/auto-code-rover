pairplot raises KeyError with MultiIndex DataFrame
When trying to pairplot a MultiIndex DataFrame, `pairplot` raises a `KeyError`:

MRE:

```python
import numpy as np
import pandas as pd
import seaborn as sns


data = {
    ("A", "1"): np.random.rand(100),
    ("A", "2"): np.random.rand(100),
    ("B", "1"): np.random.rand(100),
    ("B", "2"): np.random.rand(100),
}
df = pd.DataFrame(data)
sns.pairplot(df)
```

Output:

```
[c:\Users\KLuu\anaconda3\lib\site-packages\seaborn\axisgrid.py](file:///C:/Users/KLuu/anaconda3/lib/site-packages/seaborn/axisgrid.py) in pairplot(data, hue, hue_order, palette, vars, x_vars, y_vars, kind, diag_kind, markers, height, aspect, corner, dropna, plot_kws, diag_kws, grid_kws, size)
   2142     diag_kws.setdefault("legend", False)
   2143     if diag_kind == "hist":
-> 2144         grid.map_diag(histplot, **diag_kws)
   2145     elif diag_kind == "kde":
   2146         diag_kws.setdefault("fill", True)

[c:\Users\KLuu\anaconda3\lib\site-packages\seaborn\axisgrid.py](file:///C:/Users/KLuu/anaconda3/lib/site-packages/seaborn/axisgrid.py) in map_diag(self, func, **kwargs)
   1488                 plt.sca(ax)
   1489 
-> 1490             vector = self.data[var]
   1491             if self._hue_var is not None:
   1492                 hue = self.data[self._hue_var]

[c:\Users\KLuu\anaconda3\lib\site-packages\pandas\core\frame.py](file:///C:/Users/KLuu/anaconda3/lib/site-packages/pandas/core/frame.py) in __getitem__(self, key)
   3765             if is_iterator(key):
   3766                 key = list(key)
-> 3767             indexer = self.columns._get_indexer_strict(key, "columns")[1]
   3768 
   3769         # take() does not accept boolean indexers

[c:\Users\KLuu\anaconda3\lib\site-packages\pandas\core\indexes\multi.py](file:///C:/Users/KLuu/anaconda3/lib/site-packages/pandas/core/indexes/multi.py) in _get_indexer_strict(self, key, axis_name)
   2534             indexer = self._get_indexer_level_0(keyarr)
   2535 
-> 2536             self._raise_if_missing(key, indexer, axis_name)
   2537             return self[indexer], indexer
   2538 

[c:\Users\KLuu\anaconda3\lib\site-packages\pandas\core\indexes\multi.py](file:///C:/Users/KLuu/anaconda3/lib/site-packages/pandas/core/indexes/multi.py) in _raise_if_missing(self, key, indexer, axis_name)
   2552                 cmask = check == -1
   2553                 if cmask.any():
-> 2554                     raise KeyError(f"{keyarr[cmask]} not in index")
   2555                 # We get here when levels still contain values which are not
   2556                 # actually in Index anymore

KeyError: "['1'] not in index"
```

A workaround is to "flatten" the columns:

```python
df.columns = ["".join(column) for column in df.columns]
```
