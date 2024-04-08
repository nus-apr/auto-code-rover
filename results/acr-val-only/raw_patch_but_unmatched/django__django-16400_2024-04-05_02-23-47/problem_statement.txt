migrate management command does not respect database parameter when adding Permissions.
Description
	 
		(last modified by Vasanth)
	 
When invoking migrate with a database parameter, the migration runs successfully. However, there seems to be a DB read request that runs after the migration. This call does not respect the db param and invokes the db router .
When naming the db as a parameter, all DB calls in the context of the migrate command are expected to use the database specified.
I came across this as I am currently using a thread-local variable to get the active DB with a custom DB router for a multi-tenant service .
Minimal example 
Setup the custom middleware and custom DB Router as show below. Then run any DB migration. We see that "read {}" is being printed before the exception message.
Ideally none of this code must be called as the DB was specified during management command.
from threading import local
from django.conf import settings
local_state = local()
class InvalidTenantException(Exception):
	pass
class TenantSubdomainMiddleware:
	def __init__(self, get_response):
		self.get_response = get_response
	def __call__(self, request):
		## Get Subdomain
		host = request.get_host().split(":")[0]
		local_state.subdomain = (
			# We assume single level of subdomain : app.service.com 
			# HOST_IP : used to for local dev. 
			host if host in settings.HOST_IP else host.split(".")[0]
		)
		response = self.get_response(request)
		return response
class TenantDatabaseRouter:
	def _default_db(self):
		subdomain = getattr(local_state, "subdomain", None)
		if subdomain is not None and subdomain in settings.TENANT_MAP:
			db_name = settings.TENANT_MAP[local_state.subdomain]
			return db_name
		else:
			raise InvalidTenantException()
	def db_for_read(self, model, **hints):
		print("read", hints)
		return self._default_db()
	def db_for_write(self, model, **hints):
		print("write", hints)
		return self._default_db()
	def allow_relation(self, obj1, obj2, **hints):
		return None
	def allow_migrate(self, db, app_label, model_name=None, **hints):
		return None
## settings.py
MIDDLEWARE = [
	"utils.tenant_db_router.TenantSubdomainMiddleware",
	"django.middleware.security.SecurityMiddleware",
	...
]
TENANT_MAP = {"localhost":"default", "tenant_1":"default"}
DATABASE_ROUTERS = ["utils.tenant_db_router.TenantDatabaseRouter"]
