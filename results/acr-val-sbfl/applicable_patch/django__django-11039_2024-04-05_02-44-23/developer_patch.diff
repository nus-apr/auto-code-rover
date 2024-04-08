diff --git a/django/core/management/commands/sqlmigrate.py b/django/core/management/commands/sqlmigrate.py
--- a/django/core/management/commands/sqlmigrate.py
+++ b/django/core/management/commands/sqlmigrate.py
@@ -55,8 +55,9 @@ def handle(self, *args, **options):
                 migration_name, app_label))
         targets = [(app_label, migration.name)]
 
-        # Show begin/end around output only for atomic migrations
-        self.output_transaction = migration.atomic
+        # Show begin/end around output for atomic migrations, if the database
+        # supports transactional DDL.
+        self.output_transaction = migration.atomic and connection.features.can_rollback_ddl
 
         # Make a plan that represents just the requested migrations and show SQL
         # for it
