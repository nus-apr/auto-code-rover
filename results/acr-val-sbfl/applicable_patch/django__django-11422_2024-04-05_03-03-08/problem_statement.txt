Autoreloader with StatReloader doesn't track changes in manage.py.
Description
	 
		(last modified by Mariusz Felisiak)
	 
This is a bit convoluted, but here we go.
Environment (OSX 10.11):
$ python -V
Python 3.6.2
$ pip -V
pip 19.1.1
$ pip install Django==2.2.1
Steps to reproduce:
Run a server python manage.py runserver
Edit the manage.py file, e.g. add print(): 
def main():
	print('sth')
	os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ticket_30479.settings')
	...
Under 2.1.8 (and prior), this will trigger the auto-reloading mechanism. Under 2.2.1, it won't. As far as I can tell from the django.utils.autoreload log lines, it never sees the manage.py itself.
