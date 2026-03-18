from django.urls import path
from . import views
app_name = 'tweetapp'
urlpatterns = [
    path('', views.listtweet, name = 'listtweet'), #ardakorkmaz.com/tweetapp/
    path('addtweet/',views.addtweet, name= 'addtweet'), #ardakorkmaz.com/tweetapp/addtweet/
    path('addtweetbyform/', views.addtweetbyform, name = 'addtweetbyform'), #ardakorkmaz.com/tweetapp/addtweetbyform/
    path('addtweetbymodelform',views.addtweetbymodelform, name="addtweetbymodelform"), #ardakorkmaz.com/tweetapp/addtweetbymodelform/
    path('search/', views.searchtweet, name='searchtweet'),
    path('profile/<str:username>/', views.profile, name='profile'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path('register/',views.RegisterView.as_view(), name="register"),
    path('delete/<int:pk>/', views.delete_tweet, name='delete_tweet'),
    path('like/<int:pk>/', views.like_tweet, name='like_tweet'),
]