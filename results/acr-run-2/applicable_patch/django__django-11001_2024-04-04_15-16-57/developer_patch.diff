diff --git a/django/db/models/sql/compiler.py b/django/db/models/sql/compiler.py
--- a/django/db/models/sql/compiler.py
+++ b/django/db/models/sql/compiler.py
@@ -32,7 +32,8 @@ def __init__(self, query, connection, using):
         self.select = None
         self.annotation_col_map = None
         self.klass_info = None
-        self.ordering_parts = re.compile(r'(.*)\s(ASC|DESC)(.*)')
+        # Multiline ordering SQL clause may appear from RawSQL.
+        self.ordering_parts = re.compile(r'^(.*)\s(ASC|DESC)(.*)', re.MULTILINE | re.DOTALL)
         self._meta_ordering = None
 
     def setup_query(self):
