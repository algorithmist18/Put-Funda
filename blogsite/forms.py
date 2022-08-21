from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.forms.widgets import TextInput
from captcha.fields import ReCaptchaField
from captcha.widgets import ReCaptchaV2Checkbox

class RegisterForm(UserCreationForm):
	
	#location = forms.CharField(max_length = 25)
	#birth_date = forms.DateField(help_text = 'Required. Format: YYYY-MM-DD')
	email = forms.CharField(max_length = 50) 
	username = forms.CharField(max_length=15) 
	
	class Meta:

		model = User 
		fields = ('username', 'first_name', 'email', 'last_name', 'password1', 'password2')

		def clean(self): 

			cleaned_data = super().clean()
			email = cleaned_data.get('email') 

			if User.objects.filter(email = email).exists():

				error_message = 'Invalid email, already taken'
				self.add_error('email', error_message) 

class ForgotPasswordForm(): 

	email = forms.CharField(max_length = 50) 
	captcha = ReCaptchaField() 

class ResetPasswordForm(UserCreationForm): 

	class Meta:

		model = User 
		fields = ('password1', 'password2')