# tweetapp/context_processors.py
from .models import Notification

def unread_notifications(request):
    if request.user.is_authenticated:
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return {'unread_notif_count': count}
    return {'unread_notif_count': 0}