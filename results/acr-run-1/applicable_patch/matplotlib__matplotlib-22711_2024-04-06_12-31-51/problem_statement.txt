[Bug]: cannot give init value for RangeSlider widget
### Bug summary

I think `xy[4] = .25, val[0]` should be commented in /matplotlib/widgets. py", line 915, in set_val
as it prevents to initialized value for RangeSlider

### Code for reproduction

```python
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import RangeSlider

# generate a fake image
np.random.seed(19680801)
N = 128
img = np.random.randn(N, N)

fig, axs = plt.subplots(1, 2, figsize=(10, 5))
fig.subplots_adjust(bottom=0.25)

im = axs[0].imshow(img)
axs[1].hist(img.flatten(), bins='auto')
axs[1].set_title('Histogram of pixel intensities')

# Create the RangeSlider
slider_ax = fig.add_axes([0.20, 0.1, 0.60, 0.03])
slider = RangeSlider(slider_ax, "Threshold", img.min(), img.max(),valinit=[0.0,0.0])

# Create the Vertical lines on the histogram
lower_limit_line = axs[1].axvline(slider.val[0], color='k')
upper_limit_line = axs[1].axvline(slider.val[1], color='k')


def update(val):
    # The val passed to a callback by the RangeSlider will
    # be a tuple of (min, max)

    # Update the image's colormap
    im.norm.vmin = val[0]
    im.norm.vmax = val[1]

    # Update the position of the vertical lines
    lower_limit_line.set_xdata([val[0], val[0]])
    upper_limit_line.set_xdata([val[1], val[1]])

    # Redraw the figure to ensure it updates
    fig.canvas.draw_idle()


slider.on_changed(update)
plt.show()
```


### Actual outcome

```python
  File "<ipython-input-52-b704c53e18d4>", line 19, in <module>
    slider = RangeSlider(slider_ax, "Threshold", img.min(), img.max(),valinit=[0.0,0.0])

  File "/Users/Vincent/opt/anaconda3/envs/py38/lib/python3.8/site-packages/matplotlib/widgets.py", line 778, in __init__
    self.set_val(valinit)

  File "/Users/Vincent/opt/anaconda3/envs/py38/lib/python3.8/site-packages/matplotlib/widgets.py", line 915, in set_val
    xy[4] = val[0], .25

IndexError: index 4 is out of bounds for axis 0 with size 4
```

### Expected outcome

range slider with user initial values

### Additional information

error can be removed by commenting this line
```python

    def set_val(self, val):
        """
        Set slider value to *val*.

        Parameters
        ----------
        val : tuple or array-like of float
        """
        val = np.sort(np.asanyarray(val))
        if val.shape != (2,):
            raise ValueError(
                f"val must have shape (2,) but has shape {val.shape}"
            )
        val[0] = self._min_in_bounds(val[0])
        val[1] = self._max_in_bounds(val[1])
        xy = self.poly.xy
        if self.orientation == "vertical":
            xy[0] = .25, val[0]
            xy[1] = .25, val[1]
            xy[2] = .75, val[1]
            xy[3] = .75, val[0]
            # xy[4] = .25, val[0]
        else:
            xy[0] = val[0], .25
            xy[1] = val[0], .75
            xy[2] = val[1], .75
            xy[3] = val[1], .25
            # xy[4] = val[0], .25
        self.poly.xy = xy
        self.valtext.set_text(self._format(val))
        if self.drawon:
            self.ax.figure.canvas.draw_idle()
        self.val = val
        if self.eventson:
            self._observers.process("changed", val)

```

### Operating system

OSX

### Matplotlib Version

3.5.1

### Matplotlib Backend

_No response_

### Python version

3.8

### Jupyter version

_No response_

### Installation

pip
