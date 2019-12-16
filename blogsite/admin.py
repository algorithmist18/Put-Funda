from django.contrib import admin
from .models import Profile, Comment, Question
# Register your models here.
admin.site.register(Question)
admin.site.register(Comment)
admin.site.register(Profile)