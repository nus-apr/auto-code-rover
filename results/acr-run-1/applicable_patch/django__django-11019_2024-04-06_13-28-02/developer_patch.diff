diff --git a/django/forms/widgets.py b/django/forms/widgets.py
--- a/django/forms/widgets.py
+++ b/django/forms/widgets.py
@@ -6,16 +6,21 @@
 import datetime
 import re
 import warnings
+from collections import defaultdict
 from itertools import chain
 
 from django.conf import settings
 from django.forms.utils import to_current_timezone
 from django.templatetags.static import static
 from django.utils import datetime_safe, formats
+from django.utils.datastructures import OrderedSet
 from django.utils.dates import MONTHS
 from django.utils.formats import get_format
 from django.utils.html import format_html, html_safe
 from django.utils.safestring import mark_safe
+from django.utils.topological_sort import (
+    CyclicDependencyError, stable_topological_sort,
+)
 from django.utils.translation import gettext_lazy as _
 
 from .renderers import get_default_renderer
@@ -59,22 +64,15 @@ def __str__(self):
 
     @property
     def _css(self):
-        css = self._css_lists[0]
-        # filter(None, ...) avoids calling merge with empty dicts.
-        for obj in filter(None, self._css_lists[1:]):
-            css = {
-                medium: self.merge(css.get(medium, []), obj.get(medium, []))
-                for medium in css.keys() | obj.keys()
-            }
-        return css
+        css = defaultdict(list)
+        for css_list in self._css_lists:
+            for medium, sublist in css_list.items():
+                css[medium].append(sublist)
+        return {medium: self.merge(*lists) for medium, lists in css.items()}
 
     @property
     def _js(self):
-        js = self._js_lists[0]
-        # filter(None, ...) avoids calling merge() with empty lists.
-        for obj in filter(None, self._js_lists[1:]):
-            js = self.merge(js, obj)
-        return js
+        return self.merge(*self._js_lists)
 
     def render(self):
         return mark_safe('\n'.join(chain.from_iterable(getattr(self, 'render_' + name)() for name in MEDIA_TYPES)))
@@ -115,39 +113,37 @@ def __getitem__(self, name):
         raise KeyError('Unknown media type "%s"' % name)
 
     @staticmethod
-    def merge(list_1, list_2):
+    def merge(*lists):
         """
-        Merge two lists while trying to keep the relative order of the elements.
-        Warn if the lists have the same two elements in a different relative
-        order.
+        Merge lists while trying to keep the relative order of the elements.
+        Warn if the lists have the same elements in a different relative order.
 
         For static assets it can be important to have them included in the DOM
         in a certain order. In JavaScript you may not be able to reference a
         global or in CSS you might want to override a style.
         """
-        # Start with a copy of list_1.
-        combined_list = list(list_1)
-        last_insert_index = len(list_1)
-        # Walk list_2 in reverse, inserting each element into combined_list if
-        # it doesn't already exist.
-        for path in reversed(list_2):
-            try:
-                # Does path already exist in the list?
-                index = combined_list.index(path)
-            except ValueError:
-                # Add path to combined_list since it doesn't exist.
-                combined_list.insert(last_insert_index, path)
-            else:
-                if index > last_insert_index:
-                    warnings.warn(
-                        'Detected duplicate Media files in an opposite order:\n'
-                        '%s\n%s' % (combined_list[last_insert_index], combined_list[index]),
-                        MediaOrderConflictWarning,
-                    )
-                # path already exists in the list. Update last_insert_index so
-                # that the following elements are inserted in front of this one.
-                last_insert_index = index
-        return combined_list
+        dependency_graph = defaultdict(set)
+        all_items = OrderedSet()
+        for list_ in filter(None, lists):
+            head = list_[0]
+            # The first items depend on nothing but have to be part of the
+            # dependency graph to be included in the result.
+            dependency_graph.setdefault(head, set())
+            for item in list_:
+                all_items.add(item)
+                # No self dependencies
+                if head != item:
+                    dependency_graph[item].add(head)
+                head = item
+        try:
+            return stable_topological_sort(all_items, dependency_graph)
+        except CyclicDependencyError:
+            warnings.warn(
+                'Detected duplicate Media files in an opposite order: {}'.format(
+                    ', '.join(repr(l) for l in lists)
+                ), MediaOrderConflictWarning,
+            )
+            return list(all_items)
 
     def __add__(self, other):
         combined = Media()
