# Importing libraries 

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django import forms 

# Create your models here.

class Post(models.Model): 

	title = models.CharField(max_length = 40, default = 'Blog post') 
	content = models.TextField(default = 'Life is good.')  
	time = models.DateTimeField(auto_now_add = True)
	author = models.ForeignKey(User, on_delete = models.CASCADE, null = True) 
	anon = models.BooleanField(default = False, null = True) 


	class Meta: 

		unique_together = (("title", "author")) 

	def trim(self): 

		st = self.content
		words = st.split() 
		preview_st = "" 
		length = min(30, len(words))

		for idx in range(0, length): 
			preview_st = preview_st + " " + words[idx] 

		return preview_st 

	preview = property(trim) 

class PostComment(models.Model): 

	content = models.TextField()
	author = models.ForeignKey(User, on_delete = models.CASCADE) 
	time = models.DateTimeField(auto_now_add = True) 
	post = models.ForeignKey(Post, on_delete = models.CASCADE, default = 'Blog comment') 