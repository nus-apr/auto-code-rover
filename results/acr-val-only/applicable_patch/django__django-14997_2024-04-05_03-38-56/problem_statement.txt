Remaking table with unique constraint crashes on SQLite.
Description
	
In Django 4.0a1, this model:
class Tag(models.Model):
	name = models.SlugField(help_text="The tag key.")
	value = models.CharField(max_length=150, help_text="The tag value.")
	class Meta:
		ordering = ["name", "value"]
		constraints = [
			models.UniqueConstraint(
				"name",
				"value",
				name="unique_name_value",
			)
		]
	def __str__(self):
		return f"{self.name}={self.value}"
with these migrations, using sqlite:
class Migration(migrations.Migration):
	initial = True
	dependencies = [
	]
	operations = [
		migrations.CreateModel(
			name='Tag',
			fields=[
				('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
				('name', models.SlugField(help_text='The tag key.')),
				('value', models.CharField(help_text='The tag value.', max_length=200)),
			],
			options={
				'ordering': ['name', 'value'],
			},
		),
		migrations.AddConstraint(
			model_name='tag',
			constraint=models.UniqueConstraint(django.db.models.expressions.F('name'), django.db.models.expressions.F('value'), name='unique_name_value'),
		),
	]
class Migration(migrations.Migration):
	dependencies = [
		('myapp', '0001_initial'),
	]
	operations = [
		migrations.AlterField(
			model_name='tag',
			name='value',
			field=models.CharField(help_text='The tag value.', max_length=150),
		),
	]
raises this error:
manage.py migrate
Operations to perform:
 Apply all migrations: admin, auth, contenttypes, myapp, sessions
Running migrations:
 Applying myapp.0002_alter_tag_value...python-BaseException
Traceback (most recent call last):
 File "D:\Projects\Development\sqliteerror\.venv\lib\site-packages\django\db\backends\utils.py", line 84, in _execute
	return self.cursor.execute(sql, params)
 File "D:\Projects\Development\sqliteerror\.venv\lib\site-packages\django\db\backends\sqlite3\base.py", line 416, in execute
	return Database.Cursor.execute(self, query, params)
sqlite3.OperationalError: the "." operator prohibited in index expressions
The above exception was the direct cause of the following exception:
Traceback (most recent call last):
 File "D:\Projects\Development\sqliteerror\.venv\lib\site-packages\django\core\management\base.py", line 373, in run_from_argv
	self.execute(*args, **cmd_options)
 File "D:\Projects\Development\sqliteerror\.venv\lib\site-packages\django\core\management\base.py", line 417, in execute
	output = self.handle(*args, **options)
 File "D:\Projects\Development\sqliteerror\.venv\lib\site-packages\django\core\management\base.py", line 90, in wrapped
	res = handle_func(*args, **kwargs)
 File "D:\Projects\Development\sqliteerror\.venv\lib\site-packages\django\core\management\commands\migrate.py", line 253, in handle
	post_migrate_state = executor.migrate(
 File "D:\Projects\Development\sqliteerror\.venv\lib\site-packages\django\db\migrations\executor.py", line 126, in migrate
	state = self._migrate_all_forwards(state, plan, full_plan, fake=fake, fake_initial=fake_initial)
 File "D:\Projects\Development\sqliteerror\.venv\lib\site-packages\django\db\migrations\executor.py", line 156, in _migrate_all_forwards
	state = self.apply_migration(state, migration, fake=fake, fake_initial=fake_initial)
 File "D:\Projects\Development\sqliteerror\.venv\lib\site-packages\django\db\migrations\executor.py", line 236, in apply_migration
	state = migration.apply(state, schema_editor)
 File "D:\Projects\Development\sqliteerror\.venv\lib\site-packages\django\db\migrations\migration.py", line 125, in apply
	operation.database_forwards(self.app_label, schema_editor, old_state, project_state)
 File "D:\Projects\Development\sqliteerror\.venv\lib\site-packages\django\db\migrations\operations\fields.py", line 225, in database_forwards
	schema_editor.alter_field(from_model, from_field, to_field)
 File "D:\Projects\Development\sqliteerror\.venv\lib\site-packages\django\db\backends\sqlite3\schema.py", line 140, in alter_field
	super().alter_field(model, old_field, new_field, strict=strict)
 File "D:\Projects\Development\sqliteerror\.venv\lib\site-packages\django\db\backends\base\schema.py", line 618, in alter_field
	self._alter_field(model, old_field, new_field, old_type, new_type,
 File "D:\Projects\Development\sqliteerror\.venv\lib\site-packages\django\db\backends\sqlite3\schema.py", line 362, in _alter_field
	self._remake_table(model, alter_field=(old_field, new_field))
 File "D:\Projects\Development\sqliteerror\.venv\lib\site-packages\django\db\backends\sqlite3\schema.py", line 303, in _remake_table
	self.execute(sql)
 File "D:\Projects\Development\sqliteerror\.venv\lib\site-packages\django\db\backends\base\schema.py", line 151, in execute
	cursor.execute(sql, params)
 File "D:\Projects\Development\sqliteerror\.venv\lib\site-packages\django\db\backends\utils.py", line 98, in execute
	return super().execute(sql, params)
 File "D:\Projects\Development\sqliteerror\.venv\lib\site-packages\django\db\backends\utils.py", line 66, in execute
	return self._execute_with_wrappers(sql, params, many=False, executor=self._execute)
 File "D:\Projects\Development\sqliteerror\.venv\lib\site-packages\django\db\backends\utils.py", line 75, in _execute_with_wrappers
	return executor(sql, params, many, context)
 File "D:\Projects\Development\sqliteerror\.venv\lib\site-packages\django\db\backends\utils.py", line 84, in _execute
	return self.cursor.execute(sql, params)
 File "D:\Projects\Development\sqliteerror\.venv\lib\site-packages\django\db\utils.py", line 90, in __exit__
	raise dj_exc_value.with_traceback(traceback) from exc_value
 File "D:\Projects\Development\sqliteerror\.venv\lib\site-packages\django\db\backends\utils.py", line 84, in _execute
	return self.cursor.execute(sql, params)
 File "D:\Projects\Development\sqliteerror\.venv\lib\site-packages\django\db\backends\sqlite3\base.py", line 416, in execute
	return Database.Cursor.execute(self, query, params)
django.db.utils.OperationalError: the "." operator prohibited in index expressions
