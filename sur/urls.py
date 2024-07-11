from django.urls import path
from .views import motion_detection_view ,video_feed ,signup ,home ,index ,object_detection,display_images
from django.contrib.auth import views as auth_views
from .forms import LoginForm



urlpatterns = [
    path('detect-motion/', motion_detection_view, name='detect_motion'),
    path('video-feed/', video_feed, name='video-feed'),
    path('signup/',signup,name='signup'),
    path('home',home , name='home'),
    path('',index,name='index'),
    path('object-detection/',object_detection,name='object_detection'),
    path('display-images/', display_images, name='display_images'),
    path('login/',auth_views.LoginView.as_view(template_name='login.html',authentication_form=LoginForm),name='login'),
]