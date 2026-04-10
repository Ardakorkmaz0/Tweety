from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import datetime



class Tweet(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    nickname = models.CharField(max_length=10)
    message = models.CharField(max_length=3000)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    VISIBILITY_CHOICES = [('public', 'Public'), ('followers', 'Followers Only')]
    visibility = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default='public')

    def can_edit(self):
        return (timezone.now() - self.created_at).total_seconds() < 300

    def __str__(self):
        return f"Tweet nick: {self.nickname} \n message:{self.message}"

class TweetImage(models.Model):
    tweet = models.ForeignKey(Tweet, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='tweet_images/')

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.CharField(max_length=160, blank=True)
    profile_image = models.ImageField(upload_to='profile_images/', blank=True)
    THEME_CHOICES = [('dark', 'Dark'), ('light', 'Light')]
    theme_preference = models.CharField(max_length=10, choices=THEME_CHOICES, default='dark')
    first_name = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=50, blank=True)
    age = models.PositiveIntegerField(null=True, blank=True)
    require_follow_requests = models.BooleanField(default=False)
    last_active = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.user.username

class Like(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    tweet = models.ForeignKey(Tweet, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'tweet')

class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    tweet = models.ForeignKey(Tweet, on_delete=models.CASCADE, related_name='comments')
    message = models.CharField(max_length=3000)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}: {self.message[:30]}"

class PatchNote(models.Model):
    title = models.CharField(max_length=100)
    content = models.TextField()
    version = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.version} - {self.title}"

    class Meta:
        ordering = ['-created_at']


class Group(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='group_images/', blank=True, null=True)
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_groups')
    is_private = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class GroupMembership(models.Model):
    ROLE_CHOICES = [('admin', 'Admin'), ('member', 'Member')]
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_memberships')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='member')
    is_muted = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('group', 'user')

class GroupMessage(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='messages')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField(max_length=500, blank=True)
    image = models.ImageField(upload_to='group_messages/', blank=True, null=True)
    reply_to = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='replies')
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

class GroupInvite(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='invites')
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_invites')
    invited_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_invites')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('group', 'invited_user')

class GroupJoinRequest(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='join_requests')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='join_requests')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('group', 'user')


class Follow(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following')
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'following')

class FollowRequest(models.Model):
    sender = models.ForeignKey(User, related_name='sent_follow_requests', on_delete=models.CASCADE)
    receiver = models.ForeignKey(User, related_name='received_follow_requests', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('sender', 'receiver')

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('like', 'Like'),
        ('comment', 'Comment'),
        ('thread', 'Thread Comment'),
        ('follow', 'Follow'),
        ('follow_request', 'Follow Request'),
        ('follow_accept', 'Follow Request Accepted'),
        ('group_invite', 'Group Invite'),
        ('group_join_request', 'Group Join Request'),
        ('group_mention', 'Group Mention'),
        ('message', 'Direct Message'),
        ('mention', 'Mention'),
    )
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    actor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='actions')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    tweet = models.ForeignKey('Tweet', on_delete=models.CASCADE, null=True, blank=True)
    group = models.ForeignKey('Group', on_delete=models.CASCADE, null=True, blank=True)
    follow_request = models.ForeignKey('FollowRequest', on_delete=models.CASCADE, null=True, blank=True)
    chat_thread = models.ForeignKey('ChatThread', on_delete=models.CASCADE, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.actor.username} -> {self.recipient.username}: {self.notification_type}"

class ChatThread(models.Model):
    participants = models.ManyToManyField(User, related_name='chat_threads')
    updated_at = models.DateTimeField(auto_now=True)
    theme_color = models.CharField(max_length=50, default='#10F28C') # Default to neon green
    background_image = models.ImageField(upload_to='chat_backgrounds/', null=True, blank=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"Chat {self.pk}"

class Message(models.Model):
    thread = models.ForeignKey(ChatThread, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    image = models.ImageField(upload_to='message_images/', null=True, blank=True)
    is_read = models.BooleanField(default=False)
    reply_to = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='replies')
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Msg {self.pk} in Thread {self.thread.pk} by {self.sender.username}"

class PushSubscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='push_subscriptions')
    endpoint = models.URLField(max_length=500)
    p256dh = models.CharField(max_length=200)
    auth = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'endpoint')

    def __str__(self):
        return f"Push sub for {self.user.username}"


class NotificationPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_preferences')
    like = models.BooleanField(default=True)
    comment = models.BooleanField(default=True)
    thread = models.BooleanField(default=True)
    follow = models.BooleanField(default=True)
    follow_request = models.BooleanField(default=True)
    follow_accept = models.BooleanField(default=True)
    group_invite = models.BooleanField(default=True)
    group_join_request = models.BooleanField(default=True)
    group_mention = models.BooleanField(default=True)
    message = models.BooleanField(default=True)
    mention = models.BooleanField(default=True)

    def __str__(self):
        return f"Notification prefs for {self.user.username}"


class GameScore(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='game_scores')
    game = models.CharField(max_length=50, default='flappy_tweet')
    score = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-score']

    def __str__(self):
        return f"{self.user.username} - {self.game}: {self.score}"


class GameSettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='game_settings')
    bg_images = models.TextField(default='[]')  # JSON array of base64 images
    bg_selected = models.IntegerField(default=-1)
    pipe_images = models.TextField(default='[]')
    pipe_selected = models.IntegerField(default=-1)
    bird_images = models.TextField(default='[]')
    bird_selected = models.CharField(max_length=50, default='yellow')
    accent_color = models.CharField(max_length=7, default='#10F28C')

    def __str__(self):
        return f"Game settings for {self.user.username}"