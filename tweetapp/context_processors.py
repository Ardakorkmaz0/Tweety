# tweetapp/context_processors.py
import datetime
import random

from django.contrib.auth.models import User
from django.utils import timezone

from .models import Follow, Message, Notification, Profile


def unread_notifications(request):
    # Kept for backwards compatibility — actual work happens in
    # global_sidebar_data() to avoid duplicate query passes per request.
    return {}


def global_sidebar_data(request):
    """Provide sidebar data + unread counts globally in a single pass."""
    user_theme_preference = 'dark'

    if not request.user.is_authenticated:
        return {
            'suggested_users': User.objects.select_related('profile')[:5],
            'online_users': User.objects.none(),
            'user_theme_preference': user_theme_preference,
            'unread_notif_count': 0,
            'unread_message_count': 0,
        }

    try:
        profile = getattr(request.user, 'profile', None)
        if profile is None:
            profile = Profile.objects.get_or_create(user=request.user)[0]
        user_theme_preference = profile.theme_preference
    except Exception:
        user_theme_preference = 'dark'

    try:
        # Suggested users — avoid ORDER BY RANDOM() (full table sort).
        # Pull a small candidate window of IDs and shuffle in Python.
        following_ids = list(
            Follow.objects.filter(follower=request.user).values_list('following_id', flat=True)
        )
        candidate_ids = list(
            User.objects.exclude(pk__in=following_ids + [request.user.pk])
                .values_list('pk', flat=True)[:200]
        )
        random.shuffle(candidate_ids)
        suggested_users = list(
            User.objects.filter(pk__in=candidate_ids[:5]).select_related('profile')
        )
        # Ensure all suggested users have a profile
        for su in suggested_users:
            if not hasattr(su, 'profile') or su.profile is None:
                try:
                    Profile.objects.get_or_create(user=su)
                except Exception:
                    pass
    except Exception:
        suggested_users = []

    try:
        five_minutes_ago = timezone.now() - datetime.timedelta(minutes=5)
        online_users = User.objects.filter(
            profile__last_active__gte=five_minutes_ago
        ).select_related('profile')[:10]
    except Exception:
        online_users = User.objects.none()

    try:
        unread_notif_count = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).count()
    except Exception:
        unread_notif_count = 0

    try:
        unread_message_count = Message.objects.filter(
            thread__participants=request.user,
            is_read=False,
        ).exclude(sender=request.user).count()
    except Exception:
        unread_message_count = 0

    return {
        'suggested_users': suggested_users,
        'online_users': online_users,
        'user_theme_preference': user_theme_preference,
        'unread_notif_count': unread_notif_count,
        'unread_message_count': unread_message_count,
    }

