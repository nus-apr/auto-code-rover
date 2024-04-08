Test runner setup_databases crashes with "TEST": {"MIGRATE": False}.
Description
	
I'm trying to upgrade a project from Django 3.0 to Django 3.1 and wanted to try out the new "TEST": {"MIGRATE": False} database setting.
Sadly I'm running into an issue immediately when running ./manage.py test.
Removing the "TEST": {"MIGRATE": False} line allows the tests to run. So this is not blocking the upgrade for us, but it would be nice if we were able to use the new feature to skip migrations during testing.
For reference, this project was recently upgraded from Django 1.4 all the way to 3.0 so there might be some legacy cruft somewhere that triggers this.
Here's the trackeback. I'll try to debug this some more.
Traceback (most recent call last):
 File "/usr/local/lib/python3.6/site-packages/django/db/backends/utils.py", line 84, in _execute
	return self.cursor.execute(sql, params)
psycopg2.errors.UndefinedTable: relation "django_admin_log" does not exist
LINE 1: ...n_flag", "django_admin_log"."change_message" FROM "django_ad...
															 ^
The above exception was the direct cause of the following exception:
Traceback (most recent call last):
 File "/usr/local/lib/python3.6/site-packages/django/db/models/sql/compiler.py", line 1156, in execute_sql
	cursor.execute(sql, params)
 File "/usr/local/lib/python3.6/site-packages/django/db/backends/utils.py", line 66, in execute
	return self._execute_with_wrappers(sql, params, many=False, executor=self._execute)
 File "/usr/local/lib/python3.6/site-packages/django/db/backends/utils.py", line 75, in _execute_with_wrappers
	return executor(sql, params, many, context)
 File "/usr/local/lib/python3.6/site-packages/django/db/backends/utils.py", line 84, in _execute
	return self.cursor.execute(sql, params)
 File "/usr/local/lib/python3.6/site-packages/django/db/utils.py", line 90, in __exit__
	raise dj_exc_value.with_traceback(traceback) from exc_value
 File "/usr/local/lib/python3.6/site-packages/django/db/backends/utils.py", line 84, in _execute
	return self.cursor.execute(sql, params)
django.db.utils.ProgrammingError: relation "django_admin_log" does not exist
LINE 1: ...n_flag", "django_admin_log"."change_message" FROM "django_ad...
															 ^
During handling of the above exception, another exception occurred:
Traceback (most recent call last):
 File "./manage.py", line 15, in <module>
	main()
 File "./manage.py", line 11, in main
	execute_from_command_line(sys.argv)
 File "/usr/local/lib/python3.6/site-packages/django/core/management/__init__.py", line 401, in execute_from_command_line
	utility.execute()
 File "/usr/local/lib/python3.6/site-packages/django/core/management/__init__.py", line 395, in execute
	self.fetch_command(subcommand).run_from_argv(self.argv)
 File "/usr/local/lib/python3.6/site-packages/django/core/management/commands/test.py", line 23, in run_from_argv
	super().run_from_argv(argv)
 File "/usr/local/lib/python3.6/site-packages/django/core/management/base.py", line 330, in run_from_argv
	self.execute(*args, **cmd_options)
 File "/usr/local/lib/python3.6/site-packages/django/core/management/base.py", line 371, in execute
	output = self.handle(*args, **options)
 File "/usr/local/lib/python3.6/site-packages/django/core/management/commands/test.py", line 53, in handle
	failures = test_runner.run_tests(test_labels)
 File "/usr/local/lib/python3.6/site-packages/django/test/runner.py", line 695, in run_tests
	old_config = self.setup_databases(aliases=databases)
 File "/usr/local/lib/python3.6/site-packages/django/test/runner.py", line 616, in setup_databases
	self.parallel, **kwargs
 File "/usr/local/lib/python3.6/site-packages/django/test/utils.py", line 174, in setup_databases
	serialize=connection.settings_dict['TEST'].get('SERIALIZE', True),
 File "/usr/local/lib/python3.6/site-packages/django/db/backends/base/creation.py", line 78, in create_test_db
	self.connection._test_serialized_contents = self.serialize_db_to_string()
 File "/usr/local/lib/python3.6/site-packages/django/db/backends/base/creation.py", line 121, in serialize_db_to_string
	serializers.serialize("json", get_objects(), indent=None, stream=out)
 File "/usr/local/lib/python3.6/site-packages/django/core/serializers/__init__.py", line 128, in serialize
	s.serialize(queryset, **options)
 File "/usr/local/lib/python3.6/site-packages/django/core/serializers/base.py", line 90, in serialize
	for count, obj in enumerate(queryset, start=1):
 File "/usr/local/lib/python3.6/site-packages/django/db/backends/base/creation.py", line 118, in get_objects
	yield from queryset.iterator()
 File "/usr/local/lib/python3.6/site-packages/django/db/models/query.py", line 360, in _iterator
	yield from self._iterable_class(self, chunked_fetch=use_chunked_fetch, chunk_size=chunk_size)
 File "/usr/local/lib/python3.6/site-packages/django/db/models/query.py", line 53, in __iter__
	results = compiler.execute_sql(chunked_fetch=self.chunked_fetch, chunk_size=self.chunk_size)
 File "/usr/local/lib/python3.6/site-packages/django/db/models/sql/compiler.py", line 1159, in execute_sql
	cursor.close()
psycopg2.errors.InvalidCursorName: cursor "_django_curs_139860821038912_sync_1" does not exist
