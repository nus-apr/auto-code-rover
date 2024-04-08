Use Admin Inline verbose_name as default for Inline verbose_name_plural
Description
	
Django allows specification of a verbose_name and a verbose_name_plural for Inline classes in admin views. However, verbose_name_plural for an Inline is not currently based on a specified verbose_name. Instead, it continues to be based on the model name, or an a verbose_name specified in the model's Meta class. This was confusing to me initially (I didn't understand why I had to specify both name forms for an Inline if I wanted to overrule the default name), and seems inconsistent with the approach for a model's Meta class (which does automatically base the plural form on a specified verbose_name). I propose that verbose_name_plural for an Inline class should by default be based on the verbose_name for an Inline if that is specified.
I have written a patch to implement this, including tests. Would be happy to submit that.
