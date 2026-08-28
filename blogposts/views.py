# Importing libraries 

from django.shortcuts import render
from .models import Post, PostComment, PostLike, User
from .forms import PostForm
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.urls import reverse
from django.contrib.auth.decorators import login_required
import datetime

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

	logged_in_user = request.user

	posts = []
	context = {}
	previews = {} 
	authors = {} 

	post_objects = Post.objects.all().order_by('-time')

	for post in post_objects:

		post.like_count = PostLike.objects.filter(post = post).count()
		post.user_has_liked = PostLike.objects.filter(post = post, user = logged_in_user).exists()

		posts.append(post)
		previews.update({post.title : preview(post.content)})
		authors.update({post.content : post.author})

	# Updating context

	context.update({'posts' : posts, 'user' : logged_in_user})

	return render(request, 'blog_home.html', context)

@login_required
def like_post(request):

	if request.method != 'GET':
		return JsonResponse({'error': 'Invalid request method.'}, status = 405)

	post_id = request.GET.get('post_id')
	post = Post.objects.get(id = post_id)

	existing_like = PostLike.objects.filter(user = request.user, post = post).first()

	if existing_like:
		existing_like.delete()
		liked = False
	else:
		PostLike.objects.create(user = request.user, post = post)
		liked = True

	count = PostLike.objects.filter(post = post).count()

	return JsonResponse({'liked': liked, 'count': count})

@login_required
def show_post(request):

	# Display single post

	user = request.user

	if request.method == 'POST':

		blogId = request.POST.get('blogid')
		blogPost = Post.objects.get(id = blogId)
		action = request.POST.get('act')

		if action != 'Show comments':

			# Post a comment on the blog

			comment = request.POST.get('comment')
			comment = comment.strip()

			if comment:

				BlogComment = PostComment(content = comment, time = datetime.datetime.now(), author = user, post = blogPost)
				BlogComment.save()

				blogPost.comments = PostComment.objects.filter(post = blogPost).count()
				blogPost.save()

	else:

		blog_id = request.GET.get('id')
		blogPost = Post.objects.all().get(id = blog_id)

	blog_comments = PostComment.objects.filter(post = blogPost).order_by('time')

	args = {
		'user': user,
		'post': blogPost,
		'author': blogPost.author,
		'blog_comments': blog_comments,
		'commentCount': blog_comments.count(),
		'like_count': PostLike.objects.filter(post = blogPost).count(),
		'user_has_liked': PostLike.objects.filter(post = blogPost, user = user).exists(),
	}

	return render(request, 'blog_show.html', args)

@login_required
def edit_post(request): 

	# Editing a blog post 

	author = request.user

	primary_key = request.GET.get('id') 

	print('Author = ', author) 
	print('Primary key of blog post = ', primary_key) 

	# Retrieve post 

	post = Post.objects.get(pk = primary_key) 

	if author != post.author:

		url = reverse('blog_home')
		return HttpResponseRedirect(url) 


	if request.method == 'POST': 

		form = PostForm(request.POST, instance = post) 

		print(form.errors) 

		if form.is_valid(): 

			# Valid post 

			form.save() 
			message = 'Blog post updated, successfully.' 
			print(message) 
			url = reverse('show_post')
			return HttpResponseRedirect('{}?id={}'.format(url, post.id)) 

		else: 

			message = 'Uh oh! Blog post could not be updated, try again later.' 
			print(message) 
			return render(request, 'blog_edit.html', {'post' : post, 'author' : author, 'id' : primary_key}) 

	else: 

		#post_form = PostForm(instance = post) 
		return render(request, 'blog_edit.html', {'post' : post, 'author' : author, 'id' : primary_key})

@login_required
def delete_post(request): 

	# Deleting a post 

	author = request.user 
	status = request.GET.get('status') 

	primary_key = request.GET.get('id') 
	post = Post.objects.get(pk = primary_key)

	if author != post.author:

		url = reverse('blog_home')
		return HttpResponseRedirect(url) 

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

