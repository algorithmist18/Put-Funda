# Importing libraries
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.db import models
from registration.views import RegistrationView
from .forms import RegisterForm

class UserSignupView(RegistrationView): 

	register_form = RegisterForm() 

	def register(self, request, form): 

		print(form)
		print(request) 

		new_user = super(UserSignupView, self).register(request, form) 
		return new_user