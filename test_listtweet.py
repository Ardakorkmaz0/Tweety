import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangotweet.settings')
django.setup()

from django.test import RequestFactory
from tweetapp.views import listtweet
from django.contrib.auth.models import User

request = RequestFactory().get('/?tab=following')
request.session = {}
request.user = User.objects.first()

try:
    response = listtweet(request)
    print("STATUS", response.status_code)
except Exception as e:
    import traceback
    traceback.print_exc()
