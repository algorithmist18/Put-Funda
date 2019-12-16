# Importing libraries 

from django.shortcuts import render
from .models import Post, PostComment, User 

# Create your views here.

def index(request): 

	return render(request, 'blog_homepage.html') 

def post(request): 

	# TODO: Users post here 

	author = request.user 
	
	user = User.objects.all().filter(username = author.username)[0] 
	print('Author =', user.username)
	context = {}
	context.update({'author' : author})

	print('Post function called.') 

	if request.method == 'POST': 

		content = request.POST.get('content') 
		title = request.POST.get('title') 
		post = Post(author = user, content = content, title = title)
		post.save() 

	# Updating context

	return render(request, 'blog_post.html', context) 

def preview(st): 

	# Extract preview from string [10 words] 

	words = st.split() 
	preview_st = "" 
	length = min(20, len(words))

	for idx in range(0, length): 
		preview_st = preview_st + " " + words[idx] 

	return preview_st  

def display(request): 

	# Display posts 

	author = request.user

	posts = []
	context = {}
	previews = {} 
	authors = {} 

	post_objects = Post.objects.all().order_by('-time') 

	for post in post_objects:

		posts.append(post) 
		previews.update({post.title : preview(post.content)})
		authors.update({post.content : post.author}) 


	print('Number of blog posts', len(previews)) 
	print(posts[0].title)

	# Updating context 

	context.update({'posts' : posts, 'user' : request.user})

	return render(request, 'blog_home.html', context)

def show_post(request):

	# Display single post 

	author = request.GET.get('user')
	post_title = request.GET.get('post') 
	preview = request.GET.get('preview')

	posts = Post.objects.all().filter(title = post_title)

	for post in posts: 

		if post.preview == preview: 

			break
			
	return render(request, 'blog_show.html', {'post' : post})


