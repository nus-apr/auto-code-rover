SimpleLazyObject doesn't implement __radd__
Description
	
Technically, there's a whole bunch of magic methods it doesn't implement, compared to a complete proxy implementation, like that of wrapt.ObjectProxy, but __radd__ being missing is the one that's biting me at the moment.
As far as I can tell, the implementation can't just be
__radd__ = new_method_proxy(operator.radd)
because that doesn't exist, which is rubbish.
__radd__ = new_method_proxy(operator.attrgetter("__radd__"))
also won't work because types may not have that attr, and attrgetter doesn't supress the exception (correctly)
The minimal implementation I've found that works for me is:
	def __radd__(self, other):
		if self._wrapped is empty:
			self._setup()
		return other + self._wrapped
