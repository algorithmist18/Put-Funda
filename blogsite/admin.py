from django.contrib import admin
from .models import Profile, Comment, Post, Question
# Register your models here.
admin.site.register(Question)
admin.site.register(Comment)
admin.site.register(Post)
admin.site.register(Profile)