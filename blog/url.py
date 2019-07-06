from django.conf.urls import urls
from django.contrib import admin
from . import views

urlpatterns = [

	url(r'^admin/', admin.site.urls),
	url(r'^login/', views.index, name='index'),
	url(r'^view/', views.list_questions, name='view'),
	url(r'^register/', views.register, name='register'),
	url(r'^login/', views.login_view, name='login'),
	url(r'^home/', views.homepage, name='home'),
	url(r'^logout/', views.logout_view, name='logout'),
	url(r'$users/', views.show_user, name='show_user')
	url(r'$search', views.show_search, name='show_search')
]