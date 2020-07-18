# Importing libraries 

from django.shortcuts import render
from .models import Post, PostComment, User 
from .forms import PostForm 
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse 
from django.contrib.auth.decorators import login_required

# Create your views here.

@login_required
def index(request): 

	return render(request, 'blog_homepage.html') 

@login_required
def post(request): 

	# TODO: Users post here 

	author = request.user 
	
	user = User.objects.all().filter(username = author.username)[0] 
	print('Author =', user.username)
	context = {}
	context.update({'author' : author})

	if request.method == 'POST': 

		title = request.POST.get('title') 

		content = request.POST.get('content') 

		anonymous = request.POST.get('anon') 

		print('Anonymous =', anonymous)

		post_object = Post(title = title, content = content, author = author)  

		if anonymous is None:

			post_object.anon = False

		else:

			post_object.anon = True

		post_object.save() 

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

@login_required
def display(request): 

	# Display posts 

	author = request.user

	posts = []
	context = {}
	previews = {} 
	authors = {} 

	post_objects = Post.objects.all().order_by('-time') 
	user = User.objects.all().filter(username = author)[0] 

	for post in post_objects:

		posts.append(post) 
		previews.update({post.title : preview(post.content)})
		authors.update({post.content : post.author}) 


	print('Number of blog posts', len(previews)) 
	print(posts[0].title)

	# Updating context 

	context.update({'posts' : posts, 'user' : user})

	return render(request, 'blog_home.html', context)

@login_required
def show_post(request):

	# Display single post 

	author = request.GET.get('user')
	post_title = request.GET.get('post') 
	preview = request.GET.get('preview')

	posts = Post.objects.all().filter(title = post_title)
	user = User.objects.all().filter(username = author)[0] 

	print(author, user.username) 

	for post in posts: 

		if post.preview == preview: 

			break
			
	return render(request, 'blog_show.html', {'post' : post, 'author' : user})

@login_required
def edit_post(request): 

	# Editing a blog post 

	author = request.user

	primary_key = request.GET.get('id') 

	print('Author = ', author) 
	print('Primary key of blog post = ', primary_key) 

	# Retrieve post 

	post = Post.objects.get(pk = primary_key) 

	if request.method == 'POST': 

		form = PostForm(request.POST, instance = post) 

		if form.is_valid(): 

			# Valid post 

			form.save() 
			message = 'Blog post updated, successfully.' 
			print(message) 
			url = reverse('show_post')
			return HttpResponseRedirect('{}?user={}&post={}&preview={}'.format(url, author.username, post.title, post.preview)) 

		else: 

			message = 'Uh oh! Blog post could not be updated, try again later.' 
			print(message) 
			return render(request, 'blog_home.html') 

	else: 

		post_form = PostForm(instance = post) 
		return render(request, 'blog_edit.html', {'form' : post_form, 'author' : author, 'id' : primary_key})

@login_required
def delete_post(request): 

	# Deleting a post 

	author = request.user 
	status = request.GET.get('status') 

	primary_key = request.GET.get('id') 
	post = Post.objects.get(pk = primary_key)

	if status is None: 

		# Redirect to confirmation page 

		return render(request, 'delete_post_confirmation.html', {'post' : post, 'author' : author})

	else: 

		if post.author.username == author.username: 

			# Delete post if author is logged in user 

			if status == 'confirm': 

				print('Deleting post right now.') 
				post.delete() 
				url = reverse('blog_home')
				return HttpResponseRedirect(url) 

			else:

				url = reverse('blog_home')
				return HttpResponseRedirect(url) 

		else: 

			message = 'Uh oh! Logged in user not the author.' 
			print(message) 
			return None 
