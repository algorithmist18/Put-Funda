"""blog URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

# Importing libraries 

from django.contrib import admin
from django.urls import include, path
from blogsite import views
from blogposts import views as post_views
from quiz import views as quiz_views
from django.conf import settings 
from django.conf.urls.static import static 

# URL patterns 

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('questions', views.questions, name='questions'),
    path('ask', views.ask, name='ask'),
    path('view', views.list_questions, name = 'view'),
    path('register', views.register, name = 'register'),
    path('login', views.login_view, name = 'login'),    
    path('home', views.homepage, name = 'home'),
    path('logout', views.logout_view, name = 'logout'),
    path('users', views.show_user, name='show_user'),
    path('edit', views.edit_profile, name = 'edit'),
    path('search_users', views.search_users, name = 'search_users'),
    path('search', views.show_search, name = 'show_search'),
    path('delete_feed_question', views.delete_question, name = 'delete_q'),
    path('edit_feed_question', views.edit_question, name = 'edit_q'),
    path('like_question', views.like_question, name = 'like_q'),
    path('username-check', views.validate_username, name = 'username_check'),
    path('email-check', views.validate_email, name = 'email_check'),
    path('image-check', views.validate_image, name = 'image_check'),  
    path('blogposts/', post_views.display, name = 'blog_home'),
    path('blogposts/post', post_views.post, name = 'post'),
    path('blogposts/show_post', post_views.show_post, name = 'show_post'),
    path('blogposts/edit_post', post_views.edit_post, name = 'edit_post'),
    path('blogposts/delete_post', post_views.delete_post, name = 'delete_post'),
    path('quiz/', quiz_views.homepage, name = 'quiz_home'),
    path('quiz/schedule', quiz_views.schedule_quiz, name = 'schedule_quiz'),
    path('quiz/contest', quiz_views.create_contest, name = 'create_contest'),
    path('quiz/view_contest', quiz_views.view_contest, name = 'view_contest'),
    path('quiz/edit_question', quiz_views.edit_question, name = 'edit_question'),
    path('quiz/delete_question', quiz_views.delete_question, name = 'delete_question'),
    path('quiz/play_contest', quiz_views.play_contest, name = 'play_contest'),
    path('quiz/leaderboard', quiz_views.display_leaderboard, name = 'leaderboard'),
    path('quiz/edit_contest', quiz_views.edit_contest, name = 'edit_contest'),
    path('quiz/date-check', quiz_views.is_valid_date, name = 'is_valid_date'),
    path('quiz/updaterating', quiz_views.update_ratings, name = 'update_rating'),
    path('quiz/restorerating', quiz_views.restore_ratings, name='restore_rating'),
    path('quiz/analytics', quiz_views.view_question_analytics, name='question_analytics')
]

if settings.DEBUG: 
    urlpatterns += static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT) 

