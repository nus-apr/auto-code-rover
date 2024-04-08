regression in input validation of clustering metrics
```python
from sklearn.metrics.cluster import mutual_info_score
import numpy as np

x = np.random.choice(['a', 'b'], size=20).astype(object)
mutual_info_score(x, x)
```
ValueError: could not convert string to float: 'b'

while
```python
x = np.random.choice(['a', 'b'], size=20)
mutual_info_score(x, x)
```
works with a warning?

this worked in 0.21.1 without a warning (as I think it should)


Edit by @ogrisel: I removed the `.astype(object)` in the second code snippet.
