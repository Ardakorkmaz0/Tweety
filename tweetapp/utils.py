import re
from django.contrib.auth.models import User


def should_notify(user, notification_type):
    """Check if user wants to receive this notification type."""
    try:
        prefs = user.notification_preferences
        return getattr(prefs, notification_type, True)
    except Exception:
        return True


def extract_mentions(text):
    """Return a set of usernames mentioned with @username in text."""
    # Allow dots in username
    return set(re.findall(r'@([\w.]+)', text or ''))


def process_mentions(text, actor, tweet=None, comment_obj=None, message_obj=None):
    """Find @mentions, create Notification + push for each valid user."""
    from tweetapp.models import Notification
    from tweetapp.views import send_push_notification

    usernames = extract_mentions(text)
    if not usernames:
        return

    mentioned_users = User.objects.filter(username__in=usernames)

    for user in mentioned_users:
        if user == actor:
            continue
        if not should_notify(user, 'mention'):
            continue
            
        chat_thread = message_obj.thread if message_obj else None
        
        Notification.objects.create(
            recipient=user,
            actor=actor,
            notification_type='mention',
            tweet=tweet,
            chat_thread=chat_thread
        )
        
        tweet_ref = tweet or (comment_obj.tweet if comment_obj else None)
        if tweet_ref:
            url = f'/tweetapp/tweet/{tweet_ref.pk}/'
        elif chat_thread:
            url = f'/tweetapp/chat/{chat_thread.pk}/'
        else:
            url = '/tweetapp/notifications/'
            
        send_push_notification(
            user=user,
            title='Tweety',
            body=f'@{actor.username} mentioned you',
            url=url,
        )
