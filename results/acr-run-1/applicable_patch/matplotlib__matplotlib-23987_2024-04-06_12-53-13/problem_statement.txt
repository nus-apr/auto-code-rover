[Bug]: Constrained layout UserWarning even when False
### Bug summary

When using layout settings such as `plt.subplots_adjust` or `bbox_inches='tight`, a UserWarning is produced due to incompatibility with constrained_layout, even if constrained_layout = False. This was not the case in previous versions.

### Code for reproduction

```python
import matplotlib.pyplot as plt
import numpy as np
a = np.linspace(0,2*np.pi,100)
b = np.sin(a)
c = np.cos(a)
fig,ax = plt.subplots(1,2,figsize=(8,2),constrained_layout=False)
ax[0].plot(a,b)
ax[1].plot(a,c)
plt.subplots_adjust(wspace=0)
```


### Actual outcome

The plot works fine but the warning is generated

`/var/folders/ss/pfgdfm2x7_s4cyw2v0b_t7q80000gn/T/ipykernel_76923/4170965423.py:7: UserWarning: This figure was using a layout engine that is incompatible with subplots_adjust and/or tight_layout; not calling subplots_adjust.
  plt.subplots_adjust(wspace=0)`

### Expected outcome

no warning

### Additional information

Warning disappears when constrained_layout=False is removed

### Operating system

OS/X

### Matplotlib Version

3.6.0

### Matplotlib Backend

_No response_

### Python version

_No response_

### Jupyter version

_No response_

### Installation

conda
