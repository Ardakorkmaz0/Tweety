from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile


@receiver(post_save, sender=User)
def create_or_update_profile(sender, instance, created, **kwargs):
    """Ensure every User always has a linked Profile row."""
    if created:
        Profile.objects.get_or_create(user=instance)
    else:
        # For existing users that somehow lost their profile
        Profile.objects.get_or_create(user=instance)
