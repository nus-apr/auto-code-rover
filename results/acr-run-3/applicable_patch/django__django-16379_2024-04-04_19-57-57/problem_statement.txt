FileBasedCache has_key is susceptible to race conditions
Description
	 
		(last modified by Marti Raudsepp)
	 
I received the exception from Django's cache framework:
FileNotFoundError: [Errno 2] No such file or directory: '/app/var/cache/d729e4cf4ba88cba5a0f48e0396ec48a.djcache'
[...]
 File "django/core/cache/backends/base.py", line 229, in get_or_set
	self.add(key, default, timeout=timeout, version=version)
 File "django/core/cache/backends/filebased.py", line 26, in add
	if self.has_key(key, version):
 File "django/core/cache/backends/filebased.py", line 94, in has_key
	with open(fname, "rb") as f:
The code is:
	def has_key(self, key, version=None):
		fname = self._key_to_file(key, version)
		if os.path.exists(fname):
			with open(fname, "rb") as f:
				return not self._is_expired(f)
		return False
Between the exists() check and open(), it's possible for the file to be deleted. In fact, the _is_expired() method itself deletes the file if it finds it to be expired. So if many threads race to read an expired cache at once, it's not that unlikely to hit this window.
