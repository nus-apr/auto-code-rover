diff --git a/astropy/wcs/wcs.py b/astropy/wcs/wcs.py
--- a/astropy/wcs/wcs.py
+++ b/astropy/wcs/wcs.py
@@ -1212,6 +1212,9 @@ def _array_converter(self, func, sky, *args, ra_dec_order=False):
         """
 
         def _return_list_of_arrays(axes, origin):
+            if any([x.size == 0 for x in axes]):
+                return axes
+
             try:
                 axes = np.broadcast_arrays(*axes)
             except ValueError:
@@ -1235,6 +1238,8 @@ def _return_single_array(xy, origin):
                 raise ValueError(
                     "When providing two arguments, the array must be "
                     "of shape (N, {0})".format(self.naxis))
+            if 0 in xy.shape:
+                return xy
             if ra_dec_order and sky == 'input':
                 xy = self._denormalize_sky(xy)
             result = func(xy, origin)
