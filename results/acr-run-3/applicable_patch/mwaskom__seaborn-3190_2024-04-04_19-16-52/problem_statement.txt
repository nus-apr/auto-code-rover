Color mapping fails with boolean data
```python
so.Plot(["a", "b"], [1, 2], color=[True, False]).add(so.Bar())
```
```python-traceback
---------------------------------------------------------------------------
TypeError                                 Traceback (most recent call last)
...
File ~/code/seaborn/seaborn/_core/plot.py:841, in Plot._plot(self, pyplot)
    838 plotter._compute_stats(self, layers)
    840 # Process scale spec for semantic variables and coordinates computed by stat
--> 841 plotter._setup_scales(self, common, layers)
    843 # TODO Remove these after updating other methods
    844 # ---- Maybe have debug= param that attaches these when True?
    845 plotter._data = common

File ~/code/seaborn/seaborn/_core/plot.py:1252, in Plotter._setup_scales(self, p, common, layers, variables)
   1250     self._scales[var] = Scale._identity()
   1251 else:
-> 1252     self._scales[var] = scale._setup(var_df[var], prop)
   1254 # Everything below here applies only to coordinate variables
   1255 # We additionally skip it when we're working with a value
   1256 # that is derived from a coordinate we've already processed.
   1257 # e.g., the Stat consumed y and added ymin/ymax. In that case,
   1258 # we've already setup the y scale and ymin/max are in scale space.
   1259 if axis is None or (var != coord and coord in p._variables):

File ~/code/seaborn/seaborn/_core/scales.py:351, in ContinuousBase._setup(self, data, prop, axis)
    349 vmin, vmax = axis.convert_units((vmin, vmax))
    350 a = forward(vmin)
--> 351 b = forward(vmax) - forward(vmin)
    353 def normalize(x):
    354     return (x - a) / b

TypeError: numpy boolean subtract, the `-` operator, is not supported, use the bitwise_xor, the `^` operator, or the logical_xor function instead.
```
