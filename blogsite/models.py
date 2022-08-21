from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

#Create your models here.

class Question(models.Model):

	title = models.CharField(max_length = 42, default = 'General', null = True)
	question = models.TextField(null = True, default = 'What is life?')
	answer = models.TextField(null = True)
	genre = models.CharField(max_length = 42)
	time = models.DateTimeField(auto_now_add = True, blank = True)
	author = models.ForeignKey(User, on_delete = models.DO_NOTHING, null = True) 
	likes = models.IntegerField(default = 0) 
	comments = models.IntegerField(default = 0) 

class Like(models.Model): 

	user = models.ForeignKey(User, on_delete = models.CASCADE) 
	question = models.ForeignKey(Question, on_delete = models.CASCADE) 
	time = models.DateTimeField(auto_now_add = True) 

class Comment(models.Model):

	content = models.TextField()
	author = models.ForeignKey(User, on_delete = models.SET_NULL, null = True)
	time = models.DateTimeField(auto_now_add = True, blank = True)
	question = models.ForeignKey(Question, on_delete = models.CASCADE, default = "What is life?")

class Profile(models.Model):

	user = models.OneToOneField(User, on_delete = models.CASCADE)
	phone = models.CharField(max_length = 10, blank=True)
	location = models.CharField(max_length = 25, default='Kolkata')
	birth_date = models.DateField(null=True, blank=True)
	is_online = models.BooleanField(default = False)
	rating = models.FloatField(default = 1500.0, null=True, blank=True)
	volatility = models.FloatField(default = 150.0, null = True, blank = True) 
	no_of_contests_played = models.IntegerField(default = 0, null = True, blank = True) 
	email_confirmed = models.BooleanField(default = False, null = True, blank = True) 
	# Add image field
	picture = models.ImageField(upload_to = 'images/', max_length = 200, blank = True)  

@receiver(post_save, sender = User)
def create_user_profile(sender, instance, created, **kwargs):
	if created:
		Profile.objects.create(user=instance)

@receiver(post_save, sender = User)
def save_user_profile(sender, instance, **kwargs):
	instance.profile.save()