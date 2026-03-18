from django.db import models
from django.contrib.auth.models import User



class Tweet(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    nickname = models.CharField(max_length=10)
    message = models.CharField(max_length=280)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return f"Tweet nick: {self.nickname} \n message:{self.message}"

class TweetImage(models.Model):
    tweet = models.ForeignKey(Tweet, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='tweet_images/')

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.CharField(max_length=160, blank=True)
    profile_image = models.ImageField(upload_to='profile_images/', blank=True)
    first_name = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=50, blank=True)
    age = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return self.user.username

class Like(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    tweet = models.ForeignKey(Tweet, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'tweet')