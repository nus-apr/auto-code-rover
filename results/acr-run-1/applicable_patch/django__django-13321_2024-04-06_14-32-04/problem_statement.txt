Decoding an invalid session data crashes.
Description
	 
		(last modified by Matt Hegarty)
	 
Hi
I recently upgraded my staging server to 3.1. I think that there was an old session which was still active.
On browsing to any URL, I get the crash below. It looks similar to ​this issue.
I cannot login at all with Chrome - each attempt to access the site results in a crash. Login with Firefox works fine.
This is only happening on my Staging site, which is running Gunicorn behind nginx proxy.
Internal Server Error: /overview/
Traceback (most recent call last):
File "/usr/local/lib/python3.8/site-packages/django/contrib/sessions/backends/base.py", line 215, in _get_session
return self._session_cache
AttributeError: 'SessionStore' object has no attribute '_session_cache'
During handling of the above exception, another exception occurred:
Traceback (most recent call last):
File "/usr/local/lib/python3.8/site-packages/django/contrib/sessions/backends/base.py", line 118, in decode
return signing.loads(session_data, salt=self.key_salt, serializer=self.serializer)
File "/usr/local/lib/python3.8/site-packages/django/core/signing.py", line 135, in loads
base64d = TimestampSigner(key, salt=salt).unsign(s, max_age=max_age).encode()
File "/usr/local/lib/python3.8/site-packages/django/core/signing.py", line 201, in unsign
result = super().unsign(value)
File "/usr/local/lib/python3.8/site-packages/django/core/signing.py", line 184, in unsign
raise BadSignature('Signature "%s" does not match' % sig)
django.core.signing.BadSignature: Signature "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" does not match
During handling of the above exception, another exception occurred:
Traceback (most recent call last):
File "/usr/local/lib/python3.8/site-packages/django/core/handlers/exception.py", line 47, in inner
response = get_response(request)
File "/usr/local/lib/python3.8/site-packages/django/core/handlers/base.py", line 179, in _get_response
response = wrapped_callback(request, *callback_args, **callback_kwargs)
File "/usr/local/lib/python3.8/site-packages/django/views/generic/base.py", line 73, in view
return self.dispatch(request, *args, **kwargs)
File "/usr/local/lib/python3.8/site-packages/django/contrib/auth/mixins.py", line 50, in dispatch
if not request.user.is_authenticated:
File "/usr/local/lib/python3.8/site-packages/django/utils/functional.py", line 240, in inner
self._setup()
File "/usr/local/lib/python3.8/site-packages/django/utils/functional.py", line 376, in _setup
self._wrapped = self._setupfunc()
File "/usr/local/lib/python3.8/site-packages/django_otp/middleware.py", line 38, in _verify_user
user.otp_device = None
File "/usr/local/lib/python3.8/site-packages/django/utils/functional.py", line 270, in __setattr__
self._setup()
File "/usr/local/lib/python3.8/site-packages/django/utils/functional.py", line 376, in _setup
self._wrapped = self._setupfunc()
File "/usr/local/lib/python3.8/site-packages/django/contrib/auth/middleware.py", line 23, in <lambda>
request.user = SimpleLazyObject(lambda: get_user(request))
File "/usr/local/lib/python3.8/site-packages/django/contrib/auth/middleware.py", line 11, in get_user
request._cached_user = auth.get_user(request)
File "/usr/local/lib/python3.8/site-packages/django/contrib/auth/__init__.py", line 174, in get_user
user_id = _get_user_session_key(request)
File "/usr/local/lib/python3.8/site-packages/django/contrib/auth/__init__.py", line 58, in _get_user_session_key
return get_user_model()._meta.pk.to_python(request.session[SESSION_KEY])
File "/usr/local/lib/python3.8/site-packages/django/contrib/sessions/backends/base.py", line 65, in __getitem__
return self._session[key]
File "/usr/local/lib/python3.8/site-packages/django/contrib/sessions/backends/base.py", line 220, in _get_session
self._session_cache = self.load()
File "/usr/local/lib/python3.8/site-packages/django/contrib/sessions/backends/db.py", line 44, in load
return self.decode(s.session_data) if s else {}
File "/usr/local/lib/python3.8/site-packages/django/contrib/sessions/backends/base.py", line 122, in decode
return self._legacy_decode(session_data)
File "/usr/local/lib/python3.8/site-packages/django/contrib/sessions/backends/base.py", line 126, in _legacy_decode
encoded_data = base64.b64decode(session_data.encode('ascii'))
File "/usr/local/lib/python3.8/base64.py", line 87, in b64decode
return binascii.a2b_base64(s)
binascii.Error: Incorrect padding
