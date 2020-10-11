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
	guess = models.TextField()
	answer = models.TextField()
	second_answer = models.TextField() 
	third_answer = models.TextField()  
	contest = models.ForeignKey(Contest, on_delete = models.CASCADE) 

class Submission(models.Model): 	

	user = models.ForeignKey(User, on_delete = models.CASCADE) 
	time_taken = models.FloatField() 
	answer = models.TextField() 
	question = models.ForeignKey(QuizQuestion, on_delete = models.CASCADE) 

