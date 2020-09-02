
#Importing libraries

from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.db import models
from django.contrib.auth import login, authenticate
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required 
from blogsite.forms import RegisterForm
from blogsite.models import Question, Like, Comment, Profile
from django.dispatch import receiver
from django.contrib.auth.forms import AuthenticationForm
from django.http import HttpResponseRedirect, JsonResponse
from .models import Comment, User
from django.contrib.auth.signals import user_logged_in, user_logged_out
import datetime, collections
from datetime import timezone
from graphos.sources.simple import SimpleDataSource
from graphos.renderers.gchart import PieChart 
from django.core.files.storage import FileSystemStorage 

# Create your views here.

def index(request):
	return render(request, 'index.html')

@login_required
def homepage(request):

	username = request.GET.get('user')

	if username == None:
		return render(request, 'homepage.html', {'user' : request.user})
		
# Function for registering a user

def register(request):

	if request.method == 'POST':

		form = RegisterForm(request.POST)
		
		print(form.errors)
		
		print(form.is_valid) 

		if form.is_valid():
			
			user = form.save()
			user.refresh_from_db()
			user.profile.birth_date = form.cleaned_data.get('birth_date')
			user.save()
			raw_password = form.cleaned_data.get('password2')
			user.set_password(raw_password)
			user = authenticate(username = user.username, password = raw_password)
			
			login(request, user)
			
			print('Logged in.')
			
			return render(request, 'homepage.html', {'user' : user})
		
		else:

			return render(request, 'register.html', {'form' : form})
			
	else:

		form = RegisterForm()

	return render(request, 'register.html', {'form' : form})

# Function for logging in

def login_view(request):

	# Redirecting to homepage if user already authenticated 

	if request.user.is_authenticated:

		return render(request, 'homepage.html', {'user' : request.user})

	# If not authenticated, authenticate using Django authentication system 

	if request.method == 'POST':

		form = AuthenticationForm(request.POST)

		username = request.POST.get('username')
		passwd = request.POST.get('password')

		# Checking if password is stored in plain text or not 

		if form.is_valid:

			# Authenticate the user 

			try:

				user = authenticate(username = username, password = passwd)

				login(request, user)

				next_page_url = 'home?username=' + username

				return redirect('home')

			except:

				# Authentication error - redirect to login page with message 

				return render(request, 'login.html', {'form' : form, 'error' : 'Username/Password invalid'})
		else:

			print(form.errors)
	else:

		form = AuthenticationForm()

	return render(request, 'login.html', {'form' : form})

# Function for logging a person out
def logout_view(request):

	logout(request)
	return redirect('index')

@login_required
def questions(request):

	return render(request, 'questions.html')

@login_required
def ask(request):

	title = request.POST.get('title')
	question = request.POST.get('question')
	answer = request.POST.get('answer')

	if title == " " or question == ' ' or answer == ' ':
		print('Invalid question. Ignored.')
		pass
	elif title == None or question == None or answer == None:
		print('Invalid question, ignored.')
		pass
	else:
		title = title.strip()
		question = question.strip() 
		answer = answer.strip() 
		q = Question(title = title, question = question, answer = answer, time = datetime.datetime.now(), author = request.user)
		q.save()

	return render(request, 'questions.html')

@login_required
def load_comments(request, ques, comments):

	q_list = Question.objects.all().order_by('-time')
	genres = Question.objects.values('title')
	g = request.GET.get('genre')
	l = list(genres.values('title'))
	g_list = []

	for d in l:
		g_list.append(d['title'])
	g_set = set(g_list)
	
	if g != None and g != ' ':
		q_list = Question.objects.filter(title = g).order_by('-time')
		args = {'q_list' : q_list, 'g_list' : g_set, 'question' : ques, 'q_times' : question_times, 'comments' : comments}
		return render(request, 'question_list_display_genre.html', args)
	else:
		args = {'q_list' : q_list, 'g_list' : g_set, 'question' : ques, 'q_times' : question_times, 'comments' : comments}
		return render(request, 'questions_list_display.html', args)

@login_required
def delete_question(request): 

	# Function to delete a question 

	author = request.user.username # holding the name only 
	question = request.GET.get('q') 
	act = request.POST.get('act') 

	question_object = Question.objects.filter(question = question) 

	if request.method == 'POST': 

		if act == "Delete": 

			# Delete question 
			question_object.delete()
			return HttpResponseRedirect('view?msg=delete_success')

		else: 

			# Cancel and return 
			return redirect('view') 

	return HttpResponseRedirect('view?msg=delete_success')  

@login_required
def list_questions(request):

	author = request.user.username
	current_time = datetime.datetime.now(timezone.utc)

	print('Author = {}'.format(author))

	if request.method == 'POST':

		act = request.POST.get('act')
		show = request.POST.get('show')
		
		# Getting details of question in context

		q = request.POST.get('questions')
		question = Question.objects.filter(question = q)[0]		
		q_list = Question.objects.all().order_by('-time')

		for element in q_list: 

			print(element.comments) 

		# Appending the timestamps for each question 

		question_times = {}

		for elem in q_list:
			question_times.update({elem.question : (current_time - elem.time).total_seconds() / 3600 })

		# Displaying data according to act variable

		if act == 'Submit':

			genre = request.GET.get('genre')

			if genre != None:

				add_comment(request)

				genres = Question.objects.values('title')
				g = genre
				l = list(genres.values('title'))
				g_list = []

				for d in l:
					g_list.append(d['title'])
				g_set = set(g_list)
				
				if g != None and g != ' ':

					q_list = Question.objects.filter(title = g).order_by('-time')
					args = {'q_list' : q_list, 'g_list' : g_set, 'ques' : q, 'q_times' : question_times, 'author' : author}
					return render(request, 'question_list_display_genre.html', args)

				else:

					args = {'q_list' : q_list, 'g_list' : g_set, 'ques' : q, 'author' : author, 'q_times' : question_times}
					return render(request, 'questions_list_display.html', args)
			else:

				add_comment(request)

				return redirect('view')

		elif act == 'Show comments':

			comments = Comment.objects.filter(question = question).order_by('time')

			genres = Question.objects.values('title')
			g = request.GET.get('genre')
			l = list(genres.values('title'))
			g_list = []
			
			for d in l:
				g_list.append(d['title'])
			g_set = set(g_list)
			
			if g != None and g != ' ':

				q_list = Question.objects.filter(title = g).order_by('-time')
				args = {'q_list' : q_list, 'g_list' : g_set, 'ques' : q, 'q_times' : question_times, 'comments' : comments, 
				'q_times' : question_times, 'author' : author}
				return render(request, 'question_list_display_genre.html', args)

			else:

				args = {'q_list' : q_list, 'g_list' : g_set, 'ques' : q, 'comments' : comments, 'q_times' : question_times, 'author' : author}
				return render(request, 'questions_list_display.html', args)	


		elif act == "Delete": 

			# Delete question 
			
			args = {'ques' : question, 'author' : author} 

			# return redirect('delete?q={}')

			return render(request, 'question_delete.html', args)

		else: 

			# Show answer to the question

			genres = Question.objects.values('title')

			g = request.GET.get('genre')
			l = list(genres.values('title'))

			g_list = []

			for d in l:
				g_list.append(d['title'])
			g_set = set(g_list)
			
			if g != None and g != ' ':

				q_list = Question.objects.filter(title = g).order_by('-time')
				args = {'q_list' : q_list, 'g_list' : g_set, 'ques' : q, 'q_times' : question_times,
				'q_times' : question_times, 'author' : author, 'answer' : question.answer}
				return render(request, 'question_list_display_genre.html', args)

			else:

				args = {'q_list' : q_list, 'g_list' : g_set, 'ques' : q, 'q_times' : question_times, 
				'author' : author, 'answer' : question.answer}
				return render(request, 'questions_list_display.html', args)	

	else:

		query = request.GET.get('query')

		if query != None and query != ' ' and query != '':

			# Redirecting to search page

			return HttpResponseRedirect('search?query={}'.format(query))

		else:

			q_list = Question.objects.all().order_by('-time')
			genres = Question.objects.values('title')
			g = request.GET.get('genre')
			l = list(genres.values('title'))
			g_list = []

			question_times = {}

			for elem in q_list:	
				question_times.update({elem.question : (current_time - elem.time).total_seconds() / 3600 })

			for d in l:
				g_list.append(d['title'])
			g_set = set(g_list)

			if g != None and g != ' ':

				q_list = Question.objects.filter(title = g).order_by('-time')
				args = {'q_list' : q_list, 'g_list' : g_set, 'q_times' : question_times, 'author' : author}
				return render(request, 'question_list_display_genre.html', args)

			else:

				args = {'q_list' : q_list, 'g_list' : g_set, 'q_times' : question_times, 'author' : author}
				return render(request, 'questions_list_display.html', args)

@login_required
def add_comment(request):

	comm = request.POST.get('comment')
	ques = request.POST.get('questions')
	question = Question.objects.filter(question = ques)[0]

	if comm != None and comm != ' ' and comm != '':

		comment = Comment(content = comm, time = datetime.datetime.now(), author = request.user, question = question)
		comment.save()

		if question.comments == 0: 

			question.comments = Comment.objects.filter(question = question).count() 

		else:

			question.comments = question.comments + 1 

		question.save() 

		print(question.comments) 

# Method to return questions asked by users 

@login_required
def questions_by_user(username): 

	user = User.objects.get(username = username) 
	questions = Question.objects.filter(author = user).order_by('-time')

	# Create lists of genres and questions 

	genreList = [] 
	questionList = [] 

	# Append questions and genres 

	for question in questions: 

		genre = question.title 

		questionList.append(question) 
		genreList.append(genre) 

	return questionList, genreList 

# Method to create a chart object from given list 

def create_chart(array, name = 'Genre'): 

	arrayCount = collections.Counter(array) 

	# Creating a pie chart 

	data = [[name, 'Count']]
	count = 0 

	for key in arrayCount: 

		data.append([key, arrayCount[key]]) 
		count += 1 

	# Create a data source object 

	dataSource = SimpleDataSource(data = data) 

	# Chart object 

	chart = PieChart(dataSource, options = {'title' : 'Genres', 'width': 450, 'height': 250}) 

	return chart 

@login_required
def show_user(request):

	username = request.GET.get('user') 
	user = User.objects.get(username = username)
	
	print(user.first_name)

	current_time = datetime.datetime.now(timezone.utc)
	questions = Question.objects.filter(author = user).order_by('-time')

	print('Number of questions asked by {} = {}'.format(user.first_name, len(questions)))

	genre_lists = []
	question_list = []

	logged_in_user = request.user 

	for question in questions:

		question_list.append(question)
		genre_lists.append(question.title)

	# Creating a pie chart 

	chart = create_chart(genre_lists, name = 'Genre') 

	genre_lists = set(genre_lists)

	args = {'user' : user, 'q_list' : question_list, 'no_of_questions' : len(questions), 
			'genres' : genre_lists,'chart' : chart, 'org_user' : logged_in_user} 

	if request.method == 'POST':

		# A question has been answered

		act = request.POST.get('act')
		show = request.POST.get('show')
		
		# Getting details of question in context

		q = request.POST.get('questions')
		question = Question.objects.filter(question = q)[0]		
		q_list = Question.objects.all().order_by('-time')

		question_times = {}

		for elem in q_list:
			question_times.update({elem.question : (current_time - elem.time).total_seconds() / 3600 })

		# Displaying data according to act variable

		if act == 'Submit':

			genre = request.GET.get('genre')

			if genre != None:

				add_comment(request)

				genres = Question.objects.values('title')
				g = genre
				l = list(genres.values('title'))
				g_list = []

				for d in l:
					g_list.append(d['title'])
				g_set = set(g_list)
				
				if g != None and g != ' ':

					q_list = Question.objects.filter(title = g).order_by('-time')
					#args = {'q_list' : q_list, 'g_list' : g_set, 'ques' : q, 'q_times' : question_times, 'author' : author}
					return HttpResponseRedirect('users?user={}'.format(username))

				else:

					args = {'q_list' : q_list, 'g_list' : g_set, 'ques' : q, 'author' : author, 'q_times' : question_times}
					return HttpResponseRedirect('users?user={}'.format(username))
			else:

				add_comment(request)
				return HttpResponseRedirect('users?user={}'.format(username))

		elif act == 'Show comments':

			comments = Comment.objects.filter(question = question).order_by('time')
			
			genres = Question.objects.values('title')
			g = request.GET.get('genre')
			l = list(genres.values('title'))
			g_list = []
			
			for d in l:
				g_list.append(d['title'])
			g_set = set(g_list)
			
			if g != None and g != ' ':

				q_list = Question.objects.filter(title = g).order_by('-time')
				args.update({'ques' : q, 'q_times' : question_times, 'comments' : comments, 
				'q_times' : question_times})
				return render(request, 'user_display.html', args)

			else:
				args.update({'ques' : q, 'q_times' : question_times, 'comments' : comments, 
				'q_times' : question_times})
				return render(request, 'user_display.html', args)
		else: 

			# Show answer to the question
			
			print('Need to show answer to {}'.format(question.question))

			genres = Question.objects.values('title')

			g = request.GET.get('genre')
			l = list(genres.values('title'))

			g_list = []

			for d in l:
				g_list.append(d['title'])
			g_set = set(g_list)
			
			if g != None and g != ' ':

				q_list = Question.objects.filter(title = g).order_by('-time')
				args.update({'ques' : q, 'q_times' : question_times,
				'q_times' : question_times, 'answer' : question.answer})
				return render(request, 'user_display.html', args)

			else:

				args.update({'ques' : q, 'q_times' : question_times, 
				 'answer' : question.answer})
				return render(request, 'user_display.html', args)

	# Get user profile information

	return render(request, 'user_display.html', args)

@login_required
def show_search(request):

	author = request.user.username
	current_time = datetime.datetime.now(timezone.utc)

	query = request.GET.get('query')

	# Defining data to pass to templates
	
	question_list = []
	question_times = {}

	# Searching for data

	questions = Question.objects.all()

	for element in questions:
		s = element.question 
		if s != None:
			if s.find(query) != -1:
				question_list.append(element)

	for elem in question_list:
		question_times.update({elem.question : (current_time - elem.time).total_seconds() / 3600 })

	# Show search results of questions

	if request.method == 'GET':

		if query != None and query != ' ' and query != '':

			# Redirect to search page

			print('Searching for {}'.format(query))

			return render(request, 'search_results.html', {'q_list' : question_list, 'q_times' : question_times})

		else:

			return render(request, 'search_results.html', {'q_list' : {}, 'q_times' : {}})

	else: 

		# Load/Submit comment or Show the answer

		act = request.POST.get('act')
		
		# Getting details of question in context

		q = request.POST.get('questions')
		question = Question.objects.filter(question = q)[0]

		# Taking action according to act variable

		if act == 'Submit':
			# Submit comment
			add_comment(request)
			args = {'q_list' : question_list, 'ques' : q, 'author' : author, 'q_times' : question_times}
			return render(request, 'search_results.html', args)

		elif act == 'Show comments':
			# Load comments
			comments = Comment.objects.filter(question = question).order_by('-time')
			args = {'q_list' : question_list, 'ques' : q, 'comments' : comments, 'q_times' : question_times, 'author' : author}
			return render(request, 'search_results.html', args)	

		else:
			# Show answer
			args = {'q_list' : question_list, 'ques' : q, 'answer' : question.answer, 'q_times' : question_times, 'author' : author}
			return render(request, 'search_results.html', args)

@login_required
def search_users(request):

	user_name = request.GET.get('q')

	print('User to be searched = {}'.format(user_name))

	# Search by first name, last name and username 

	users_by_firstname = User.objects.filter(first_name__icontains = user_name)
	users_by_lastname = User.objects.filter(last_name__icontains = user_name)
	users_by_username = User.objects.filter(username__icontains = user_name) 

	user_list = []

	for users in users_by_firstname:
		user_list.append(users)

	for users in users_by_lastname:
		user_list.append(users)

	for users in users_by_lastname: 
		user_list.append(users) 

	user_list = set(user_list) 

	print(user_list)

	return render(request, 'search_user_page.html', {'user_list' : user_list, 'query' : user_name})

# Method to edit profile details 

@login_required
def edit_profile(request): 

	# Method for editing and saving the profile 

	username = request.GET.get('user') 
	user = User.objects.get(username = username)
	logged_in_user = request.user 

	# Check if user is logged into their own profile 

	if logged_in_user != user: 

		# Redirect to home 

		return HttpResponseRedirect('edit?user={}&msg={}'.format(logged_in_user.username, 'bad_request'))  


	print(user.first_name, user.last_name, user.profile.birth_date)  
	
	if request.method == 'POST': 

		# Save user profile 

		image = request.FILES.get('avatar')

		if image is not None: 

			# Assign image to profile 

			file_storage = FileSystemStorage() 
			filename = file_storage.save(image.name, image) 
			file_url = file_storage.url(filename) 

			# Check if image is valid 
		
			user.profile.picture = image 

		# Getting POST data 

		location = request.POST.get('location')
		dateOfBirth = request.POST.get('dateOfBirth')

		# Assign to user profile

		user.profile.location = location 

		if dateOfBirth != '': 

			user.profile.birth_date = dateOfBirth

		# Save profile 

		user.profile.save() 

		message = 'Edits saved successfully.'

		print(message) 

		return HttpResponseRedirect('users?user={}'.format(username)) 

	else:

		return render(request, 'edit_profile.html', {'user' : user})

# Liking a question 

@login_required
def like_question(request): 

	if request.method == 'GET': 

		question_id = request.GET.get('question_id') 
		question_object = Question.objects.get(id = question_id) 
		new_like = Like.objects.get_or_create(user = request.user, question = question_object) 

		# Get the number of likes for the question 

		likes = Like.objects.all().filter(question = question_object) 

		print(likes) 

		number_of_likes = len(likes) 

		for like in likes:

			print(like.user.username) 

		question_object.likes = number_of_likes

		question_object.save()  

		print('Number of likes obtained = ', number_of_likes) 

		return HttpResponse(number_of_likes) 

	else:

		return HttpResponse(0) 

# Method to count alphabets in a string 

def count_alphabet(token): 

	alpha_count = 0 

	# Check if string has an alphabet 

	for character in token: 

		if character.isalpha(): 

			alpha_count = alpha_count + 1 

	return alpha_count 

# Method to validate a username 

def validate_username(request):

	# Validate username 

	response = {} 

	if request.method == 'GET': 

		username = request.GET.get('username')

		if count_alphabet(username) == 0: 

			response['valid'] = 'NO'
			response['message'] = 'Username is not a valid string'

			return JsonResponse(response) 

		# Check if username has underscore 

		try:

			user = User.objects.get(username = username) 

		except User.DoesNotExist:

			response.update({'valid' : 'YES'})
			response.update({'message' : 'Username is valid'})

			print(len(response)) 

			return JsonResponse(response)

		response.update({'valid' : 'NO'})
		response.update({'message' : 'Username is taken'})

		return JsonResponse(response)

	else:

		return JsonResponse('')

# Method to validate email address 

def validate_email(request): 

	# Initialize JSON response 

	response = {} 

	extensions = ['@gmail.com', '@yahoo.co.in', '@yahoo.com', '@rediffmail.com'] 

	if request.method == 'GET': 

		# Extract email ID 

		email = request.GET.get('email') 

		# Check if email string is an email ID or not 

		found = False 

		for extension in extensions: 

			if email.endswith(extension): 

				found = True 
				break

		if found == False:

			# Invalid email ID 

			response['valid'] = 'NO'
			response['message'] = 'This is not a valid email ID'

			return JsonResponse(response) 

		# Validate string form 

		print(email) 

		try: 

			users = User.objects.filter(email = email)

		except User.DoesNotExist: 

			# Email unique 

			response['valid'] = 'YES' 
			response['message'] = 'Email ID is valid'

			return JsonResponse(response) 

		noOfUsers = len(users) 

		if noOfUsers == 0: 

			# Unique email ID 

			response['valid'] = 'YES' 
			response['message'] = 'Email ID is valid'

		else:

			# Email has been taken 

			response['valid'] = 'NO'
			response['message'] = 'This email ID has been used before'

		return JsonResponse(response) 

	else:

		return JsonResponse('') 

# Method to validate an image 

def validate_image(request): 

	# Return true if image is a valid one 

	extensions = ['.jpg', '.png', '.gif', '.jpeg']
	response = {} 

	if request.method == 'GET': 

		file = request.GET.get('imageFile') 
		
		file = file.lower() 

		print(file) 

		for extension in extensions: 

			if file.endswith(extension): 

				# Probably an image file 

				print(extension) 

				response['valid'] = 'YES'
				response['message'] = 'Image file is OK'

				return JsonResponse(response)  

		response['valid'] = 'NO'
		response['message'] = 'Image file is invalid.\nPlease upload another one'

		return JsonResponse(response) 

	else:

		return JsonResponse(response) 


# Receiver signals: to check whether user is logged in or not

@receiver(user_logged_in)

def got_online(sender, user, request, **kwargs):

	print('{} just got online.'.format(user.username))
	user.profile.is_online = True
	user.save()

@receiver(user_logged_out)

def got_offline(sender, user, request, **kwargs):

	print('{} offline.'.format(request.user.username))
	request.user.profile.is_online = False
	user.save()