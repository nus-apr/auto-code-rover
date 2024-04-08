check_for_template_tags_with_the_same_name with libraries in TEMPLATES
Description
	
I didn't explore this thoroughly, but I think there might be an issue with the check_for_template_tags_with_the_same_name when you add a template tag library into TEMPLATES['OPTIONS']['librairies'].
I'm getting an error like: 
(templates.E003) 'my_tags' is used for multiple template tag modules: 'someapp.templatetags.my_tags', 'someapp.templatetags.my_tags'
