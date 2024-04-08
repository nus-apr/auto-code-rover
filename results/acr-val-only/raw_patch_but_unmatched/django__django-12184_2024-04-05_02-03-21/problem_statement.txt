Optional URL params crash some view functions.
Description
	
My use case, running fine with Django until 2.2:
URLConf:
urlpatterns += [
	...
	re_path(r'^module/(?P<format>(html|json|xml))?/?$', views.modules, name='modules'),
]
View:
def modules(request, format='html'):
	...
	return render(...)
With Django 3.0, this is now producing an error:
Traceback (most recent call last):
 File "/l10n/venv/lib/python3.6/site-packages/django/core/handlers/exception.py", line 34, in inner
	response = get_response(request)
 File "/l10n/venv/lib/python3.6/site-packages/django/core/handlers/base.py", line 115, in _get_response
	response = self.process_exception_by_middleware(e, request)
 File "/l10n/venv/lib/python3.6/site-packages/django/core/handlers/base.py", line 113, in _get_response
	response = wrapped_callback(request, *callback_args, **callback_kwargs)
Exception Type: TypeError at /module/
Exception Value: modules() takes from 1 to 2 positional arguments but 3 were given
