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
from django.db.models import Count
from django.utils import timezone
from django.core.paginator import Paginator
import datetime


def get_sidebar_context(request):
    if request.user.is_authenticated:
        following_ids = list(models.Follow.objects.filter(follower=request.user).values_list('following_id', flat=True))
        suggested_users = User.objects.exclude(
            pk__in=following_ids + [request.user.pk]
        ).select_related('profile').order_by('?')[:5]
        five_minutes_ago = timezone.now() - datetime.timedelta(minutes=5)
        online_users = User.objects.filter(
            profile__last_active__gte=five_minutes_ago
        ).select_related('profile')[:10]
    else:
        suggested_users = User.objects.select_related('profile').order_by('?')[:5]
        online_users = User.objects.none()
    return {
        'suggested_users': suggested_users,
        'online_users': online_users,
    }


def listtweet(request):
    if request.user.is_authenticated:
        liked_ids = list(models.Like.objects.filter(user=request.user).values_list('tweet_id', flat=True))
        following_ids = list(models.Follow.objects.filter(follower=request.user).values_list('following_id', flat=True))
        
        if request.user.is_staff:
            latest_tweets = models.Tweet.objects.all().order_by('-created_at')
            recommended_tweets = models.Tweet.objects.all().annotate(like_count=Count('likes')).order_by('-like_count', '-created_at')[:20]
        else:
            visible = models.Tweet.objects.filter(
                Q(visibility='public') |
                Q(user=request.user) |
                Q(user_id__in=following_ids, visibility='followers')
            )
            latest_tweets = visible.order_by('-created_at')
            recommended_tweets = visible.annotate(like_count=Count('likes')).order_by('-like_count', '-created_at')[:20]
        
        following_tweets = models.Tweet.objects.filter(
            user_id__in=following_ids
        ).filter(
            Q(visibility='public') |
            Q(visibility='followers')
        ).order_by('-created_at')
    else:
        latest_tweets = models.Tweet.objects.filter(visibility='public').order_by('-created_at')
        recommended_tweets = latest_tweets[:20]
        following_tweets = models.Tweet.objects.none()
        liked_ids = []

    tab = request.GET.get('tab', 'latest')

    paginator = Paginator(latest_tweets, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'latest_tweets': page_obj,
        'recommended_tweets': recommended_tweets,
        'following_tweets': following_tweets,
        'liked_ids': liked_ids,
        'active_tab': tab,
        'page_obj': page_obj,
    }
    context.update(get_sidebar_context(request))
    return render(request, 'tweetapp/listtweet.html', context)


@login_required(login_url='/login/')
def addtweetbyform(request):
    if request.method == "POST":
        form = AddTweetForm(request.POST, request.FILES)
        if form.is_valid():
            tweet = models.Tweet.objects.create(
                user=request.user,
                nickname=request.user.username,
                message=form.cleaned_data["message_input"],
                visibility=form.cleaned_data["visibility"]
            )
            for file in request.FILES.getlist('images'):
                models.TweetImage.objects.create(tweet=tweet, image=file)
            return redirect(reverse('tweetapp:listtweet'))
        else:
            return render(request, 'tweetapp/addtwetbyform.html', context={"form": form})
    else:
        form = AddTweetForm()
        return render(request, 'tweetapp/addtwetbyform.html', context={"form": form})


def searchtweet(request):
    query = request.GET.get('q', '')
    tab = request.GET.get('tab', 'latest')
    
    if query:
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
            
        results = results.order_by('-created_at')
        
        if tab == 'following' and request.user.is_authenticated:
            following_ids = list(models.Follow.objects.filter(follower=request.user).values_list('following_id', flat=True))
            latest_tweets = results.filter(user_id__in=following_ids)
            recommended_tweets = latest_tweets
            following_tweets = latest_tweets
        else:
            latest_tweets = results
            recommended_tweets = results
            following_tweets = results
    else:
        latest_tweets = models.Tweet.objects.none()
        recommended_tweets = models.Tweet.objects.none()
        following_tweets = models.Tweet.objects.none()
        
    if request.user.is_authenticated:
        liked_ids = list(models.Like.objects.filter(user=request.user).values_list('tweet_id', flat=True))
    else:
        liked_ids = []
    
    return render(request, 'tweetapp/listtweet.html', {
        'latest_tweets': latest_tweets,
        'recommended_tweets': recommended_tweets,
        'following_tweets': following_tweets,
        'liked_ids': liked_ids,
        'suggested_users': [],
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

    if request.user.is_authenticated:
        if request.user.is_staff or (user and request.user == user):
            tweets = models.Tweet.objects.filter(nickname__iexact=username).order_by('-created_at')
        else:
            i_follow_author = user and models.Follow.objects.filter(follower=request.user, following=user).exists()
            if i_follow_author:
                tweets = models.Tweet.objects.filter(nickname__iexact=username).order_by('-created_at')
            else:
                tweets = models.Tweet.objects.filter(nickname__iexact=username, visibility='public').order_by('-created_at')
    else:
        tweets = models.Tweet.objects.filter(nickname__iexact=username, visibility='public').order_by('-created_at')    
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
            return redirect('tweetapp:profile', username=request.user.username)
        else:
            return render(request, 'tweetapp/edit_profile.html', context={"form": form})
    else:
        profile = request.user.profile
        form = ProfileForm(initial={
            'first_name': profile.first_name,
            'last_name': profile.last_name,
            'age': profile.age,
            'bio': profile.bio,
            'require_follow_requests': profile.require_follow_requests,
        })
        return render(request, 'tweetapp/edit_profile.html', context={"form": form})


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
        return response


@login_required(login_url='/login/')
def delete_tweet(request, pk):
    if request.method != "POST":
        return redirect(reverse('tweetapp:listtweet'))
    tweet = get_object_or_404(models.Tweet, pk=pk)
    if request.user == tweet.user or request.user.is_staff:
        tweet.delete()
    return redirect(reverse('tweetapp:listtweet'))


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
        if request.user != tweet.user:
            models.Notification.objects.create(
                recipient=tweet.user, actor=request.user,
                notification_type='like', tweet=tweet
            )
    return JsonResponse({
        'liked': created,
        'count': tweet.likes.count()
    })


@login_required(login_url='/login/')
def add_comment(request, pk):
    from django.http import Http404
    if request.method != "POST":
        return redirect(reverse('tweetapp:listtweet'))
    message = request.POST.get('comment_message', '')
    if message:
        tweet = get_object_or_404(models.Tweet, pk=pk)
        
        # Security: Prevent unauthorized users from commenting on private tweets
        if tweet.visibility == 'followers' and request.user != tweet.user and not request.user.is_staff:
            if not models.Follow.objects.filter(follower=request.user, following=tweet.user).exists():
                raise Http404()
                
        models.Comment.objects.create(user=request.user, tweet=tweet, message=message)
        
        if request.user != tweet.user:
            models.Notification.objects.create(
                recipient=tweet.user, actor=request.user,
                notification_type='comment', tweet=tweet
            )
        
        other_commenters = User.objects.filter(
            comment__tweet=tweet
        ).exclude(id=request.user.id).exclude(id=tweet.user.id).distinct()
        
        for commenter in other_commenters:
            models.Notification.objects.create(
                recipient=commenter, actor=request.user,
                notification_type='thread', tweet=tweet
            )
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
        users = User.objects.select_related('profile').order_by('-profile__last_active')
    else:
        users = User.objects.select_related('profile').all()
    
    context = {'users': users}
    context.update(get_sidebar_context(request))
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
    members = group.memberships.select_related('user').all()
    messages_list = group.messages.select_related('user').all()
    join_requests = group.join_requests.select_related('user').all() if membership.role == 'admin' else []

    return render(request, 'tweetapp/group_detail.html', {
        'group': group,
        'membership': membership,
        'members': members,
        'messages_list': messages_list,
        'join_requests': join_requests,
    })


@login_required(login_url='/login/')
def group_send_message(request, pk):
    group = get_object_or_404(models.Group, pk=pk)
    if not group.memberships.filter(user=request.user).exists():
        return redirect('tweetapp:group_list')
    if request.method == "POST":
        message = request.POST.get('message', '')
        image = request.FILES.get('image')
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
    if membership and membership.role != 'admin':
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
        models.GroupJoinRequest.objects.get_or_create(group=group, user=request.user)
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


@login_required(login_url='/login/')
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
                models.Notification.objects.create(
                    recipient=target, actor=request.user,
                    notification_type='follow_request',
                    follow_request=req
                )
                messages.success(request, f"Follow request sent to {target.username}")
        else:
            # Direct follow
            models.Follow.objects.create(follower=request.user, following=target)
            models.Notification.objects.create(
                recipient=target, actor=request.user,
                notification_type='follow'
            )
            
    return redirect('tweetapp:profile', username=username)


@login_required(login_url='/login/')
def accept_follow_request(request, pk):
    if request.method != "POST":
        return redirect('tweetapp:notifications')
    follow_req = get_object_or_404(models.FollowRequest, pk=pk, receiver=request.user)
    
    models.Follow.objects.create(follower=follow_req.sender, following=request.user)
    
    models.Notification.objects.create(
        recipient=follow_req.sender, actor=request.user,
        notification_type='follow_accept'
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
    context.update(get_sidebar_context(request))
    return render(request, 'tweetapp/notifications.html', context)


def tweet_detail(request, pk):
    from django.http import Http404
    
    tweet = get_object_or_404(
        models.Tweet.objects.select_related('user', 'user__profile').prefetch_related('images', 'comments', 'comments__user'),
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
    
    context = {
        'tweet': tweet,
        'liked_ids': liked_ids,
    }
    context.update(get_sidebar_context(request))
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
    context.update(get_sidebar_context(request))
    return render(request, 'tweetapp/tweet_likers.html', context)