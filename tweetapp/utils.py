import re
import time
from functools import wraps
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.http import JsonResponse


# --- Image upload validation ---------------------------------------------
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_IMAGE_CONTENT_TYPES = {
    'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'
}
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}


def validate_image(file_obj, max_bytes=MAX_IMAGE_BYTES):
    """Validate an uploaded image: size, content-type, extension, and a Pillow
    integrity check. Raises ValidationError on failure, returns the file_obj
    on success (with file pointer reset)."""
    if file_obj is None:
        return None

    # Size check
    size = getattr(file_obj, 'size', None)
    if size is not None and size > max_bytes:
        raise ValidationError(
            f'Image is too large ({size // 1024} KB). Max {max_bytes // 1024 // 1024} MB.'
        )

    # Content-type check (browser-supplied; not authoritative on its own)
    content_type = getattr(file_obj, 'content_type', '') or ''
    if content_type and content_type.lower() not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise ValidationError(f'Unsupported image type: {content_type}.')

    # Extension check
    name = getattr(file_obj, 'name', '') or ''
    ext = ''
    if '.' in name:
        ext = '.' + name.rsplit('.', 1)[-1].lower()
    if ext and ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(f'Unsupported image extension: {ext}.')

    # Pillow verify — confirms the bytes are actually a parseable image and
    # not, e.g., a script with an .png extension.
    try:
        from PIL import Image
    except ImportError:
        # Pillow is a Django dependency for ImageField; if it's missing the
        # ImageField itself wouldn't work. Skip the verify but keep other
        # checks above.
        Image = None
    if Image is not None:
        try:
            file_obj.seek(0)
            img = Image.open(file_obj)
            img.verify()
        except Exception:
            raise ValidationError('Uploaded file is not a valid image.')
        finally:
            try:
                file_obj.seek(0)
            except Exception:
                pass

    return file_obj


# --- Simple rate limiting --------------------------------------------------
def _client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '0.0.0.0')


def rate_limit(key, limit, window):
    """Per-user (or per-IP for anonymous) rate limit using the cache.

    `key` is a stable string identifying the endpoint family (e.g. 'send_msg').
    `limit` requests allowed per `window` seconds. On exceed, returns a 429
    JsonResponse for AJAX/JSON paths or sets a flag the view can ignore.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.user.is_authenticated:
                ident = f'u{request.user.pk}'
            else:
                ident = f'i{_client_ip(request)}'
            cache_key = f'rl:{key}:{ident}'
            now = time.time()
            bucket = cache.get(cache_key) or []
            # Drop entries outside the window
            bucket = [t for t in bucket if now - t < window]
            if len(bucket) >= limit:
                retry = int(window - (now - bucket[0])) + 1
                return JsonResponse(
                    {'error': 'Too many requests. Slow down.', 'retry_after': retry},
                    status=429,
                )
            bucket.append(now)
            cache.set(cache_key, bucket, timeout=window)
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


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
