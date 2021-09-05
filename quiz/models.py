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
	has_rating_updated = models.BooleanField(default = False, blank = True, null = True) 

class QuizQuestion(models.Model): 

	question = models.TextField()
	image = models.ImageField(upload_to = 'images/', max_length = 200, blank = True, null = True)
	guess = models.TextField(blank = True)
	answer = models.TextField()
	second_answer = models.TextField(blank = True) 
	third_answer = models.TextField(blank = True)  
	contest = models.ForeignKey(Contest, on_delete = models.CASCADE) 

class Submission(models.Model): 	

	user = models.ForeignKey(User, on_delete = models.CASCADE) 
	time_taken = models.FloatField() 
	answer = models.TextField() 
	question = models.ForeignKey(QuizQuestion, on_delete = models.CASCADE) 

class RatingHistory(models.Model): 

	user = models.ForeignKey(User, on_delete = models.CASCADE) 
	contest = models.ForeignKey(Contest, on_delete = models.CASCADE) 
	rating = models.FloatField(default = 1500, blank = True, null = True) 