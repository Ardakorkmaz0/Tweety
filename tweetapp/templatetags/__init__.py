from django import template

register = template.Library()

@register.filter
def is_moderator(user):
    return user.groups.filter(name='moderator').exists()