from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.forms.widgets import TextInput

class RegisterForm(UserCreationForm):
	
	#location = forms.CharField(max_length = 25)
	#birth_date = forms.DateField(help_text = 'Required. Format: YYYY-MM-DD')
	email = forms.CharField(max_length = 50) 
	username = forms.CharField(max_length=15) 
	
	class Meta:

		model = User 
		fields = ('username', 'first_name', 'email', 'last_name', 'password1', 'password2')

	def clean_email(self):

		email = self.cleaned_data.get('email')

		if User.objects.filter(email = email).exists():
			raise forms.ValidationError('Invalid email, already taken')

		return email