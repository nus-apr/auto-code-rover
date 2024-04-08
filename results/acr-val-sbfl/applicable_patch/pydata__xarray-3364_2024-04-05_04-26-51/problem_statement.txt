Ignore missing variables when concatenating datasets?
Several users (@raj-kesavan, @richardotis, now myself) have wondered about how to concatenate xray Datasets with different variables.

With the current `xray.concat`, you need to awkwardly create dummy variables filled with `NaN` in datasets that don't have them (or drop mismatched variables entirely). Neither of these are great options -- `concat` should have an option (the default?) to take care of this for the user.

This would also be more consistent with `pd.concat`, which takes a more relaxed approach to matching dataframes with different variables (it does an outer join).

