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
from django.contrib import admin
from django.urls import path
from blogsite import views

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
    path('search_users', views.search_users, name = 'search_users'),
    path('search', views.show_search, name = 'show_search')
]
