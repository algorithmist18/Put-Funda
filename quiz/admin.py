# Importing libraries 

from django.contrib import admin
from .models import QuizQuestion, Contest, Submission, RatingHistory

# Register your models here.

admin.site.register(QuizQuestion) 
admin.site.register(Contest) 
admin.site.register(Submission) 
admin.site.register(RatingHistory) 