from django.shortcuts import render, redirect, get_object_or_404
from . import models
from django.urls import reverse, reverse_lazy
from tweetapp.forms import AddTweetForm, ProfileForm, RegisterForm
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.views.generic import CreateView
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.db.models import Count, F, OuterRef, Subquery
from django.utils import timezone
from django.core.paginator import Paginator
from django.conf import settings
import re
from django.views.decorators.csrf import csrf_exempt
import datetime
import json
import logging
from django.core.exceptions import ValidationError
from tweetapp.utils import should_notify, process_mentions, extract_mentions, validate_image, rate_limit

logger = logging.getLogger(__name__)
MAX_TWEET_IMAGES = 10



def listtweet(request):
    tab = request.GET.get('tab')
    if tab:
        request.session['active_tab'] = tab
    else:
        tab = request.session.get('active_tab', 'latest')

    liked_ids = []
    following_ids = []

    if request.user.is_authenticated:
        liked_ids = list(models.Like.objects.filter(user=request.user).values_list('tweet_id', flat=True))
        following_ids = list(models.Follow.objects.filter(follower=request.user).values_list('following_id', flat=True))
        
        visible_tweets = models.Tweet.objects.filter(
            Q(visibility='public') |
            Q(user=request.user) |
            Q(user_id__in=following_ids, visibility='followers')
        )
        if request.user.is_staff:
            visible_tweets = models.Tweet.objects.all()
    else:
        visible_tweets = models.Tweet.objects.filter(visibility='public')
        if tab == 'following':
            tab = 'latest'

    # Annotate likes/comments counts once so the template doesn't trigger N+1
    # via tweet.likes.count / tweet.comments.count per row.
    visible_tweets = visible_tweets.annotate(
        like_count=Count('likes', distinct=True),
        comment_count=Count('comments', distinct=True),
    ).select_related('user', 'user__profile').prefetch_related('images')

    # Build dynamically based on tab strategy
    if tab == 'following':
        # People you follow exclusively
        qs = visible_tweets.filter(user_id__in=following_ids).order_by('-created_at')
    elif tab == 'recommended':
        # "For You" Feed: Rank by custom engagement algorithm
        # Engagement = (Likes * 2) + (Comments * 3)
        qs = visible_tweets.annotate(
            engagement_score=(F('like_count') * 2) + (F('comment_count') * 3)
        ).order_by('-engagement_score', '-created_at')
    else:
        # "Latest" Feed
        qs = visible_tweets.order_by('-created_at')

    paginator = Paginator(qs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'liked_ids': liked_ids,
        'active_tab': tab,
    }
    return render(request, 'tweetapp/listtweet.html', context)


@login_required(login_url='/login/')
@rate_limit('tweet_post', limit=10, window=60)
def addtweetbyform(request):
    if request.method == "POST":
        form = AddTweetForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_images = request.FILES.getlist('images')
            if len(uploaded_images) > MAX_TWEET_IMAGES:
                messages.error(request, f"You can upload at most {MAX_TWEET_IMAGES} images per tweet.")
                return render(request, 'tweetapp/addtwetbyform.html', context={"form": form})

            # Validate every uploaded image (size, type, Pillow integrity)
            for file in uploaded_images:
                try:
                    validate_image(file)
                except ValidationError as e:
                    messages.error(request, e.messages[0] if e.messages else 'Invalid image upload.')
                    return render(request, 'tweetapp/addtwetbyform.html', context={"form": form})

            tweet = models.Tweet.objects.create(
                user=request.user,
                nickname=request.user.username,
                message=form.cleaned_data["message_input"],
                visibility=form.cleaned_data["visibility"]
            )
            for file in uploaded_images:
                models.TweetImage.objects.create(tweet=tweet, image=file)
            process_mentions(tweet.message, request.user, tweet=tweet)
            return redirect(reverse('tweetapp:listtweet'))
        else:
            return render(request, 'tweetapp/addtwetbyform.html', context={"form": form})
    else:
        form = AddTweetForm()
        return render(request, 'tweetapp/addtwetbyform.html', context={"form": form})


def searchtweet(request):
    query = request.GET.get('q', '')
    tab = request.GET.get('tab')
    if tab:
        request.session['active_tab'] = tab
    else:
        tab = request.session.get('active_tab', 'latest')
    
    if query:
        clean_query = query[1:] if query.startswith('@') else query
        searched_users = User.objects.filter(
            Q(username__icontains=clean_query) |
            Q(profile__first_name__icontains=clean_query) |
            Q(profile__last_name__icontains=clean_query)
        ).select_related('profile').distinct()[:15]

        if query.startswith('@'):
            nickname = query[1:]
            results = models.Tweet.objects.filter(nickname__iexact=nickname)
        else:
            results = models.Tweet.objects.filter(message__icontains=query)
            
        if request.user.is_authenticated:
            if not request.user.is_staff:
                following_ids = list(models.Follow.objects.filter(follower=request.user).values_list('following_id', flat=True))
                results = results.filter(
                    Q(visibility='public') |
                    Q(user=request.user) |
                    Q(user_id__in=following_ids, visibility='followers')
                )
        else:
            results = results.filter(visibility='public')
            
        results = results.annotate(
            like_count=Count('likes', distinct=True),
            comment_count=Count('comments', distinct=True),
        ).select_related('user', 'user__profile').prefetch_related('images').order_by('-created_at')

        if tab == 'following' and request.user.is_authenticated:
            following_ids = list(models.Follow.objects.filter(follower=request.user).values_list('following_id', flat=True))
            qs = results.filter(user_id__in=following_ids)
        elif tab == 'recommended':
            qs = results.annotate(
                engagement_score=(F('like_count') * 2) + (F('comment_count') * 3)
            ).order_by('-engagement_score', '-created_at')
        else:
            qs = results
    else:
        searched_users = []
        qs = models.Tweet.objects.none()
        
    if request.user.is_authenticated:
        liked_ids = list(models.Like.objects.filter(user=request.user).values_list('tweet_id', flat=True))
    else:
        liked_ids = []
        
    paginator = Paginator(qs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'tweetapp/listtweet.html', {
        'page_obj': page_obj,
        'liked_ids': liked_ids,
        'suggested_users': [],
        'searched_users': searched_users,
        'active_tab': tab,
        'is_search': bool(query),
        'search_query': query,
    })

def profile(request, username):
    try:
        user = User.objects.get(username=username)
        if not hasattr(user, 'profile'):
            models.Profile.objects.create(user=user)
        profile_exists = True
    except User.DoesNotExist:
        user = None
        profile_exists = False

    base_tweets = models.Tweet.objects.filter(nickname__iexact=username).annotate(
        like_count=Count('likes', distinct=True),
        comment_count=Count('comments', distinct=True),
    ).select_related('user', 'user__profile').prefetch_related('images')

    if request.user.is_authenticated:
        if request.user.is_staff or (user and request.user == user):
            tweets = base_tweets.order_by('-created_at')
        else:
            i_follow_author = user and models.Follow.objects.filter(follower=request.user, following=user).exists()
            if i_follow_author:
                tweets = base_tweets.order_by('-created_at')
            else:
                tweets = base_tweets.filter(visibility='public').order_by('-created_at')
    else:
        tweets = base_tweets.filter(visibility='public').order_by('-created_at')
    tweet_count = tweets.count()

    if request.user.is_authenticated:
        liked_ids = list(models.Like.objects.filter(user=request.user).values_list('tweet_id', flat=True))
    else:
        liked_ids = []

    user_comments = []
    is_following = False
    has_pending_request = False
    follower_count = 0
    following_count = 0
    if user:
        user_comments = models.Comment.objects.filter(user=user).select_related('tweet').order_by('-created_at')
        follower_count = models.Follow.objects.filter(following=user).count()
        following_count = models.Follow.objects.filter(follower=user).count()
        if request.user.is_authenticated and request.user != user:
            is_following = models.Follow.objects.filter(follower=request.user, following=user).exists()
            if not is_following:
                has_pending_request = models.FollowRequest.objects.filter(sender=request.user, receiver=user).exists()
            
    context = {
        'profile_user': user,
        'profile_exists': profile_exists,
        'tweets': tweets,
        'tweet_count': tweet_count,
        'searched_username': username,
        'liked_ids': liked_ids,
        'user_comments': user_comments,
        'is_following': is_following,
        'has_pending_request': has_pending_request,
        'follower_count': follower_count,
        'following_count': following_count,
    }
    return render(request, 'tweetapp/profile.html', context=context)


def edit_profile(request):
    if not request.user.is_authenticated:
        messages.warning(request, "Profil düzenlemek için giriş yapmalısın!")
        return redirect('/login/')

    if not hasattr(request.user, 'profile'):
        models.Profile.objects.create(user=request.user)

    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES)
        if form.is_valid():
            profile = request.user.profile
            profile.first_name = form.cleaned_data['first_name']
            profile.last_name = form.cleaned_data['last_name']
            profile.age = form.cleaned_data['age']
            profile.bio = form.cleaned_data['bio']
            profile.require_follow_requests = form.cleaned_data['require_follow_requests']
            if form.cleaned_data['profile_image']:
                profile.profile_image = form.cleaned_data['profile_image']
            profile.save()
            request.user.email = form.cleaned_data.get('email', '')
            request.user.save(update_fields=['email'])
            return redirect('tweetapp:profile', username=request.user.username)
        else:
            return render(request, 'tweetapp/edit_profile.html', context={"form": form})
    else:
        profile = request.user.profile
        form = ProfileForm(initial={
            'first_name': profile.first_name,
            'last_name': profile.last_name,
            'email': request.user.email,
            'age': profile.age,
            'bio': profile.bio,
            'require_follow_requests': profile.require_follow_requests,
        })
        return render(request, 'tweetapp/edit_profile.html', context={"form": form})


@login_required(login_url='/login/')
def account_settings(request):
    error = ''
    success = ''
    if request.method == 'POST' and 'new_username' in request.POST:
        new_username = request.POST.get('new_username', '').strip()
        if not new_username:
            error = 'Username cannot be empty.'
        elif new_username == request.user.username:
            error = 'This is already your username.'
        elif User.objects.filter(username=new_username).exists():
            error = 'This username is already taken.'
        elif len(new_username) > 150:
            error = 'Username must be 150 characters or fewer.'
        else:
            old_username = request.user.username
            # Update username
            request.user.username = new_username
            request.user.save(update_fields=['username'])
            # Update tweet nicknames
            models.Tweet.objects.filter(nickname__iexact=old_username).update(nickname=new_username)
            mention_re = re.compile(r'@' + re.escape(old_username) + r'(?!\w)', re.IGNORECASE)
            replacement = '@' + new_username

            # Update @mentions in tweets (single bulk_update instead of N saves)
            tweets_to_update = list(
                models.Tweet.objects.filter(message__iregex=r'@' + old_username + r'(?!\w)')
            )
            for tweet in tweets_to_update:
                tweet.message = mention_re.sub(replacement, tweet.message)
            if tweets_to_update:
                models.Tweet.objects.bulk_update(tweets_to_update, ['message'], batch_size=500)

            # Update @mentions in comments
            comments_to_update = list(
                models.Comment.objects.filter(message__iregex=r'@' + old_username + r'(?!\w)')
            )
            for comment in comments_to_update:
                comment.message = mention_re.sub(replacement, comment.message)
            if comments_to_update:
                models.Comment.objects.bulk_update(comments_to_update, ['message'], batch_size=500)
            success = 'Username changed successfully!'
    context = {
        'email': request.user.email,
        'username_error': error,
        'username_success': success,
    }
    return render(request, 'tweetapp/settings.html', context)


class RegisterView(CreateView):
    form_class = RegisterForm
    template_name = 'registration/register.html'
    success_url = '/login/'

    def form_valid(self, form):
        response = super().form_valid(form)
        models.Profile.objects.create(
            user=self.object,
            first_name=form.cleaned_data.get('first_name', ''),
            last_name=form.cleaned_data.get('last_name', ''),
            age=form.cleaned_data.get('age'),
        )
        models.NotificationPreference.objects.create(user=self.object)
        return response


@login_required(login_url='/login/')
def delete_tweet(request, pk):
    if request.method != "POST":
        return redirect(reverse('tweetapp:listtweet'))
    tweet = get_object_or_404(models.Tweet, pk=pk)
    if request.user == tweet.user or request.user.is_staff:
        tweet.delete()
    return redirect(reverse('tweetapp:listtweet'))


@rate_limit('like', limit=60, window=60)
def like_tweet(request, pk):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'login'}, status=401)
    tweet = get_object_or_404(models.Tweet, pk=pk)
    
    # Security: Prevent unauthorized users from liking private tweets
    if tweet.visibility == 'followers' and request.user != tweet.user and not request.user.is_staff:
        if not models.Follow.objects.filter(follower=request.user, following=tweet.user).exists():
            return JsonResponse({'error': 'unauthorized'}, status=403)
            
    like, created = models.Like.objects.get_or_create(user=request.user, tweet=tweet)
    if not created:
        like.delete()
        models.Notification.objects.filter(
            recipient=tweet.user, actor=request.user,
            notification_type='like', tweet=tweet
        ).delete()
    else:
        if request.user != tweet.user and should_notify(tweet.user, 'like'):
            models.Notification.objects.create(
                recipient=tweet.user, actor=request.user,
                notification_type='like', tweet=tweet
            )
            send_push_notification(
                user=tweet.user,
                title='Tweety',
                body=f'@{request.user.username} liked your tweet',
                url=f'/tweetapp/tweet/{tweet.pk}/'
            )
    return JsonResponse({
        'liked': created,
        'count': tweet.likes.count()
    })


@login_required(login_url='/login/')
@rate_limit('comment', limit=20, window=60)
def add_comment(request, pk):
    from django.http import Http404
    if request.method != "POST":
        return redirect(reverse('tweetapp:listtweet'))
    message = request.POST.get('comment_message', '')
    image = request.FILES.get('comment_image')

    if not message and not image:
        return redirect(request.META.get('HTTP_REFERER', reverse('tweetapp:listtweet')))

    tweet = get_object_or_404(models.Tweet, pk=pk)

    # Security: Prevent unauthorized users from commenting on private tweets
    if tweet.visibility == 'followers' and request.user != tweet.user and not request.user.is_staff:
        if not models.Follow.objects.filter(follower=request.user, following=tweet.user).exists():
            raise Http404()

    # Image validation
    if image:
        try:
            validate_image(image)
        except ValidationError as e:
            messages.error(request, e.messages[0] if e.messages else 'Invalid image')
            return redirect(request.META.get('HTTP_REFERER', reverse('tweetapp:listtweet')))

    # Reply-to parent comment
    parent = None
    parent_id = request.POST.get('parent_id')
    if parent_id:
        parent = models.Comment.objects.filter(pk=parent_id, tweet=tweet).first()

    comment_obj = models.Comment.objects.create(
        user=request.user, tweet=tweet, message=message,
        image=image, parent=parent,
    )

    # Notify tweet owner
    if request.user != tweet.user and should_notify(tweet.user, 'comment'):
        models.Notification.objects.create(
            recipient=tweet.user, actor=request.user,
            notification_type='comment', tweet=tweet
        )
        send_push_notification(
            user=tweet.user,
            title='Tweety',
            body=f'@{request.user.username} commented on your tweet',
            url=f'/tweetapp/tweet/{tweet.pk}/'
        )

    # Notify parent comment owner on reply
    if parent and parent.user != request.user and parent.user != tweet.user:
        if should_notify(parent.user, 'thread'):
            models.Notification.objects.create(
                recipient=parent.user, actor=request.user,
                notification_type='thread', tweet=tweet
            )
            send_push_notification(
                user=parent.user,
                title='Tweety',
                body=f'@{request.user.username} replied to your comment',
                url=f'/tweetapp/tweet/{tweet.pk}/'
            )

    # Notify other commenters in the thread
    other_commenters = User.objects.filter(
        comment__tweet=tweet
    ).exclude(id=request.user.id).exclude(id=tweet.user.id)
    if parent:
        other_commenters = other_commenters.exclude(id=parent.user.id)
    other_commenters = other_commenters.distinct()

    for commenter in other_commenters:
        if should_notify(commenter, 'thread'):
            models.Notification.objects.create(
                recipient=commenter, actor=request.user,
                notification_type='thread', tweet=tweet
            )
            send_push_notification(
                user=commenter,
                title='Tweety',
                body=f'@{request.user.username} also commented on a tweet you commented on',
                url=f'/tweetapp/tweet/{tweet.pk}/'
            )

    process_mentions(message, request.user, tweet=tweet, comment_obj=comment_obj)
    return redirect(request.META.get('HTTP_REFERER', reverse('tweetapp:listtweet')))


@login_required(login_url='/login/')
def delete_comment(request, pk):
    if request.method != "POST":
        return redirect(reverse('tweetapp:listtweet'))
    comment = get_object_or_404(models.Comment, pk=pk)
    if request.user == comment.user or request.user.is_staff:
        comment.delete()
    return redirect(request.META.get('HTTP_REFERER', reverse('tweetapp:listtweet')))


@login_required(login_url='/login/')
def userlist(request):
    if request.user.is_staff:
        users_qs = User.objects.select_related('profile').order_by('-profile__last_active')
    else:
        users_qs = User.objects.select_related('profile').order_by('username')

    paginator = Paginator(users_qs, 30)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'users': page_obj,
        'page_obj': page_obj,
    }
    return render(request, 'tweetapp/userlist.html', context)


@login_required(login_url='/login/')
def edit_tweet(request, pk):
    if request.method != "POST":
        return redirect(reverse('tweetapp:listtweet'))
    tweet = get_object_or_404(models.Tweet, pk=pk)
    if request.user != tweet.user or not tweet.can_edit():
        messages.warning(request, "Editing time expired! (5 min limit)")
        return redirect(reverse('tweetapp:listtweet'))
    message = request.POST.get('message', '')
    if message:
        tweet.message = message
        tweet.save()
    return redirect(request.META.get('HTTP_REFERER', reverse('tweetapp:listtweet')))


def patchnotes(request):
    notes = models.PatchNote.objects.all()
    return render(request, 'tweetapp/patchnotes.html', {'notes': notes})


@login_required(login_url='/login/')
def add_patchnote(request):
    if not request.user.is_staff:
        return redirect(reverse('tweetapp:patchnotes'))
    if request.method == "POST":
        title = request.POST.get('title', '')
        content = request.POST.get('content', '')
        version = request.POST.get('version', '')
        if title and content:
            models.PatchNote.objects.create(title=title, content=content, version=version)
    return redirect(reverse('tweetapp:patchnotes'))


@login_required(login_url='/login/')
def delete_patchnote(request, pk):
    if not request.user.is_staff:
        return redirect(reverse('tweetapp:patchnotes'))
    if request.method != "POST":
        return redirect(reverse('tweetapp:patchnotes'))
    note = get_object_or_404(models.PatchNote, pk=pk)
    note.delete()
    return redirect(reverse('tweetapp:patchnotes'))


@login_required(login_url='/login/')
def group_list(request):
    my_groups = models.Group.objects.filter(memberships__user=request.user)
    other_groups = models.Group.objects.exclude(memberships__user=request.user)
    invites = models.GroupInvite.objects.filter(invited_user=request.user)
    pending_request_ids = list(models.GroupJoinRequest.objects.filter(user=request.user).values_list('group_id', flat=True))
    return render(request, 'tweetapp/group_list.html', {
        'my_groups': my_groups,
        'other_groups': other_groups,
        'invites': invites,
        'pending_request_ids': pending_request_ids,
    })


@login_required(login_url='/login/')
def create_group(request):
    if request.method == "POST":
        name = request.POST.get('name', '')
        description = request.POST.get('description', '')
        is_private = request.POST.get('is_private') == 'on'
        image = request.FILES.get('image')
        if image:
            try:
                validate_image(image)
            except ValidationError as e:
                messages.error(request, e.messages[0] if e.messages else 'Invalid image upload.')
                return render(request, 'tweetapp/create_group.html')
        if name:
            group = models.Group.objects.create(
                name=name, description=description,
                is_private=is_private, creator=request.user, image=image
            )
            models.GroupMembership.objects.create(group=group, user=request.user, role='admin')
            return redirect('tweetapp:group_detail', pk=group.pk)
    return render(request, 'tweetapp/create_group.html')


@login_required(login_url='/login/')
def group_detail(request, pk):
    group = get_object_or_404(models.Group, pk=pk)
    is_member = group.memberships.filter(user=request.user).exists()
    if not is_member:
        return render(request, 'tweetapp/group_locked.html', {'group': group})

    membership = group.memberships.get(user=request.user)
    members = group.memberships.select_related('user__profile').all()
    messages_list = group.messages.select_related('user__profile', 'reply_to__user').all()
    join_requests = group.join_requests.select_related('user').all() if membership.role == 'admin' else []
    other_admins_exist = group.memberships.filter(role='admin').exclude(user=request.user).exists()
    five_minutes_ago = timezone.now() - datetime.timedelta(minutes=5)
    online_user_ids = set(
        User.objects.filter(
            profile__last_active__gte=five_minutes_ago,
            group_memberships__group=group
        ).values_list('id', flat=True)
    )

    return render(request, 'tweetapp/group_detail.html', {
        'group': group,
        'membership': membership,
        'members': members,
        'messages_list': messages_list,
        'join_requests': join_requests,
        'is_muted': membership.is_muted,
        'other_admins_exist': other_admins_exist,
        'online_user_ids': online_user_ids,
    })


@login_required(login_url='/login/')
@rate_limit('group_msg', limit=30, window=60)
def group_send_message(request, pk):
    group = get_object_or_404(models.Group, pk=pk)
    if not group.memberships.filter(user=request.user).exists():
        return redirect('tweetapp:group_list')
    if request.method == "POST":
        message = request.POST.get('message', '')
        image = request.FILES.get('image')
        if image:
            try:
                validate_image(image)
            except ValidationError as e:
                messages.error(request, e.messages[0] if e.messages else 'Invalid image upload.')
                return redirect('tweetapp:group_detail', pk=pk)
        if message or image:
            models.GroupMessage.objects.create(group=group, user=request.user, message=message, image=image)
    return redirect('tweetapp:group_detail', pk=pk)


@login_required(login_url='/login/')
def group_join(request, pk):
    group = get_object_or_404(models.Group, pk=pk)
    if group.is_private:
        return redirect('tweetapp:group_list')
    if not group.memberships.filter(user=request.user).exists():
        models.GroupMembership.objects.create(group=group, user=request.user, role='member')
    return redirect('tweetapp:group_detail', pk=pk)


@login_required(login_url='/login/')
def group_leave(request, pk):
    group = get_object_or_404(models.Group, pk=pk)
    membership = group.memberships.filter(user=request.user).first()
    if membership:
        if membership.role == 'admin':
            other_admins = group.memberships.filter(role='admin').exclude(user=request.user)
            if not other_admins.exists():
                messages.warning(request, "You must promote another member to admin before leaving.")
                return redirect('tweetapp:group_detail', pk=pk)
        membership.delete()
    return redirect('tweetapp:group_list')


@login_required(login_url='/login/')
def group_invite(request, pk):
    group = get_object_or_404(models.Group, pk=pk)
    if not group.memberships.filter(user=request.user, role='admin').exists():
        return redirect('tweetapp:group_detail', pk=pk)
    if request.method == "POST":
        username = request.POST.get('username', '')
        try:
            invited_user = User.objects.get(username=username)
            if not group.memberships.filter(user=invited_user).exists():
                models.GroupInvite.objects.get_or_create(
                    group=group, invited_user=invited_user, invited_by=request.user
                )
                models.Notification.objects.create(
                    recipient=invited_user, actor=request.user,
                    notification_type='group_invite', group=group
                )
        except User.DoesNotExist:
            messages.warning(request, "User not found!")
    return redirect('tweetapp:group_detail', pk=pk)


@login_required(login_url='/login/')
def group_accept_invite(request, pk):
    invite = get_object_or_404(models.GroupInvite, pk=pk, invited_user=request.user)
    group_pk = invite.group.pk
    models.GroupMembership.objects.create(group=invite.group, user=request.user, role='member')
    invite.delete()
    return redirect('tweetapp:group_detail', pk=group_pk)


@login_required(login_url='/login/')
def group_decline_invite(request, pk):
    invite = get_object_or_404(models.GroupInvite, pk=pk, invited_user=request.user)
    invite.delete()
    return redirect('tweetapp:group_list')


@login_required(login_url='/login/')
def group_kick(request, pk, user_id):
    group = get_object_or_404(models.Group, pk=pk)
    if not group.memberships.filter(user=request.user, role='admin').exists():
        return redirect('tweetapp:group_detail', pk=pk)
    membership = group.memberships.filter(user_id=user_id, role='member').first()
    if membership:
        membership.delete()
    return redirect('tweetapp:group_detail', pk=pk)


@login_required(login_url='/login/')
def group_delete(request, pk):
    if request.method != "POST":
        return redirect('tweetapp:group_list')
    group = get_object_or_404(models.Group, pk=pk)
    if group.creator == request.user or request.user.is_staff:
        group.delete()
    return redirect('tweetapp:group_list')


@login_required(login_url='/login/')
def group_request_join(request, pk):
    group = get_object_or_404(models.Group, pk=pk)
    if not group.memberships.filter(user=request.user).exists():
        created = models.GroupJoinRequest.objects.get_or_create(group=group, user=request.user)[1]
        if created:
            admins = group.memberships.filter(role='admin').select_related('user')
            for admin_membership in admins:
                if should_notify(admin_membership.user, 'group_join_request'):
                    models.Notification.objects.create(
                        recipient=admin_membership.user,
                        actor=request.user,
                        notification_type='group_join_request',
                        group=group,
                    )
                    send_push_notification(
                        user=admin_membership.user,
                        title='Tweety',
                        body=f'@{request.user.username} requested to join {group.name}',
                        url=f'/tweetapp/groups/{group.pk}/',
                    )
    return redirect('tweetapp:group_list')


@login_required(login_url='/login/')
def group_accept_request(request, pk):
    join_request = get_object_or_404(models.GroupJoinRequest, pk=pk)
    group = join_request.group
    if group.memberships.filter(user=request.user, role='admin').exists():
        models.GroupMembership.objects.create(group=group, user=join_request.user, role='member')
        join_request.delete()
    return redirect('tweetapp:group_detail', pk=group.pk)


@login_required(login_url='/login/')
def group_decline_request(request, pk):
    join_request = get_object_or_404(models.GroupJoinRequest, pk=pk)
    group = join_request.group
    if group.memberships.filter(user=request.user, role='admin').exists():
        join_request.delete()
    return redirect('tweetapp:group_detail', pk=group.pk)


def linkify_mentions_html(text):
    """Server-side mention linkification for JSON API responses."""
    if not text:
        return text
    from django.utils.html import escape as html_escape
    escaped = html_escape(text)
    usernames = set(re.findall(r'@(\w+)', escaped))
    if not usernames:
        return escaped
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
    return re.sub(r'@(\w+)', replace_mention, escaped)


def notify_group_members(group, sender, content, msg):
    """Push notification to all non-muted members except sender."""
    members = group.memberships.filter(is_muted=False).exclude(user=sender).select_related('user')
    push_body = content[:100] if content else 'Sent an image'
    for m in members:
        send_push_notification(
            user=m.user,
            title=f'{group.name}',
            body=f'@{sender.username}: {push_body}',
            url=f'/tweetapp/groups/{group.pk}/',
        )


def process_group_mentions(text, actor, group, msg):
    """Handle @mentions in group messages."""
    usernames = extract_mentions(text)
    if not usernames:
        return
    mentioned_users = User.objects.filter(username__in=usernames)
    for user in mentioned_users:
        if user == actor:
            continue
        if not should_notify(user, 'group_mention'):
            continue
        models.Notification.objects.create(
            recipient=user, actor=actor,
            notification_type='group_mention', group=group,
        )
        send_push_notification(
            user=user,
            title=f'{group.name}',
            body=f'@{actor.username} mentioned you',
            url=f'/tweetapp/groups/{group.pk}/',
        )


def _group_msg_to_json(msg):
    """Serialize a GroupMessage to JSON dict."""
    reply_data = None
    if msg.reply_to:
        if msg.reply_to.is_deleted:
            reply_data = {'id': msg.reply_to.pk, 'content': 'This message was deleted', 'sender_username': msg.reply_to.user.username}
        else:
            reply_data = {'id': msg.reply_to.pk, 'content': msg.reply_to.message[:80], 'sender_username': msg.reply_to.user.username}
    sender_image = None
    if hasattr(msg.user, 'profile') and msg.user.profile.profile_image:
        sender_image = msg.user.profile.profile_image.url
    return {
        'id': msg.pk,
        'content': msg.message if not msg.is_deleted else '',
        'content_html': linkify_mentions_html(msg.message) if not msg.is_deleted else '',
        'image_url': msg.image.url if msg.image and not msg.is_deleted else None,
        'created_at': msg.created_at.strftime("%H:%M"),
        'sender_id': msg.user.pk,
        'sender_username': msg.user.username,
        'sender_image': sender_image,
        'is_deleted': msg.is_deleted,
        'reply_to': reply_data,
    }


@login_required(login_url='/login/')
@rate_limit('group_msg', limit=30, window=60)
def group_api_send_message(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    group = get_object_or_404(models.Group, pk=pk)
    if not group.memberships.filter(user=request.user).exists():
        return JsonResponse({'error': 'Not a member'}, status=403)
    message = request.POST.get('message', '').strip()
    image = request.FILES.get('image')
    reply_to_id = request.POST.get('reply_to')
    if not message and not image:
        return JsonResponse({'error': 'Empty message'}, status=400)
    if image:
        try:
            validate_image(image)
        except ValidationError as e:
            return JsonResponse({'error': e.messages[0] if e.messages else 'Invalid image'}, status=400)
    reply_to = None
    if reply_to_id:
        try:
            reply_to = models.GroupMessage.objects.get(pk=int(reply_to_id), group=group)
        except (models.GroupMessage.DoesNotExist, ValueError):
            pass
    msg = models.GroupMessage.objects.create(
        group=group, user=request.user,
        message=message, image=image, reply_to=reply_to
    )
    process_group_mentions(message, request.user, group, msg)
    notify_group_members(group, request.user, message, msg)
    data = _group_msg_to_json(msg)
    data['success'] = True
    return JsonResponse(data)


@login_required(login_url='/login/')
def group_api_poll_messages(request, pk):
    from django.core.cache import cache
    group = get_object_or_404(models.Group, pk=pk)
    if not group.memberships.filter(user=request.user).exists():
        return JsonResponse({'error': 'Not a member'}, status=403)
    last_id = int(request.GET.get('last_id', 0))
    new_msgs = group.messages.filter(id__gt=last_id).select_related('user__profile', 'reply_to__user')
    # Also return recently deleted messages the client might have
    deleted_ids = list(group.messages.filter(id__lte=last_id, is_deleted=True).values_list('id', flat=True)[:50])
    results = [_group_msg_to_json(m) for m in new_msgs]

    # Typing indicator: collect usernames of other members currently typing
    member_ids = list(
        group.memberships.exclude(user=request.user).values_list('user_id', flat=True)
    )
    typing_users = []
    for mid in member_ids:
        uname = cache.get(f'gtyping:{pk}:{mid}')
        if uname:
            typing_users.append(uname)

    return JsonResponse({'messages': results, 'deleted_ids': deleted_ids, 'typing_users': typing_users})


@login_required(login_url='/login/')
@rate_limit('group_typing', limit=120, window=60)
def group_api_set_typing(request, pk):
    """Mark current user as typing in this group for ~5 seconds."""
    from django.core.cache import cache
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    group = get_object_or_404(models.Group, pk=pk)
    if not group.memberships.filter(user=request.user).exists():
        return JsonResponse({'error': 'Not a member'}, status=403)
    cache.set(f'gtyping:{pk}:{request.user.pk}', request.user.username, timeout=5)
    return JsonResponse({'success': True})


@login_required(login_url='/login/')
def group_api_delete_message(request, pk, msg_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    group = get_object_or_404(models.Group, pk=pk)
    if not group.memberships.filter(user=request.user).exists():
        return JsonResponse({'error': 'Not a member'}, status=403)
    msg = get_object_or_404(models.GroupMessage, pk=msg_id, group=group)
    if msg.user != request.user:
        return JsonResponse({'error': 'Not your message'}, status=403)
    msg.is_deleted = True
    msg.message = ''
    if msg.image:
        msg.image.delete(save=False)
        msg.image = None
    msg.save()
    return JsonResponse({'success': True, 'id': msg.pk})


@login_required(login_url='/login/')
def group_promote_member(request, pk, user_id):
    if request.method != 'POST':
        return redirect('tweetapp:group_detail', pk=pk)
    group = get_object_or_404(models.Group, pk=pk)
    if not group.memberships.filter(user=request.user, role='admin').exists():
        return redirect('tweetapp:group_detail', pk=pk)
    target = group.memberships.filter(user_id=user_id).first()
    if not target or target.user == request.user:
        return redirect('tweetapp:group_detail', pk=pk)
    target.role = 'admin' if target.role == 'member' else 'member'
    target.save()
    return redirect('tweetapp:group_detail', pk=pk)


@login_required(login_url='/login/')
def group_edit(request, pk):
    group = get_object_or_404(models.Group, pk=pk)
    if not group.memberships.filter(user=request.user, role='admin').exists():
        return redirect('tweetapp:group_detail', pk=pk)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if name:
            group.name = name
        group.description = request.POST.get('description', '')
        image = request.FILES.get('image')
        if image:
            try:
                validate_image(image)
            except ValidationError as e:
                messages.error(request, e.messages[0] if e.messages else 'Invalid image')
                return redirect('tweetapp:group_detail', pk=pk)
            group.image = image
        group.save()
    return redirect('tweetapp:group_detail', pk=pk)


@login_required(login_url='/login/')
def group_toggle_mute(request, pk):
    group = get_object_or_404(models.Group, pk=pk)
    membership = group.memberships.filter(user=request.user).first()
    if membership:
        membership.is_muted = not membership.is_muted
        membership.save()
    return redirect('tweetapp:group_detail', pk=pk)


@login_required(login_url='/login/')
@rate_limit('follow', limit=30, window=60)
def follow_user(request, username):
    target = get_object_or_404(User, username=username)
    if target == request.user:
        return redirect('tweetapp:profile', username=username)
        
    # Check if already following
    is_following = models.Follow.objects.filter(follower=request.user, following=target).exists()
    
    if is_following:
        # Unfollow
        models.Follow.objects.filter(follower=request.user, following=target).delete()
    else:
        # Not following. Check for profile setting
        if hasattr(target, 'profile') and target.profile.require_follow_requests:
            # Check if request already sent
            request_exists = models.FollowRequest.objects.filter(sender=request.user, receiver=target).exists()
            if request_exists:
                # Cancel request
                models.FollowRequest.objects.filter(sender=request.user, receiver=target).delete()
            else:
                # Send request
                req = models.FollowRequest.objects.create(sender=request.user, receiver=target)
                if should_notify(target, 'follow_request'):
                    models.Notification.objects.create(
                        recipient=target, actor=request.user,
                        notification_type='follow_request',
                        follow_request=req
                    )
                    send_push_notification(
                        user=target,
                        title='Tweety',
                        body=f'@{request.user.username} sent you a follow request',
                        url='/tweetapp/notifications/'
                    )
                messages.success(request, f"Follow request sent to {target.username}")
        else:
            # Direct follow
            models.Follow.objects.create(follower=request.user, following=target)
            if should_notify(target, 'follow'):
                models.Notification.objects.create(
                    recipient=target, actor=request.user,
                    notification_type='follow'
                )
                send_push_notification(
                    user=target,
                    title='Tweety',
                    body=f'@{request.user.username} started following you',
                    url=f'/tweetapp/profile/{request.user.username}/'
                )
            
    return redirect('tweetapp:profile', username=username)


@login_required(login_url='/login/')
def accept_follow_request(request, pk):
    if request.method != "POST":
        return redirect('tweetapp:notifications')
    follow_req = get_object_or_404(models.FollowRequest, pk=pk, receiver=request.user)
    
    models.Follow.objects.create(follower=follow_req.sender, following=request.user)
    
    if should_notify(follow_req.sender, 'follow_accept'):
        models.Notification.objects.create(
            recipient=follow_req.sender, actor=request.user,
            notification_type='follow_accept'
        )
        send_push_notification(
            user=follow_req.sender,
            title='Tweety',
            body=f'@{request.user.username} accepted your follow request',
            url=f'/tweetapp/profile/{request.user.username}/'
        )

    follow_req.delete()
    return redirect('tweetapp:notifications')


@login_required(login_url='/login/')
def decline_follow_request(request, pk):
    if request.method != "POST":
        return redirect('tweetapp:notifications')
    follow_req = get_object_or_404(models.FollowRequest, pk=pk, receiver=request.user)
    follow_req.delete()
    return redirect('tweetapp:notifications')


@login_required(login_url='/login/')
def followers_following(request, username):
    user = get_object_or_404(User, username=username)
    
    if request.user != user and not request.user.is_staff:
        messages.error(request, "You don't have permission to view this page.")
        return redirect('tweetapp:profile', username=username)
    
    followers = models.Follow.objects.filter(following=user).select_related('follower', 'follower__profile')
    following = models.Follow.objects.filter(follower=user).select_related('following', 'following__profile')
    
    context = {
        'profile_user': user,
        'followers': followers,
        'following': following,
        'followers_count': followers.count(),
        'following_count': following.count(),
    }
    
    return render(request, 'tweetapp/followers_following.html', context)


@login_required(login_url='/login/')
def toggle_visibility(request, pk):
    if request.method != "POST":
        return redirect(reverse('tweetapp:listtweet'))
    tweet = get_object_or_404(models.Tweet, pk=pk)
    if request.user == tweet.user:
        if tweet.visibility == 'public':
            tweet.visibility = 'followers'
        else:
            tweet.visibility = 'public'
        tweet.save()
    return redirect(request.META.get('HTTP_REFERER', reverse('tweetapp:listtweet')))


@login_required(login_url='/login/')
def notifications_view(request):
    notifs = models.Notification.objects.filter(recipient=request.user).select_related('actor', 'tweet').order_by('-created_at')
    notifs.filter(is_read=False).update(is_read=True)
    
    liked_ids = list(models.Like.objects.filter(user=request.user).values_list('tweet_id', flat=True))
    
    context = {
        'notifications': notifs,
        'liked_ids': liked_ids,
    }
    return render(request, 'tweetapp/notifications.html', context)


@login_required(login_url='/login/')
def notification_settings(request):
    prefs, _ = models.NotificationPreference.objects.get_or_create(user=request.user)
    PREF_FIELDS = [
        ('like', 'Likes', 'heart', 'When someone likes your tweet'),
        ('comment', 'Comments', 'message-circle', 'When someone comments on your tweet'),
        ('thread', 'Thread Replies', 'messages-square', 'When someone replies to a thread you commented on'),
        ('follow', 'New Followers', 'user-check', 'When someone follows you'),
        ('follow_request', 'Follow Requests', 'user-plus', 'When someone requests to follow you'),
        ('follow_accept', 'Follow Accepted', 'user-check', 'When your follow request is accepted'),
        ('group_invite', 'Group Invites', 'users', 'When you are invited to a group'),
        ('group_join_request', 'Join Requests', 'user-plus', 'When someone requests to join your group'),
        ('group_mention', 'Group Mentions', 'at-sign', 'When someone mentions you in a group message'),
        ('message', 'Direct Messages', 'mail', 'When you receive a direct message'),
        ('mention', 'Mentions', 'at-sign', 'When someone mentions you with @username'),
    ]
    if request.method == 'POST':
        for field, _, _, _ in PREF_FIELDS:
            setattr(prefs, field, field in request.POST)
        prefs.save()
        messages.success(request, 'Notification preferences saved.')
        return redirect('tweetapp:notification_settings')
    context = {
        'prefs': prefs,
        'pref_fields': [(f, label, icon, desc, getattr(prefs, f)) for f, label, icon, desc in PREF_FIELDS],
    }
    return render(request, 'tweetapp/notification_settings.html', context)


@login_required(login_url='/login/')
def api_unread_counts(request):
    notif_count = models.Notification.objects.filter(recipient=request.user, is_read=False).count()
    msg_count = models.Message.objects.filter(
        thread__participants=request.user, is_read=False
    ).exclude(sender=request.user).count()
    return JsonResponse({'notif_count': notif_count, 'msg_count': msg_count})


@login_required(login_url='/login/')
def api_set_theme_preference(request):
    """Persist theme preference for the authenticated user."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    theme = data.get('theme')
    if theme not in ('dark', 'light'):
        return JsonResponse({'error': 'Invalid theme'}, status=400)

    profile, _ = models.Profile.objects.get_or_create(user=request.user)
    profile.theme_preference = theme
    profile.save(update_fields=['theme_preference'])
    return JsonResponse({'success': True, 'theme': theme})


def tweet_detail(request, pk):
    from django.http import Http404
    
    tweet = get_object_or_404(
        models.Tweet.objects.select_related('user', 'user__profile').prefetch_related(
            'images',
            'comments__user__profile',
            'comments__parent__user',
            'comments__replies',
        ),
        pk=pk
    )

    # Security: Prevent viewing followers-only tweets by direct link if not authorized
    if tweet.visibility == 'followers' and request.user != tweet.user and not request.user.is_staff:
        if not request.user.is_authenticated:
            raise Http404()
        if not models.Follow.objects.filter(follower=request.user, following=tweet.user).exists():
            raise Http404()

    if request.user.is_authenticated:
        liked_ids = list(models.Like.objects.filter(user=request.user).values_list('tweet_id', flat=True))
    else:
        liked_ids = []

    # Build threaded comments: top-level + replies map
    all_comments = list(
        tweet.comments.select_related('user__profile', 'parent__user').order_by('created_at')
    )
    top_comments = [c for c in all_comments if c.parent is None]
    replies_map = {}
    for c in all_comments:
        if c.parent_id:
            replies_map.setdefault(c.parent_id, []).append(c)

    context = {
        'tweet': tweet,
        'liked_ids': liked_ids,
        'top_comments': top_comments,
        'replies_map': replies_map,
    }
    return render(request, 'tweetapp/tweet_detail.html', context)


@login_required(login_url='/login/')
def tweet_likers(request, pk):
    from django.http import Http404
    
    tweet = get_object_or_404(models.Tweet, pk=pk)
    
    # Check visibility before allowing them to see who liked it
    if tweet.visibility == 'followers' and request.user != tweet.user and not request.user.is_staff:
        if not models.Follow.objects.filter(follower=request.user, following=tweet.user).exists():
            raise Http404()
            
    likes_qs = models.Like.objects.filter(tweet=tweet).select_related('user', 'user__profile').order_by('-created_at')
    
    query = request.GET.get('q', '')
    if query:
        likes_qs = likes_qs.filter(
            Q(user__username__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query)
        )
        
    context = {
        'tweet': tweet,
        'likers': likes_qs,
        'search_query': query,
    }
    return render(request, 'tweetapp/tweet_likers.html', context)

# --- DIRECT MESSAGING ---

def _build_chat_list(request_user):
    """Build the inbox chat list with last_message + unread_count in 2 queries
    instead of N (one per thread). Returns (chat_list, chat_user_ids)."""
    # Annotate each thread with the id of its most-recent message and the
    # unread count for the current user.
    last_msg_id_sq = models.Message.objects.filter(thread=OuterRef('pk')).order_by('-created_at').values('pk')[:1]
    threads = (
        request_user.chat_threads
        .annotate(
            _last_message_id=Subquery(last_msg_id_sq),
            _unread_count=Count(
                'messages',
                filter=Q(messages__is_read=False) & ~Q(messages__sender=request_user),
            ),
        )
        .prefetch_related('participants', 'participants__profile')
        .order_by('-updated_at')
    )
    threads = list(threads)

    # Bulk-fetch the actual last messages in one query.
    last_msg_ids = [t._last_message_id for t in threads if t._last_message_id]
    last_msgs = {
        m.pk: m for m in models.Message.objects.filter(pk__in=last_msg_ids).select_related('sender')
    }

    chat_list = []
    chat_user_ids = []
    for t in threads:
        other_user = next((p for p in t.participants.all() if p.pk != request_user.pk), None)
        if other_user:
            chat_user_ids.append(other_user.pk)
        chat_list.append({
            'thread': t,
            'other_user': other_user,
            'last_message': last_msgs.get(t._last_message_id),
            'unread_count': t._unread_count,
        })
    return chat_list, chat_user_ids


@login_required
def inbox(request):
    """List all chat threads for the logged in user."""
    chat_list, chat_user_ids = _build_chat_list(request.user)

    # Override online_users to only people I follow or have chatted with
    following_ids = list(models.Follow.objects.filter(follower=request.user).values_list('following_id', flat=True))
    relevant_ids = set(following_ids + chat_user_ids)
    if relevant_ids:
        five_minutes_ago = timezone.now() - datetime.timedelta(minutes=5)
        online_users = User.objects.filter(
            pk__in=relevant_ids,
            profile__last_active__gte=five_minutes_ago
        ).exclude(pk=request.user.pk).select_related('profile')[:15]
    else:
        online_users = User.objects.none()
    context = {
        'online_users': online_users,
        'chat_list': chat_list,
        'active_thread_id': None,
    }
    return render(request, 'tweetapp/inbox.html', context)

@login_required
def start_chat(request, username):
    """Start or open a chat with a specific user."""
    if request.user.username == username:
        messages.warning(request, "You cannot message yourself.")
        return redirect('tweetapp:profile', username=username)
        
    target_user = get_object_or_404(User, username=username)
    
    # Check if a 1:1 thread exists
    thread = models.ChatThread.objects.filter(participants=request.user).filter(participants=target_user).first()
    
    if not thread:
        thread = models.ChatThread.objects.create()
        thread.participants.add(request.user, target_user)
        
    return redirect('tweetapp:chat_detail', thread_id=thread.pk)

@login_required
def chat_detail(request, thread_id):
    """View a single chat thread."""
    thread = get_object_or_404(models.ChatThread, pk=thread_id)
    if request.user not in thread.participants.all():
        return redirect('tweetapp:inbox')
        
    thread.messages.exclude(sender=request.user).filter(is_read=False).update(is_read=True)

    chat_list, chat_user_ids = _build_chat_list(request.user)
    other_user = next(
        (entry['other_user'] for entry in chat_list if entry['thread'].pk == thread.pk),
        None,
    )
        
    msgs = thread.messages.select_related('sender').order_by('created_at')
    
    following_ids = list(models.Follow.objects.filter(follower=request.user).values_list('following_id', flat=True))
    relevant_ids = set(following_ids + chat_user_ids)
    if relevant_ids:
        five_minutes_ago = timezone.now() - datetime.timedelta(minutes=5)
        online_users = User.objects.filter(
            pk__in=relevant_ids,
            profile__last_active__gte=five_minutes_ago
        ).exclude(pk=request.user.pk).select_related('profile')[:15]
    else:
        online_users = User.objects.none()
    context = {
        'online_users': online_users,
        'chat_list': chat_list,
        'active_thread': thread,
        'active_thread_id': thread.pk,
        'other_user': other_user,
        'chat_messages': msgs,
    }
    return render(request, 'tweetapp/inbox.html', context)

@login_required
def delete_chat(request, thread_id):
    """Delete a chat thread."""
    if request.method != 'POST':
        return redirect('tweetapp:inbox')
    thread = get_object_or_404(models.ChatThread, pk=thread_id)
    if request.user not in thread.participants.all():
        return redirect('tweetapp:inbox')
    thread.messages.all().delete()
    thread.delete()
    return redirect('tweetapp:inbox')

@login_required
@rate_limit('dm_send', limit=30, window=60)
def api_send_message(request, thread_id):
    """Send a message via AJAX."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
        
    thread = get_object_or_404(models.ChatThread, pk=thread_id)
    if request.user not in thread.participants.all():
        return JsonResponse({'error': 'Unauthorized'}, status=403)
        
    content = request.POST.get('content', '').strip()
    image = request.FILES.get('image')
    reply_to_id = request.POST.get('reply_to')

    if not content and not image:
        return JsonResponse({'error': 'Empty message'}, status=400)

    if image:
        try:
            validate_image(image)
        except ValidationError as e:
            return JsonResponse({'error': e.messages[0] if e.messages else 'Invalid image'}, status=400)

    reply_to = None
    if reply_to_id:
        try:
            reply_to = models.Message.objects.get(pk=int(reply_to_id), thread=thread)
        except (models.Message.DoesNotExist, ValueError):
            pass

    msg = models.Message.objects.create(
        thread=thread,
        sender=request.user,
        content=content,
        image=image,
        reply_to=reply_to
    )
    
    thread.updated_at = timezone.now()
    thread.save()
    
    other_user = thread.participants.exclude(pk=request.user.pk).first()
    if other_user and should_notify(other_user, 'message'):
        push_body = content[:100] if content else 'Sent you an image'
        send_push_notification(
            user=other_user,
            title=f'@{request.user.username}',
            body=push_body,
            url=f'/tweetapp/chat/{thread.pk}/'
        )
        
    process_mentions(msg.content, request.user, message_obj=msg)
        
    reply_data = None
    if msg.reply_to and not msg.reply_to.is_deleted:
        reply_data = {
            'id': msg.reply_to.pk,
            'content': msg.reply_to.content[:80] if msg.reply_to.content else '',
            'sender_username': msg.reply_to.sender.username,
        }

    return JsonResponse({
        'success': True,
        'id': msg.pk,
        'content': msg.content,
        'image_url': msg.image.url if msg.image else None,
        'created_at': msg.created_at.strftime("%I:%M %p"),
        'sender_id': msg.sender.pk,
        'is_read': False,
        'is_deleted': False,
        'reply_to': reply_data,
    })

@login_required
def api_poll_messages(request, thread_id):
    """Poll for new messages."""
    from django.core.cache import cache
    thread = get_object_or_404(models.ChatThread, pk=thread_id)
    if request.user not in thread.participants.all():
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    last_id = request.GET.get('last_id', 0)
    try:
        last_id = int(last_id)
    except ValueError:
        last_id = 0

    # Typing indicator: did any other participant set a typing flag in cache
    # within the last 5 seconds?
    other_typing = False
    other_ids = list(thread.participants.exclude(pk=request.user.pk).values_list('pk', flat=True))
    for oid in other_ids:
        cache_key = f'typing:{thread_id}:{oid}'
        val = cache.get(cache_key)
        if val:
            other_typing = True
            break

    new_messages = thread.messages.filter(id__gt=last_id).order_by('created_at')
    new_messages.exclude(sender=request.user).filter(is_read=False).update(is_read=True)
    
    results = []
    for m in new_messages:
        reply_data = None
        if m.reply_to and not m.reply_to.is_deleted:
            reply_data = {
                'id': m.reply_to.pk,
                'content': m.reply_to.content[:80] if m.reply_to.content else '',
                'sender_username': m.reply_to.sender.username,
            }
        results.append({
            'id': m.pk,
            'content': m.content if not m.is_deleted else '',
            'image_url': m.image.url if m.image and not m.is_deleted else None,
            'created_at': m.created_at.strftime("%I:%M %p"),
            'sender_id': m.sender.pk,
            'sender_username': m.sender.username,
            'sender_image': m.sender.profile.profile_image.url if m.sender.profile.profile_image else None,
            'is_read': m.is_read,
            'is_deleted': m.is_deleted,
            'reply_to': reply_data,
        })
        
    # Return read status of my messages that were read by other user
    read_ids = list(
        thread.messages.filter(sender=request.user, is_read=True)
            .values_list('pk', flat=True)
    )

    return JsonResponse({'messages': results, 'read_ids': read_ids, 'typing': other_typing})


@login_required
@rate_limit('typing', limit=120, window=60)
def api_set_typing(request, thread_id):
    """Mark current user as typing in this thread for ~5 seconds."""
    from django.core.cache import cache
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    thread = get_object_or_404(models.ChatThread, pk=thread_id)
    if request.user not in thread.participants.all():
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    cache.set(f'typing:{thread_id}:{request.user.pk}', 1, timeout=5)
    return JsonResponse({'success': True})


@login_required
def api_delete_message(request, thread_id, msg_id):
    """Soft-delete a message."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    thread = get_object_or_404(models.ChatThread, pk=thread_id)
    if request.user not in thread.participants.all():
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    msg = get_object_or_404(models.Message, pk=msg_id, thread=thread)
    if msg.sender != request.user:
        return JsonResponse({'error': 'Not your message'}, status=403)
    msg.is_deleted = True
    msg.content = ''
    if msg.image:
        msg.image.delete(save=False)
        msg.image = None
    msg.save()
    return JsonResponse({'success': True, 'id': msg.pk})


@login_required
def update_chat_theme(request, thread_id):
    """Update background or theme color."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
        
    thread = get_object_or_404(models.ChatThread, pk=thread_id)
    if request.user not in thread.participants.all():
        return JsonResponse({'error': 'Unauthorized'}, status=403)
        
    theme_color = request.POST.get('theme_color')
    if theme_color:
        thread.theme_color = theme_color
        
    bg_image = request.FILES.get('background_image')
    if bg_image:
        try:
            validate_image(bg_image)
        except ValidationError as e:
            return JsonResponse({'error': e.messages[0] if e.messages else 'Invalid image'}, status=400)
        thread.background_image = bg_image
        
    if request.POST.get('clear_background') == 'true':
        thread.background_image = None
        
    thread.save()
    
    # redirect back to chat
    return redirect('tweetapp:chat_detail', thread_id=thread.pk)


@login_required
def api_mention_autocomplete(request):
    """Return top 5 user matches for a mention query."""
    q = request.GET.get('q', '').strip()
    if not q:
        return JsonResponse({'users': []})
        
    users = User.objects.filter(
        Q(username__icontains=q) |
        Q(profile__first_name__icontains=q) |
        Q(profile__last_name__icontains=q)
    ).select_related('profile').distinct()[:5]
    
    results = []
    for u in users:
        results.append({
            'username': u.username,
            'full_name': f"{u.profile.first_name} {u.profile.last_name}".strip() if u.profile.first_name or u.profile.last_name else u.username,
            'avatar_url': u.profile.profile_image.url if u.profile.profile_image else None
        })
        
    return JsonResponse({'users': results})


# ─── Web Push Notifications ───────────────────────────────────────

def send_push_notification(user, title, body, url='/tweetapp/chat/'):
    """Send push notification to all subscriptions of a user."""
    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        logger.warning("pywebpush not installed, skipping push notification")
        return

    subscriptions = models.PushSubscription.objects.filter(user=user)
    if not subscriptions.exists():
        return

    payload = json.dumps({
        'title': title,
        'body': body,
        'url': url,
    })

    vapid_private_key = getattr(settings, 'VAPID_PRIVATE_KEY', '')
    vapid_claims = {'sub': getattr(settings, 'VAPID_ADMIN_EMAIL', 'mailto:admin@tweety.com')}

    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    'endpoint': sub.endpoint,
                    'keys': {
                        'p256dh': sub.p256dh,
                        'auth': sub.auth,
                    }
                },
                data=payload,
                vapid_private_key=vapid_private_key,
                vapid_claims=vapid_claims,
            )
        except Exception as e:
            logger.warning(f"Push failed for {user.username}: {e}")
            # If subscription is expired/invalid, remove it
            if '410' in str(e) or '404' in str(e):
                sub.delete()


@login_required
@rate_limit('push_sub', limit=10, window=60)
def push_subscribe(request):
    """Save a push subscription for the current user."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    endpoint = data.get('endpoint')
    keys = data.get('keys', {})
    p256dh = keys.get('p256dh')
    auth = keys.get('auth')

    if not endpoint or not p256dh or not auth:
        return JsonResponse({'error': 'Missing subscription data'}, status=400)

    models.PushSubscription.objects.update_or_create(
        user=request.user,
        endpoint=endpoint,
        defaults={'p256dh': p256dh, 'auth': auth}
    )

    return JsonResponse({'success': True})


@login_required
def push_unsubscribe(request):
    """Remove a push subscription."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    endpoint = data.get('endpoint')
    if endpoint:
        models.PushSubscription.objects.filter(user=request.user, endpoint=endpoint).delete()

    return JsonResponse({'success': True})


def vapid_public_key(request):
    """Return the VAPID public key for the frontend."""
    return JsonResponse({'public_key': getattr(settings, 'VAPID_PUBLIC_KEY', '')})


# ─── Games ───────────────────────────────────────────────────────────────────

@login_required(login_url='/login/')
def games_view(request):
    """Render the Flappy Tweet game page with sidebar context."""
    user = request.user
    # User's all-time best score
    best_score_obj = models.GameScore.objects.filter(
        user=user, game='flappy_tweet'
    ).order_by('-score').first()
    best_score = best_score_obj.score if best_score_obj else 0

    # Today's best score (local timezone day)
    today_local = timezone.localdate()
    daily_best_obj = models.GameScore.objects.filter(
        user=user, game='flappy_tweet', created_at__date=today_local
    ).order_by('-score').first()
    daily_best = daily_best_obj.score if daily_best_obj else 0

    # Top 5 all-time leaderboard for sidebar
    from django.db.models import Max
    top5 = (
        models.GameScore.objects
        .filter(game='flappy_tweet')
        .values('user__username', 'user__id')
        .annotate(top_score=Max('score'))
        .order_by('-top_score')[:5]
    )

    # Enrich with profile images (bulk fetch — no N+1)
    top5_user_ids = [e['user__id'] for e in top5]
    top5_profile_images = {
        p.user_id: (p.profile_image.url if p.profile_image else None)
        for p in models.Profile.objects.filter(user_id__in=top5_user_ids)
    }
    top5_list = [
        {
            'username': entry['user__username'],
            'score': entry['top_score'],
            'profile_image': top5_profile_images.get(entry['user__id']),
        }
        for entry in top5
    ]

    # Recent notifications (last 5 unread)
    recent_notifs = models.Notification.objects.filter(
        recipient=user, is_read=False
    ).select_related('actor')[:5]

    # Unread message count + last message
    unread_threads = models.Message.objects.filter(
        thread__participants=user, is_read=False
    ).exclude(sender=user).select_related('sender', 'thread')
    unread_msg_count = unread_threads.count()
    last_message = unread_threads.order_by('-created_at').first()

    # Online users
    five_minutes_ago = timezone.now() - datetime.timedelta(minutes=5)
    online_users = User.objects.filter(
        profile__last_active__gte=five_minutes_ago
    ).select_related('profile')[:10]

    # Recent group activity
    user_groups = models.Group.objects.filter(memberships__user=user)
    recent_group_msgs = models.GroupMessage.objects.filter(
        group__in=user_groups
    ).exclude(user=user).select_related('user', 'group').order_by('-created_at')[:5]

    # Game Settings
    game_settings, _ = models.GameSettings.objects.get_or_create(user=user)

    context = {
        'best_score': best_score,
        'daily_best': daily_best,
        'top5': top5_list,
        'recent_notifs': recent_notifs,
        'unread_msg_count': unread_msg_count,
        'last_message': last_message,
        'online_users': online_users,
        'recent_group_msgs': recent_group_msgs,
        'game_settings': {
            'bgImages': json.loads(game_settings.bg_images),
            'bgSelected': game_settings.bg_selected,
            'pipeImages': json.loads(game_settings.pipe_images),
            'pipeSelected': game_settings.pipe_selected,
            'birdImages': json.loads(game_settings.bird_images),
            'birdSelected': game_settings.bird_selected,
            'accent': game_settings.accent_color,
        }
    }
    return render(request, 'tweetapp/games.html', context)


@login_required(login_url='/login/')
def api_submit_score(request):
    """Save a game score via AJAX POST."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    score = data.get('score')
    if score is None or not isinstance(score, int) or score < 0:
        return JsonResponse({'error': 'Invalid score'}, status=400)

    models.GameScore.objects.create(
        user=request.user,
        game='flappy_tweet',
        score=score,
    )

    # Return updated best scores
    from django.db.models import Max
    best = models.GameScore.objects.filter(
        user=request.user, game='flappy_tweet'
    ).aggregate(best=Max('score'))['best'] or 0

    today_local = timezone.localdate()
    daily_best = models.GameScore.objects.filter(
        user=request.user, game='flappy_tweet', created_at__date=today_local
    ).aggregate(best=Max('score'))['best'] or 0

    return JsonResponse({
        'success': True,
        'best_score': best,
        'daily_best': daily_best,
    })


@login_required(login_url='/login/')
def leaderboard_view(request):
    """Render the leaderboard page with daily + all-time tabs."""
    from django.db.models import Max
    tab = request.GET.get('tab', 'alltime')

    if tab == 'daily':
        today_local = timezone.localdate()
        entries = (
            models.GameScore.objects
            .filter(game='flappy_tweet', created_at__date=today_local)
            .values('user__username', 'user__id')
            .annotate(top_score=Max('score'))
            .order_by('-top_score')[:50]
        )
    else:
        entries = (
            models.GameScore.objects
            .filter(game='flappy_tweet')
            .values('user__username', 'user__id')
            .annotate(top_score=Max('score'))
            .order_by('-top_score')[:50]
        )

    user_ids = [e['user__id'] for e in entries]
    profile_images = {
        p.user_id: (p.profile_image.url if p.profile_image else None)
        for p in models.Profile.objects.filter(user_id__in=user_ids)
    }
    leaderboard = []
    for i, entry in enumerate(entries, 1):
        leaderboard.append({
            'rank': i,
            'username': entry['user__username'],
            'user_id': entry['user__id'],
            'score': entry['top_score'],
            'profile_image': profile_images.get(entry['user__id']),
        })

    # Current user's rank
    my_rank = None
    my_score = None
    for entry in leaderboard:
        if entry['user_id'] == request.user.id:
            my_rank = entry['rank']
            my_score = entry['score']
            break

    if my_rank is None:
        # User not in top 50, find their rank
        if tab == 'daily':
            today_local = timezone.localdate()
            user_best = models.GameScore.objects.filter(
                user=request.user, game='flappy_tweet', created_at__date=today_local
            ).aggregate(best=Max('score'))['best']
        else:
            user_best = models.GameScore.objects.filter(
                user=request.user, game='flappy_tweet'
            ).aggregate(best=Max('score'))['best']

        if user_best is not None:
            my_score = user_best
            if tab == 'daily':
                today_local = timezone.localdate()
                higher_count = (
                    models.GameScore.objects
                    .filter(game='flappy_tweet', created_at__date=today_local)
                    .values('user')
                    .annotate(top_score=Max('score'))
                    .filter(top_score__gt=user_best)
                    .count()
                )
            else:
                higher_count = (
                    models.GameScore.objects
                    .filter(game='flappy_tweet')
                    .values('user')
                    .annotate(top_score=Max('score'))
                    .filter(top_score__gt=user_best)
                    .count()
                )
            my_rank = higher_count + 1

    context = {
        'leaderboard': leaderboard,
        'active_tab': tab,
        'my_rank': my_rank,
        'my_score': my_score,
    }
    return render(request, 'tweetapp/leaderboard.html', context)

@login_required(login_url='/login/')
def api_save_game_settings(request):
    """Save game settings to the database via AJAX POST."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    settings_obj, _ = models.GameSettings.objects.get_or_create(user=request.user)
    
    # Update fields if provided
    if 'bgImages' in data:
        settings_obj.bg_images = json.dumps(data['bgImages'])
    if 'bgSelected' in data:
        settings_obj.bg_selected = data['bgSelected']
    if 'pipeImages' in data:
        settings_obj.pipe_images = json.dumps(data['pipeImages'])
    if 'pipeSelected' in data:
        settings_obj.pipe_selected = data['pipeSelected']
    if 'birdImages' in data:
        settings_obj.bird_images = json.dumps(data['birdImages'])
    if 'birdSelected' in data:
        settings_obj.bird_selected = data['birdSelected']
    if 'accent' in data:
        settings_obj.accent_color = data['accent']
        
    settings_obj.save()
    return JsonResponse({'success': True})


@login_required(login_url='/login/')
def api_get_game_settings(request):
    """Retrieve game settings for the current user."""
    settings_obj, _ = models.GameSettings.objects.get_or_create(user=request.user)
    return JsonResponse({
        'bgImages': json.loads(settings_obj.bg_images),
        'bgSelected': settings_obj.bg_selected,
        'pipeImages': json.loads(settings_obj.pipe_images),
        'pipeSelected': settings_obj.pipe_selected,
        'birdImages': json.loads(settings_obj.bird_images),
        'birdSelected': settings_obj.bird_selected,
        'accent': settings_obj.accent_color,
    })
