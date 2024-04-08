[Bug]: Setting matplotlib.pyplot.style.library['seaborn-colorblind'] result in key error on matplotlib v3.6.1
### Bug summary

I have code that executes:
```
import matplotlib.pyplot as plt
the_rc = plt.style.library["seaborn-colorblind"]
```

Using version 3.4.3 of matplotlib, this works fine. I recently installed my code on a machine with matplotlib version 3.6.1 and upon importing my code, this generated a key error for line `the_rc = plt.style.library["seaborn-colorblind"]` saying "seaborn-colorblind" was a bad key.

### Code for reproduction

```python
import matplotlib.pyplot as plt
the_rc = plt.style.library["seaborn-colorblind"]
```


### Actual outcome

Traceback (most recent call last):
KeyError: 'seaborn-colorblind'

### Expected outcome

seaborn-colorblind should be set as the matplotlib library style and I should be able to continue plotting with that style.

### Additional information

- Bug occurs with matplotlib version 3.6.1
- Bug does not occur with matplotlib version 3.4.3
- Tested on MacOSX and Ubuntu (same behavior on both)

### Operating system

OS/X

### Matplotlib Version

3.6.1

### Matplotlib Backend

MacOSX

### Python version

3.9.7

### Jupyter version

_No response_

### Installation

pip
