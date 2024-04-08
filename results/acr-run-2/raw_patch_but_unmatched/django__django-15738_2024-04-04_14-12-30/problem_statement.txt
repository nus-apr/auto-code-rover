Models migration with change field foreign to many and deleting unique together.
Description
	 
		(last modified by Simon Charette)
	 
I have models like
class Authors(models.Model):
	project_data_set = models.ForeignKey(
		ProjectDataSet,
		on_delete=models.PROTECT
	)
	state = models.IntegerField()
	start_date = models.DateField()
	class Meta:
		 unique_together = (('project_data_set', 'state', 'start_date'),)
and
class DataSet(models.Model):
	name = models.TextField(max_length=50)
class Project(models.Model):
	data_sets = models.ManyToManyField(
		DataSet,
		through='ProjectDataSet',
	)
	name = models.TextField(max_length=50)
class ProjectDataSet(models.Model):
	"""
	Cross table of data set and project
	"""
	data_set = models.ForeignKey(DataSet, on_delete=models.PROTECT)
	project = models.ForeignKey(Project, on_delete=models.PROTECT)
	class Meta:
		unique_together = (('data_set', 'project'),)
when i want to change field project_data_set in Authors model from foreign key field to many to many field I must delete a unique_together, cause it can't be on many to many field.
Then my model should be like:
class Authors(models.Model):
	project_data_set = models.ManyToManyField(
		ProjectDataSet,
	)
	state = models.IntegerField()
	start_date = models.DateField()
But when I want to do a migrations.
python3 manage.py makemigrations
python3 manage.py migrate
I have error:
ValueError: Found wrong number (0) of constraints for app_authors(project_data_set, state, start_date)
The database is on production, so I can't delete previous initial migrations, and this error isn't depending on database, cause I delete it and error is still the same.
My solve is to first delete unique_together, then do a makemigrations and then migrate. After that change the field from foreign key to many to many field, then do a makemigrations and then migrate.
But in this way I have 2 migrations instead of one.
I added attachment with this project, download it and then do makemigrations and then migrate to see this error.
