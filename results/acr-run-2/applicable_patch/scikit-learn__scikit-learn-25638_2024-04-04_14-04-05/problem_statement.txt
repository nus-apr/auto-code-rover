Support nullable pandas dtypes in `unique_labels`
### Describe the workflow you want to enable

I would like to be able to pass the nullable pandas dtypes ("Int64", "Float64", "boolean") into sklearn's `unique_labels` function. Because the dtypes become `object` dtype when converted to numpy arrays we get `ValueError: Mix type of y not allowed, got types {'binary', 'unknown'}`:

Repro with sklearn 1.2.1
```py 
    import pandas as pd
    import pytest
    from sklearn.utils.multiclass import unique_labels
    
    for dtype in ["Int64", "Float64", "boolean"]:
        y_true = pd.Series([1, 0, 0, 1, 0, 1, 1, 0, 1], dtype=dtype)
        y_predicted = pd.Series([0, 0, 1, 1, 0, 1, 1, 1, 1], dtype="int64")

        with pytest.raises(ValueError, match="Mix type of y not allowed, got types"):
            unique_labels(y_true, y_predicted)
```

### Describe your proposed solution

We should get the same behavior as when `int64`, `float64`, and `bool` dtypes are used, which is no error:  

```python
    import pandas as pd
    from sklearn.utils.multiclass import unique_labels
    
    for dtype in ["int64", "float64", "bool"]:
        y_true = pd.Series([1, 0, 0, 1, 0, 1, 1, 0, 1], dtype=dtype)
        y_predicted = pd.Series([0, 0, 1, 1, 0, 1, 1, 1, 1], dtype="int64")

        unique_labels(y_true, y_predicted)
```

### Describe alternatives you've considered, if relevant

Our current workaround is to convert the data to numpy arrays with the corresponding dtype that works prior to passing it into `unique_labels`.

### Additional context

_No response_
