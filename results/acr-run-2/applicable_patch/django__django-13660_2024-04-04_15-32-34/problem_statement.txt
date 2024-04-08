shell command crashes when passing (with -c) the python code with functions.
Description
	
The examples below use Python 3.7 and Django 2.2.16, but I checked that the code is the same on master and works the same in Python 3.8.
Here's how ​python -c works:
$ python -c <<EOF " 
import django
def f():
		print(django.__version__)
f()"
EOF
2.2.16
Here's how ​python -m django shell -c works (paths shortened for clarify):
$ python -m django shell -c <<EOF "
import django
def f():
		print(django.__version__)
f()"
EOF
Traceback (most recent call last):
 File "{sys.base_prefix}/lib/python3.7/runpy.py", line 193, in _run_module_as_main
	"__main__", mod_spec)
 File "{sys.base_prefix}/lib/python3.7/runpy.py", line 85, in _run_code
	exec(code, run_globals)
 File "{sys.prefix}/lib/python3.7/site-packages/django/__main__.py", line 9, in <module>
	management.execute_from_command_line()
 File "{sys.prefix}/lib/python3.7/site-packages/django/core/management/__init__.py", line 381, in execute_from_command_line
	utility.execute()
 File "{sys.prefix}/lib/python3.7/site-packages/django/core/management/__init__.py", line 375, in execute
	self.fetch_command(subcommand).run_from_argv(self.argv)
 File "{sys.prefix}/lib/python3.7/site-packages/django/core/management/base.py", line 323, in run_from_argv
	self.execute(*args, **cmd_options)
 File "{sys.prefix}/lib/python3.7/site-packages/django/core/management/base.py", line 364, in execute
	output = self.handle(*args, **options)
 File "{sys.prefix}/lib/python3.7/site-packages/django/core/management/commands/shell.py", line 86, in handle
	exec(options['command'])
 File "<string>", line 5, in <module>
 File "<string>", line 4, in f
NameError: name 'django' is not defined
The problem is in the ​usage of ​exec:
	def handle(self, **options):
		# Execute the command and exit.
		if options['command']:
			exec(options['command'])
			return
		# Execute stdin if it has anything to read and exit.
		# Not supported on Windows due to select.select() limitations.
		if sys.platform != 'win32' and not sys.stdin.isatty() and select.select([sys.stdin], [], [], 0)[0]:
			exec(sys.stdin.read())
			return
exec should be passed a dictionary containing a minimal set of globals. This can be done by just passing a new, empty dictionary as the second argument of exec.
