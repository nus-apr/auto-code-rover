Auto-reloading with StatReloader very intermittently throws "ValueError: embedded null byte".
Description
	
Raising this mainly so that it's tracked, as I have no idea how to reproduce it, nor why it's happening. It ultimately looks like a problem with Pathlib, which wasn't used prior to 2.2.
Stacktrace:
Traceback (most recent call last):
 File "manage.py" ...
	execute_from_command_line(sys.argv)
 File "/Userz/kez/path/to/venv/lib/python3.6/site-packages/django/core/management/__init__.py", line 381, in execute_from_command_line
	utility.execute()
 File "/Userz/kez/path/to/venv/lib/python3.6/site-packages/django/core/management/__init__.py", line 375, in execute
	self.fetch_command(subcommand).run_from_argv(self.argv)
 File "/Userz/kez/path/to/venv/lib/python3.6/site-packages/django/core/management/base.py", line 323, in run_from_argv
	self.execute(*args, **cmd_options)
 File "/Userz/kez/path/to/venv/lib/python3.6/site-packages/django/core/management/commands/runserver.py", line 60, in execute
	super().execute(*args, **options)
 File "/Userz/kez/path/to/venv/lib/python3.6/site-packages/django/core/management/base.py", line 364, in execute
	output = self.handle(*args, **options)
 File "/Userz/kez/path/to/venv/lib/python3.6/site-packages/django/core/management/commands/runserver.py", line 95, in handle
	self.run(**options)
 File "/Userz/kez/path/to/venv/lib/python3.6/site-packages/django/core/management/commands/runserver.py", line 102, in run
	autoreload.run_with_reloader(self.inner_run, **options)
 File "/Userz/kez/path/to/venv/lib/python3.6/site-packages/django/utils/autoreload.py", line 577, in run_with_reloader
	start_django(reloader, main_func, *args, **kwargs)
 File "/Userz/kez/path/to/venv/lib/python3.6/site-packages/django/utils/autoreload.py", line 562, in start_django
	reloader.run(django_main_thread)
 File "/Userz/kez/path/to/venv/lib/python3.6/site-packages/django/utils/autoreload.py", line 280, in run
	self.run_loop()
 File "/Userz/kez/path/to/venv/lib/python3.6/site-packages/django/utils/autoreload.py", line 286, in run_loop
	next(ticker)
 File "/Userz/kez/path/to/venv/lib/python3.6/site-packages/django/utils/autoreload.py", line 326, in tick
	for filepath, mtime in self.snapshot_files():
 File "/Userz/kez/path/to/venv/lib/python3.6/site-packages/django/utils/autoreload.py", line 342, in snapshot_files
	for file in self.watched_files():
 File "/Userz/kez/path/to/venv/lib/python3.6/site-packages/django/utils/autoreload.py", line 241, in watched_files
	yield from iter_all_python_module_files()
 File "/Userz/kez/path/to/venv/lib/python3.6/site-packages/django/utils/autoreload.py", line 103, in iter_all_python_module_files
	return iter_modules_and_files(modules, frozenset(_error_files))
 File "/Userz/kez/path/to/venv/lib/python3.6/site-packages/django/utils/autoreload.py", line 132, in iter_modules_and_files
	results.add(path.resolve().absolute())
 File "/Users/kez/.pyenv/versions/3.6.2/lib/python3.6/pathlib.py", line 1120, in resolve
	s = self._flavour.resolve(self, strict=strict)
 File "/Users/kez/.pyenv/versions/3.6.2/lib/python3.6/pathlib.py", line 346, in resolve
	return _resolve(base, str(path)) or sep
 File "/Users/kez/.pyenv/versions/3.6.2/lib/python3.6/pathlib.py", line 330, in _resolve
	target = accessor.readlink(newpath)
 File "/Users/kez/.pyenv/versions/3.6.2/lib/python3.6/pathlib.py", line 441, in readlink
	return os.readlink(path)
ValueError: embedded null byte
I did print(path) before os.readlink(path) in pathlib and ended up with:
/Users/kez
/Users/kez/.pyenv
/Users/kez/.pyenv/versions
/Users/kez/.pyenv/versions/3.6.2
/Users/kez/.pyenv/versions/3.6.2/lib
/Users/kez/.pyenv/versions/3.6.2/lib/python3.6
/Users/kez/.pyenv/versions/3.6.2/lib/python3.6/asyncio
/Users/kez/.pyenv/versions/3.6.2/lib/python3.6/asyncio/selector_events.py
/Users
It always seems to be /Users which is last
It may have already printed /Users as part of another .resolve() multiple times (that is, the order is not deterministic, and it may have traversed beyond /Users successfully many times during startup.
I don't know where to begin looking for the rogue null byte, nor why it only exists sometimes.
Best guess I have is that there's a mountpoint in /Users to a samba share which may not have been connected to yet? I dunno.
I have no idea if it's fixable without removing the use of pathlib (which tbh I think should happen anyway, because it's slow) and reverting to using os.path.join and friends. 
I have no idea if it's fixed in a later Python version, but with no easy way to reproduce ... dunno how I'd check.
I have no idea if it's something specific to my system (pyenv, OSX 10.11, etc)
