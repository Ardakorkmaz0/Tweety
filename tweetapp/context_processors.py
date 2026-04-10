# tweetapp/context_processors.py
import datetime

from django.contrib.auth.models import User
from django.utils import timezone

from .models import Follow, Message, Notification

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


def global_sidebar_data(request):
    """Provide online users and suggestions globally for the right sidebar."""
    if request.user.is_authenticated:
        following_ids = list(
            Follow.objects.filter(follower=request.user).values_list('following_id', flat=True)
        )
        suggested_users = User.objects.exclude(
            pk__in=following_ids + [request.user.pk]
        ).select_related('profile').order_by('?')[:5]

        five_minutes_ago = timezone.now() - datetime.timedelta(minutes=5)
        online_users = User.objects.filter(
            profile__last_active__gte=five_minutes_ago
        ).select_related('profile')[:10]
    else:
        suggested_users = User.objects.select_related('profile').order_by('?')[:5]
        online_users = User.objects.none()

    return {
        'suggested_users': suggested_users,
        'online_users': online_users,
    }