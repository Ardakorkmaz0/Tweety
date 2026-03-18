from django import forms
from django.forms import ModelForm
from tweetapp.models import Tweet
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class AddTweetForm(forms.Form):
    message_input = forms.CharField(label="Message", max_length=280, 
                                    widget=forms.Textarea(attrs={"class":"tweetmessage"}))

    

class AddTweetModelForm(ModelForm):
    class Meta:
        model = Tweet
        fields = ["nickname","message"]

class ProfileForm(forms.Form):
    first_name = forms.CharField(label="First Name", max_length=50, required=False)
    last_name = forms.CharField(label="Last Name", max_length=50, required=False)
    age = forms.IntegerField(label="Age", required=False, min_value=18, max_value=150)
    bio = forms.CharField(label="Bio", max_length=160, required=False,
                          widget=forms.Textarea(attrs={"class": "tweetmessage", "rows": 3}))
    profile_image = forms.ImageField(label="Profile Photo", required=False)

class RegisterForm(UserCreationForm):
    first_name = forms.CharField(label="First Name", max_length=50, required=False)
    last_name = forms.CharField(label="Last Name", max_length=50, required=False)
    age = forms.IntegerField(label="Age", required=False, min_value=18, max_value=150)
    class Meta:
        model = User
        fields = ['username', 'password1', 'password2', 'first_name', 'last_name']