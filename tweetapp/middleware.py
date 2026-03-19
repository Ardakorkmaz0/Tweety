from django.utils import timezone
from tweetapp.models import Profile

class UpdateLastActiveMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Update the database first
        if request.user.is_authenticated:
            if hasattr(request.user, 'profile'):
                Profile.objects.filter(user=request.user).update(last_active=timezone.now())
        
        # 2. Then generate the page response with fresh data
        response = self.get_response(request)
        return response