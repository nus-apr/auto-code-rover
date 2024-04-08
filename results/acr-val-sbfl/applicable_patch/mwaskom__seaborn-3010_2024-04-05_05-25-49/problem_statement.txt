PolyFit is not robust to missing data
```python
so.Plot([1, 2, 3, None, 4], [1, 2, 3, 4, 5]).add(so.Line(), so.PolyFit())
```

<details><summary>Traceback</summary>

```python-traceback
---------------------------------------------------------------------------
LinAlgError                               Traceback (most recent call last)
File ~/miniconda3/envs/seaborn-py39-latest/lib/python3.9/site-packages/IPython/core/formatters.py:343, in BaseFormatter.__call__(self, obj)
    341     method = get_real_method(obj, self.print_method)
    342     if method is not None:
--> 343         return method()
    344     return None
    345 else:

File ~/code/seaborn/seaborn/_core/plot.py:265, in Plot._repr_png_(self)
    263 def _repr_png_(self) -> tuple[bytes, dict[str, float]]:
--> 265     return self.plot()._repr_png_()

File ~/code/seaborn/seaborn/_core/plot.py:804, in Plot.plot(self, pyplot)
    800 """
    801 Compile the plot spec and return the Plotter object.
    802 """
    803 with theme_context(self._theme_with_defaults()):
--> 804     return self._plot(pyplot)

File ~/code/seaborn/seaborn/_core/plot.py:822, in Plot._plot(self, pyplot)
    819 plotter._setup_scales(self, common, layers, coord_vars)
    821 # Apply statistical transform(s)
--> 822 plotter._compute_stats(self, layers)
    824 # Process scale spec for semantic variables and coordinates computed by stat
    825 plotter._setup_scales(self, common, layers)

File ~/code/seaborn/seaborn/_core/plot.py:1110, in Plotter._compute_stats(self, spec, layers)
   1108     grouper = grouping_vars
   1109 groupby = GroupBy(grouper)
-> 1110 res = stat(df, groupby, orient, scales)
   1112 if pair_vars:
   1113     data.frames[coord_vars] = res

File ~/code/seaborn/seaborn/_stats/regression.py:41, in PolyFit.__call__(self, data, groupby, orient, scales)
     39 def __call__(self, data, groupby, orient, scales):
---> 41     return groupby.apply(data, self._fit_predict)

File ~/code/seaborn/seaborn/_core/groupby.py:109, in GroupBy.apply(self, data, func, *args, **kwargs)
    106 grouper, groups = self._get_groups(data)
    108 if not grouper:
--> 109     return self._reorder_columns(func(data, *args, **kwargs), data)
    111 parts = {}
    112 for key, part_df in data.groupby(grouper, sort=False):

File ~/code/seaborn/seaborn/_stats/regression.py:30, in PolyFit._fit_predict(self, data)
     28     xx = yy = []
     29 else:
---> 30     p = np.polyfit(x, y, self.order)
     31     xx = np.linspace(x.min(), x.max(), self.gridsize)
     32     yy = np.polyval(p, xx)

File <__array_function__ internals>:180, in polyfit(*args, **kwargs)

File ~/miniconda3/envs/seaborn-py39-latest/lib/python3.9/site-packages/numpy/lib/polynomial.py:668, in polyfit(x, y, deg, rcond, full, w, cov)
    666 scale = NX.sqrt((lhs*lhs).sum(axis=0))
    667 lhs /= scale
--> 668 c, resids, rank, s = lstsq(lhs, rhs, rcond)
    669 c = (c.T/scale).T  # broadcast scale coefficients
    671 # warn on rank reduction, which indicates an ill conditioned matrix

File <__array_function__ internals>:180, in lstsq(*args, **kwargs)

File ~/miniconda3/envs/seaborn-py39-latest/lib/python3.9/site-packages/numpy/linalg/linalg.py:2300, in lstsq(a, b, rcond)
   2297 if n_rhs == 0:
   2298     # lapack can't handle n_rhs = 0 - so allocate the array one larger in that axis
   2299     b = zeros(b.shape[:-2] + (m, n_rhs + 1), dtype=b.dtype)
-> 2300 x, resids, rank, s = gufunc(a, b, rcond, signature=signature, extobj=extobj)
   2301 if m == 0:
   2302     x[...] = 0

File ~/miniconda3/envs/seaborn-py39-latest/lib/python3.9/site-packages/numpy/linalg/linalg.py:101, in _raise_linalgerror_lstsq(err, flag)
    100 def _raise_linalgerror_lstsq(err, flag):
--> 101     raise LinAlgError("SVD did not converge in Linear Least Squares")

LinAlgError: SVD did not converge in Linear Least Squares

```

</details>
