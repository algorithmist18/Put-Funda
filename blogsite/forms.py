from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.forms.widgets import TextInput

class RegisterForm(UserCreationForm):
	
	location = forms.CharField(max_length = 25)
	birth_date = forms.DateField(help_text = 'Required. Format: YYYY-MM-DD')
	username = forms.CharField(widget = TextInput(attrs = {'id' : 'username', 'placeholder' : 'username'}))

	class Meta:

		model = User 
		fields = ('username', 'first_name', 'last_name', 'birth_date', 'password1', 'password2', )
