xlim_changed not emitted on shared axis
<!--To help us understand and resolve your issue, please fill out the form to the best of your ability.-->
<!--You can feel free to delete the sections that do not apply.-->

### Bug report

**Bug summary**

When an axis is shared with another its registered "xlim_changed" callbacks does not get called when the change is induced by a shared axis (via sharex=). 

In _base.py the set_xlim for sibling axis are called with emit=False:

```
matplotlib/lib/matplotlib/axes/_base.py:

/.../
def set_xlim(...)
/.../
        if emit:
            self.callbacks.process('xlim_changed', self)
            # Call all of the other x-axes that are shared with this one
            for other in self._shared_x_axes.get_siblings(self):
                if other is not self:
                    other.set_xlim(self.viewLim.intervalx,
                                   emit=False, auto=auto)
```

I'm very new to matplotlib, so perhaps there is a good reason for this? emit=False seems to disable both continued "inheritance" of axis (why?) and triggering of change callbacks (looking at the code above).

It seems like one would at least want to trigger the xlim_changed callbacks as they would be intended to react to any change in axis limits.

Edit: Setting emit=True seems to introduce a recursion issue (not sure why but as inheritance seems to be passed along anyway it doesn't really matter). Moving the callback call to outside of the "if emit:"-statement seems to solve the issue as far as I can see when trying it out. Any reason to keep it inside the if-statement? 

