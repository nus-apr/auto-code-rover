AlterOrderWithRespectTo() with ForeignKey crash when _order is included in Index().
Description
	
	class Meta:
		db_table = 'look_image'
		order_with_respect_to = 'look'
		indexes = [
			models.Index(fields=['look', '_order']),
			models.Index(fields=['created_at']),
			models.Index(fields=['updated_at']),
		]
migrations.CreateModel(
			name='LookImage',
			fields=[
				('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
				('look', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='posts.Look', verbose_name='LOOK')),
				('image_url', models.URLField(blank=True, max_length=10000, null=True)),
				('image', models.ImageField(max_length=2000, upload_to='')),
				('deleted', models.DateTimeField(editable=False, null=True)),
				('created_at', models.DateTimeField(auto_now_add=True)),
				('updated_at', models.DateTimeField(auto_now=True)),
			],
		),
		migrations.AddIndex(
			model_name='lookimage',
			index=models.Index(fields=['look', '_order'], name='look_image_look_id_eaff30_idx'),
		),
		migrations.AddIndex(
			model_name='lookimage',
			index=models.Index(fields=['created_at'], name='look_image_created_f746cf_idx'),
		),
		migrations.AddIndex(
			model_name='lookimage',
			index=models.Index(fields=['updated_at'], name='look_image_updated_aceaf9_idx'),
		),
		migrations.AlterOrderWithRespectTo(
			name='lookimage',
			order_with_respect_to='look',
		),
I added orders_with_respect_to in new model class's Meta class and also made index for '_order' field by combining with other field. And a new migration file based on the model looks like the code above.
The problem is operation AlterOrderWithRespectTo after AddIndex of '_order' raising error because '_order' field had not been created yet.
It seems to be AlterOrderWithRespectTo has to proceed before AddIndex of '_order'.
