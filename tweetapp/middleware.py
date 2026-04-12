from django.core.cache import cache
from django.utils import timezone
from tweetapp.models import Profile


class UpdateLastActiveMiddleware:
    """Throttled last_active update — at most once per 60s per user."""

    THROTTLE_SECONDS = 60

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            cache_key = f'last_active_{request.user.pk}'
            if not cache.get(cache_key):
                Profile.objects.filter(user=request.user).update(last_active=timezone.now())
                cache.set(cache_key, 1, timeout=self.THROTTLE_SECONDS)

        return self.get_response(request)
