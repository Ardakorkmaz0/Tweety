# tweetapp/context_processors.py
from .models import Notification, Message

def unread_notifications(request):
    if request.user.is_authenticated:
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        unread_msgs = Message.objects.filter(
            thread__participants=request.user,
            is_read=False
        ).exclude(sender=request.user).count()
        return {
            'unread_notif_count': count,
            'unread_message_count': unread_msgs,
        }
    return {'unread_notif_count': 0, 'unread_message_count': 0}