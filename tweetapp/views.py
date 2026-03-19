from django.shortcuts import render, redirect
from . import models
from django.urls import reverse, reverse_lazy
from tweetapp.forms import AddTweetForm, AddTweetModelForm
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from tweetapp.forms import AddTweetForm, AddTweetModelForm, ProfileForm
from django.contrib.auth.forms import UserCreationForm
from django.views.generic import CreateView
from tweetapp.forms import AddTweetForm, AddTweetModelForm, ProfileForm, RegisterForm
from django.contrib.auth.models import User
from django.http import JsonResponse


def listtweet(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            all_tweets = models.Tweet.objects.all().order_by('-created_at')
        else:
            authors_following_me = models.Follow.objects.filter(following=request.user).values_list('follower_id', flat=True)
            all_tweets = models.Tweet.objects.filter(
                Q(visibility='public') |
                Q(user=request.user) |
                Q(user_id__in=authors_following_me, visibility='followers')
            ).order_by('-created_at')
        liked_ids = models.Like.objects.filter(user=request.user).values_list('tweet_id', flat=True)
    else:
        all_tweets = models.Tweet.objects.filter(visibility='public').order_by('-created_at')
        liked_ids = []
    return render(request, 'tweetapp/listtweet.html', {"tweets": all_tweets, "liked_ids": liked_ids})


def addtweet(request):
    if request.POST:
        nickname = request.POST["nickname"]
        message = request.POST["message"]
        models.Tweet.objects.create(nickname=nickname, message=message)
        return redirect(reverse('tweetapp:listtweet'))
    else:
        return render(request, 'tweetapp/addtweet.html')


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


def addtweetbymodelform(request):
    if request.method == "POST":
        form = AddTweetModelForm(request.POST)
        if form.is_valid():
            nickname = form.cleaned_data["nickname"]
            message = form.cleaned_data["message"]
            models.Tweet.objects.create(nickname=nickname, message=message)
            return redirect(reverse('tweetapp:listtweet'))
        else:
            return render(request, 'tweetapp/addtweetbymodelform.html', context={"form": form})
    else:
        form = AddTweetModelForm()
        return render(request, 'tweetapp/addtweetbymodelform.html', context={"form": form})


def searchtweet(request):
    query = request.GET.get('q', '')
    if query:
        if query.startswith('@'):
            nickname = query[1:]
            results = models.Tweet.objects.filter(nickname__iexact=nickname).order_by('-created_at')
        else:
            results = models.Tweet.objects.filter(message__icontains=query).order_by('-created_at')
    else:
        results = models.Tweet.objects.none()
    if request.user.is_authenticated:
        liked_ids = models.Like.objects.filter(user=request.user).values_list('tweet_id', flat=True)
    else:
        liked_ids = []
    return render(request, 'tweetapp/listtweet.html', context={"tweets": results, "liked_ids": liked_ids})


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
            tweets = models.Tweet.objects.filter(nickname__iexact=username)
        else:
            author_follows_me = user and models.Follow.objects.filter(follower=user, following=request.user).exists()
            if author_follows_me:
                tweets = models.Tweet.objects.filter(nickname__iexact=username)
            else:
                tweets = models.Tweet.objects.filter(nickname__iexact=username, visibility='public')
    else:
        tweets = models.Tweet.objects.filter(nickname__iexact=username, visibility='public')    
    tweet_count = tweets.count()

    if request.user.is_authenticated:
        liked_ids = list(models.Like.objects.filter(user=request.user).values_list('tweet_id', flat=True))
    else:
        liked_ids = []

    user_comments = []
    is_following = False
    follower_count = 0
    following_count = 0
    if user:
        user_comments = models.Comment.objects.filter(user=user).select_related('tweet').order_by('-created_at')
        follower_count = models.Follow.objects.filter(following=user).count()
        following_count = models.Follow.objects.filter(follower=user).count()
        if request.user.is_authenticated and request.user != user:
            is_following = models.Follow.objects.filter(follower=request.user, following=user).exists()

    context = {
        'profile_user': user,
        'profile_exists': profile_exists,
        'tweets': tweets,
        'tweet_count': tweet_count,
        'searched_username': username,
        'liked_ids': liked_ids,
        'user_comments': user_comments,
        'is_following': is_following,
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


def delete_tweet(request, pk):
    tweet = models.Tweet.objects.get(pk=pk)
    is_moderator = request.user.groups.filter(name='moderator').exists()
    if request.user == tweet.user or is_moderator:
        tweet.delete()
    return redirect(reverse('tweetapp:listtweet'))


def like_tweet(request, pk):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'login'}, status=401)
    tweet = models.Tweet.objects.get(pk=pk)
    like, created = models.Like.objects.get_or_create(user=request.user, tweet=tweet)
    if not created:
        like.delete()
    return JsonResponse({
        'liked': created,
        'count': tweet.likes.count()
    })


def add_comment(request, pk):
    if not request.user.is_authenticated:
        return redirect('/login/')
    if request.method == "POST":
        message = request.POST.get('comment_message', '')
        if message:
            tweet = models.Tweet.objects.get(pk=pk)
            models.Comment.objects.create(user=request.user, tweet=tweet, message=message)
    return redirect(request.META.get('HTTP_REFERER', reverse('tweetapp:listtweet')))


def delete_comment(request, pk):
    comment = models.Comment.objects.get(pk=pk)
    if request.user == comment.user or request.user.is_staff:
        comment.delete()
    return redirect(request.META.get('HTTP_REFERER', reverse('tweetapp:listtweet')))


def userlist(request):
    users = User.objects.all()
    return render(request, 'tweetapp/userlist.html', {'users': users})


@login_required(login_url='/login/')
def edit_tweet(request, pk):
    tweet = models.Tweet.objects.get(pk=pk)
    if request.user != tweet.user or not tweet.can_edit():
        messages.warning(request, "Editing time expired! (5 min limit)")
        return redirect(reverse('tweetapp:listtweet'))
    if request.method == "POST":
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
    note = models.PatchNote.objects.get(pk=pk)
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
    group = models.Group.objects.get(pk=pk)
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
    group = models.Group.objects.get(pk=pk)
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
    group = models.Group.objects.get(pk=pk)
    if group.is_private:
        return redirect('tweetapp:group_list')
    if not group.memberships.filter(user=request.user).exists():
        models.GroupMembership.objects.create(group=group, user=request.user, role='member')
    return redirect('tweetapp:group_detail', pk=pk)


@login_required(login_url='/login/')
def group_leave(request, pk):
    group = models.Group.objects.get(pk=pk)
    membership = group.memberships.filter(user=request.user).first()
    if membership and membership.role != 'admin':
        membership.delete()
    return redirect('tweetapp:group_list')


@login_required(login_url='/login/')
def group_invite(request, pk):
    group = models.Group.objects.get(pk=pk)
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
        except User.DoesNotExist:
            messages.warning(request, "User not found!")
    return redirect('tweetapp:group_detail', pk=pk)


@login_required(login_url='/login/')
def group_accept_invite(request, pk):
    invite = models.GroupInvite.objects.get(pk=pk, invited_user=request.user)
    models.GroupMembership.objects.create(group=invite.group, user=request.user, role='member')
    invite.delete()
    return redirect('tweetapp:group_detail', pk=invite.group.pk)


@login_required(login_url='/login/')
def group_decline_invite(request, pk):
    invite = models.GroupInvite.objects.get(pk=pk, invited_user=request.user)
    invite.delete()
    return redirect('tweetapp:group_list')


@login_required(login_url='/login/')
def group_kick(request, pk, user_id):
    group = models.Group.objects.get(pk=pk)
    if not group.memberships.filter(user=request.user, role='admin').exists():
        return redirect('tweetapp:group_detail', pk=pk)
    membership = group.memberships.filter(user_id=user_id, role='member').first()
    if membership:
        membership.delete()
    return redirect('tweetapp:group_detail', pk=pk)


@login_required(login_url='/login/')
def group_delete(request, pk):
    group = models.Group.objects.get(pk=pk)
    if group.creator == request.user or request.user.is_staff:
        group.delete()
    return redirect('tweetapp:group_list')


@login_required(login_url='/login/')
def group_request_join(request, pk):
    group = models.Group.objects.get(pk=pk)
    if not group.memberships.filter(user=request.user).exists():
        models.GroupJoinRequest.objects.get_or_create(group=group, user=request.user)
    return redirect('tweetapp:group_list')


@login_required(login_url='/login/')
def group_accept_request(request, pk):
    join_request = models.GroupJoinRequest.objects.get(pk=pk)
    group = join_request.group
    if group.memberships.filter(user=request.user, role='admin').exists():
        models.GroupMembership.objects.create(group=group, user=join_request.user, role='member')
        join_request.delete()
    return redirect('tweetapp:group_detail', pk=group.pk)


@login_required(login_url='/login/')
def group_decline_request(request, pk):
    join_request = models.GroupJoinRequest.objects.get(pk=pk)
    group = join_request.group
    if group.memberships.filter(user=request.user, role='admin').exists():
        join_request.delete()
    return redirect('tweetapp:group_detail', pk=group.pk)


@login_required(login_url='/login/')
def follow_user(request, username):
    target = User.objects.get(username=username)
    if target != request.user:
        follow, created = models.Follow.objects.get_or_create(follower=request.user, following=target)
        if not created:
            follow.delete()
    return redirect('tweetapp:profile', username=username)


@login_required(login_url='/login/')
def toggle_visibility(request, pk):
    tweet = models.Tweet.objects.get(pk=pk)
    if request.user == tweet.user:
        if tweet.visibility == 'public':
            tweet.visibility = 'followers'
        else:
            tweet.visibility = 'public'
        tweet.save()
    return redirect(request.META.get('HTTP_REFERER', reverse('tweetapp:listtweet')))