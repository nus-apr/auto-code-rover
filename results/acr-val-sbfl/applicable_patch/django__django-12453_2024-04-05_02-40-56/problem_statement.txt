`TransactionTestCase.serialized_rollback` fails to restore objects due to ordering constraints
Description
	
I hit this problem in a fairly complex projet and haven't had the time to write a minimal reproduction case. I think it can be understood just by inspecting the code so I'm going to describe it while I have it in mind.
Setting serialized_rollback = True on a TransactionTestCase triggers ​rollback emulation. In practice, for each database:
BaseDatabaseCreation.create_test_db calls connection._test_serialized_contents = connection.creation.serialize_db_to_string()
TransactionTestCase._fixture_setup calls connection.creation.deserialize_db_from_string(connection._test_serialized_contents)
(The actual code isn't written that way; it's equivalent but the symmetry is less visible.)
serialize_db_to_string orders models with serializers.sort_dependencies and serializes them. The sorting algorithm only deals with natural keys. It doesn't do anything to order models referenced by foreign keys before models containing said foreign keys. That wouldn't be possible in general because circular foreign keys are allowed.
deserialize_db_from_string deserializes and saves models without wrapping in a transaction. This can result in integrity errors if an instance containing a foreign key is saved before the instance it references. I'm suggesting to fix it as follows:
diff --git a/django/db/backends/base/creation.py b/django/db/backends/base/creation.py
index bca8376..7bed2be 100644
--- a/django/db/backends/base/creation.py
+++ b/django/db/backends/base/creation.py
@@ -4,7 +4,7 @@ import time
 from django.apps import apps
 from django.conf import settings
 from django.core import serializers
-from django.db import router
+from django.db import router, transaction
 from django.utils.six import StringIO
 from django.utils.six.moves import input
 
@@ -128,8 +128,9 @@ class BaseDatabaseCreation(object):
		 the serialize_db_to_string method.
		 """
		 data = StringIO(data)
-		for obj in serializers.deserialize("json", data, using=self.connection.alias):
-			obj.save()
+		with transaction.atomic(using=self.connection.alias):
+			for obj in serializers.deserialize("json", data, using=self.connection.alias):
+				obj.save()
 
	 def _get_database_display_str(self, verbosity, database_name):
		 """
Note that loaddata doesn't have this problem because it wraps everything in a transaction:
	def handle(self, *fixture_labels, **options):
		# ...
		with transaction.atomic(using=self.using):
			self.loaddata(fixture_labels)
		# ...
This suggest that the transaction was just forgotten in the implementation of deserialize_db_from_string.
It should be possible to write a deterministic test for this bug because the order in which serialize_db_to_string serializes models depends on the app registry, and the app registry uses OrderedDict to store apps and models in a deterministic order.
