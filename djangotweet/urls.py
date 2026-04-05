"""
URL configuration for djangotweet project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from django.shortcuts import render
from django.http import HttpResponse
import os
def service_worker(request):
    from django.contrib.staticfiles import finders
    sw_path = finders.find('sw.js')
    if sw_path:
        with open(sw_path, 'r') as f:
            response = HttpResponse(f.read(), content_type='application/javascript')
        response['Service-Worker-Allowed'] = '/'
        return response
    return HttpResponse('// sw not found', content_type='application/javascript', status=404)




def custom_404(request, exception):
    return render(request, '404.html', status=404)


handler404 = custom_404

urlpatterns = [
    path('admin/', admin.site.urls),
    path("tweetapp/", include('tweetapp.urls')),
    path('', include('tweetapp.urls')),
    path('', include('django.contrib.auth.urls')),
    # Always serve media files (Django's static() silently fails when DEBUG=False)
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    path('sw.js', service_worker, name='service_worker'),

]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += [path('test-404/', lambda r: custom_404(r, None))]
