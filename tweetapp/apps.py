from django.apps import AppConfig


class TweetappConfig(AppConfig):
    name = 'tweetapp'

    def ready(self):
        import tweetapp.signals  # noqa: F401
