diff --git a/django/db/models/fields/__init__.py b/django/db/models/fields/__init__.py
--- a/django/db/models/fields/__init__.py
+++ b/django/db/models/fields/__init__.py
@@ -1709,7 +1709,7 @@ def get_prep_value(self, value):
 
     def formfield(self, **kwargs):
         return super().formfield(**{
-            'path': self.path,
+            'path': self.path() if callable(self.path) else self.path,
             'match': self.match,
             'recursive': self.recursive,
             'form_class': forms.FilePathField,
