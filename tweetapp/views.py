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




# Create your views here.

def listtweet(request):
    all_tweets = models.Tweet.objects.all()
    if request.user.is_authenticated:
        liked_ids = models.Like.objects.filter(user=request.user).values_list('tweet_id', flat=True)
    else:
        liked_ids = []
    tweet_dict = {"tweets": all_tweets, "liked_ids": liked_ids}
    return render(request, 'tweetapp/listtweet.html', context=tweet_dict)

def addtweet(request):
    if request.POST:
        nickname = request.POST["nickname"]
        message = request.POST["message"]
        print(request.POST["nickname"])
        print(request.POST["message"])
        models.Tweet.objects.create(nickname= nickname, message = message)
        return redirect(reverse('tweetapp:listtweet'))
    else:
        return render(request, 'tweetapp/addtweet.html')
    


@login_required(login_url='/login/')
def addtweetbyform(request):
    if not request.user.is_authenticated:
        return redirect('/login/')
    if request.method == "POST":
        form = AddTweetForm(request.POST, request.FILES)
        if form.is_valid():
            tweet = models.Tweet.objects.create(
                user=request.user,
                nickname=request.user.username,
                message=form.cleaned_data["message_input"]
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
        #print(request.POST)
        form = AddTweetModelForm(request.POST)
        if form.is_valid():
            nickname = form.cleaned_data["nickname"]
            message = form.cleaned_data["message"]
            models.Tweet.objects.create(nickname=nickname, message=message)
            return redirect(reverse('tweetapp:listtweet'))
        else:
            print("error in form!")
            return render(request, 'tweetapp/addtweetbymodelform.html', context={"form": form})
    else:
        form = AddTweetModelForm()
        return render(request, 'tweetapp/addtweetbymodelform.html', context={"form": form})
    
def searchtweet(request):
    query = request.GET.get('q', '')
    if query:
        if query.startswith('@'):
            nickname = query[1:]
            results = models.Tweet.objects.filter(nickname__iexact=nickname)
        else:
            results = models.Tweet.objects.filter(message__icontains=query)
    else:
        results = models.Tweet.objects.none()
    if request.user.is_authenticated:
        liked_ids = models.Like.objects.filter(user=request.user).values_list('tweet_id', flat=True)
    else:
        liked_ids = []
    return render(request, 'tweetapp/listtweet.html', context={"tweets": results, "liked_ids": liked_ids})

def profile(request, username):
    from django.contrib.auth.models import User
    try:
        user = User.objects.get(username=username)
        if not hasattr(user, 'profile'):
            models.Profile.objects.create(user=user)
        profile_exists = True
    except User.DoesNotExist:
        user = None
        profile_exists = False
    
    tweets = models.Tweet.objects.filter(nickname__iexact=username)
    tweet_count = tweets.count()
    
    if request.user.is_authenticated:
        liked_ids = models.Like.objects.filter(user=request.user).values_list('tweet_id', flat=True)
    else:
        liked_ids = []
    
    context = {
        'profile_user': user,
        'profile_exists': profile_exists,
        'tweets': tweets,
        'tweet_count': tweet_count,
        'searched_username': username,
        'liked_ids': liked_ids,
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
        # Profil oluştur
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
        return redirect('/login/')
    tweet = models.Tweet.objects.get(pk=pk)
    like, created = models.Like.objects.get_or_create(user=request.user, tweet=tweet)
    if not created:
        like.delete()
    return redirect(request.META.get('HTTP_REFERER', reverse('tweetapp:listtweet')))