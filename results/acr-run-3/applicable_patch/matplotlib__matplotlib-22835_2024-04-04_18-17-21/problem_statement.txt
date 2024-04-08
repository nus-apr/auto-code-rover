[Bug]: scalar mappable format_cursor_data crashes on BoundarNorm
### Bug summary

In 3.5.0 if you do:

```python
import matplotlib.pyplot as plt
import numpy as np
import matplotlib as mpl

fig, ax = plt.subplots()
norm = mpl.colors.BoundaryNorm(np.linspace(-4, 4, 5), 256)
X = np.random.randn(10, 10)
pc = ax.imshow(X, cmap='RdBu_r', norm=norm)
```

and mouse over the image, it crashes with

```
File "/Users/jklymak/matplotlib/lib/matplotlib/artist.py", line 1282, in format_cursor_data
    neighbors = self.norm.inverse(
  File "/Users/jklymak/matplotlib/lib/matplotlib/colors.py", line 1829, in inverse
    raise ValueError("BoundaryNorm is not invertible")
ValueError: BoundaryNorm is not invertible
```

and interaction stops.  

Not sure if we should have a special check here, a try-except, or actually just make BoundaryNorm approximately invertible.  


### Matplotlib Version

main 3.5.0


[Bug]: scalar mappable format_cursor_data crashes on BoundarNorm
### Bug summary

In 3.5.0 if you do:

```python
import matplotlib.pyplot as plt
import numpy as np
import matplotlib as mpl

fig, ax = plt.subplots()
norm = mpl.colors.BoundaryNorm(np.linspace(-4, 4, 5), 256)
X = np.random.randn(10, 10)
pc = ax.imshow(X, cmap='RdBu_r', norm=norm)
```

and mouse over the image, it crashes with

```
File "/Users/jklymak/matplotlib/lib/matplotlib/artist.py", line 1282, in format_cursor_data
    neighbors = self.norm.inverse(
  File "/Users/jklymak/matplotlib/lib/matplotlib/colors.py", line 1829, in inverse
    raise ValueError("BoundaryNorm is not invertible")
ValueError: BoundaryNorm is not invertible
```

and interaction stops.  

Not sure if we should have a special check here, a try-except, or actually just make BoundaryNorm approximately invertible.  


### Matplotlib Version

main 3.5.0


