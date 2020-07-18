# Importing libraries

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django import forms 

# Create your models here.

class Contest(models.Model): 

	host = models.ForeignKey(User, on_delete = models.CASCADE) 
	time = models.DateTimeField() 
	genre = models.CharField(max_length = 20, default = 'General') 


class QuizQuestion(models.Model): 

	question = models.TextField()
	image = models.ImageField(upload_to = 'images/', max_length = 200, blank = True, null = True) 
	options = models.TextField() 
	answer = models.CharField(max_length = 100) 
	contest = models.ForeignKey(Contest, on_delete = models.CASCADE) 

	# Method to separate out options 

	def separate(self): 

		option_list = self.options.split(',') 
		
		return option_list 


	option_list = property(separate) 
		 
