diff --git a/astropy/io/fits/fitsrec.py b/astropy/io/fits/fitsrec.py
--- a/astropy/io/fits/fitsrec.py
+++ b/astropy/io/fits/fitsrec.py
@@ -1261,7 +1261,7 @@ def _scale_back_ascii(self, col_idx, input_field, output_field):
 
         # Replace exponent separator in floating point numbers
         if 'D' in format:
-            output_field.replace(encode_ascii('E'), encode_ascii('D'))
+            output_field[:] = output_field.replace(b'E', b'D')
 
 
 def _get_recarray_field(array, key):
