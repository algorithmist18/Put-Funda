from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class RegisterForm(UserCreationForm):

	phone = forms.CharField(help_text = '10 digit number.')
	location = forms.CharField(max_length = 25)
	birth_date = forms.DateField(help_text = 'Required. Format: YYYY-MM-DD')

	class Meta:

		model = User 
		fields = ('username', 'first_name', 'last_name', 'birth_date', 'password1', 'password2', )