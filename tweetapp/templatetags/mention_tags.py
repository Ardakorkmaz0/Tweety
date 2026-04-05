import re
from django import template
from django.contrib.auth.models import User
from django.utils.safestring import mark_safe
from django.utils.html import escape

register = template.Library()


@register.filter(name='linkify_mentions')
def linkify_mentions(text):
    if not text:
        return text
    escaped = escape(text)
    usernames = set(re.findall(r'@([\w.]+)', escaped))
    if not usernames:
        return mark_safe(escaped)
    valid_users = set(User.objects.filter(username__in=usernames).values_list('username', flat=True))

    def replace_mention(match):
        username = match.group(1)
        if username in valid_users:
            return (
                f'<a href="/tweetapp/profile/{username}/" '
                f'style="color: var(--neon-green); font-weight: 600;" '
                f'onclick="event.stopPropagation()">@{username}</a>'
            )
        return match.group(0)

    return mark_safe(re.sub(r'@([\w.]+)', replace_mention, escaped))
