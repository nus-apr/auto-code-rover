Update colorbar after changing mappable.norm
How can I update a colorbar, after I changed the norm instance of the colorbar?

`colorbar.update_normal(mappable)` has now effect and `colorbar.update_bruteforce(mappable)` throws a `ZeroDivsionError`-Exception.

Consider this example:

``` python
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import numpy as np

img = 10**np.random.normal(1, 1, size=(50, 50))

fig, ax = plt.subplots(1, 1)
plot = ax.imshow(img, cmap='gray')
cb = fig.colorbar(plot, ax=ax)
plot.norm = LogNorm()
cb.update_normal(plot)  # no effect
cb.update_bruteforce(plot)  # throws ZeroDivisionError
plt.show()
```

Output for `cb.update_bruteforce(plot)`:

```
Traceback (most recent call last):
  File "test_norm.py", line 12, in <module>
    cb.update_bruteforce(plot)
  File "/home/maxnoe/.local/anaconda3/lib/python3.4/site-packages/matplotlib/colorbar.py", line 967, in update_bruteforce
    self.draw_all()
  File "/home/maxnoe/.local/anaconda3/lib/python3.4/site-packages/matplotlib/colorbar.py", line 342, in draw_all
    self._process_values()
  File "/home/maxnoe/.local/anaconda3/lib/python3.4/site-packages/matplotlib/colorbar.py", line 664, in _process_values
    b = self.norm.inverse(self._uniform_y(self.cmap.N + 1))
  File "/home/maxnoe/.local/anaconda3/lib/python3.4/site-packages/matplotlib/colors.py", line 1011, in inverse
    return vmin * ma.power((vmax / vmin), val)
ZeroDivisionError: division by zero
```

