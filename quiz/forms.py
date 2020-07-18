# Importing libraries 

from quiz.models import Contest, QuizQuestion  
from django.forms import ModelForm

# Declaring form prototypes 

class QuizForm(ModelForm): 

	class Meta: 

		model = QuizQuestion
		fields = ['question', 'image', 'options', 'answer', 'contest']