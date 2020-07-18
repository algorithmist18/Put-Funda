# Importing libraries 

from blogposts.models import Post 
from django.forms import ModelForm

# Declaring form prototypes 

class PostForm(ModelForm): 

	class Meta: 

		model = Post
		fields = ['title', 'content']
		