
#Importing libraries

from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.db import models
from django.contrib.auth import login, authenticate
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required 
from blogsite.forms import RegisterForm
from blogposts.models import Post
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
from quiz.models import Contest, QuizQuestion, Leaderboard
import pytz

# Create your views here.

def index(request):

	response = {} 
	current_time = datetime.datetime.now(pytz.timezone('UTC')) 
	new_contests = [] 
	active_contests = [] 

	# Fetch blogs 
	blog_posts = Post.objects.all().order_by("-time")[0:10]

	# Fetch leaderboard
	users = Profile.objects.all().order_by("-rating")[0:10] 

	# Fetch leaderboard of previous contest 
	previous_contest = Contest.objects.all().filter(time__lt = current_time, has_rating_updated = True).order_by('-time')[:1] 
	print(previous_contest[0].id)
	players = list(Leaderboard.objects.all().filter(contest = previous_contest, rank__lt = 11))[:10]

	# Fetch upcoming contests 
	for contest in Contest.objects.all().order_by("-time"):

		question_count = QuizQuestion.objects.filter(contest = contest).count() 

		# Append to active contests 
		time_difference = (contest.time - current_time).total_seconds() 
		time_difference /= 60 
		time_difference *= -1

		if time_difference >= 0 and time_difference <= contest.valid_for and question_count >= 10: 
			active_contests.append(contest) 


	for contest in Contest.objects.all().filter(time__gt = current_time).order_by("time"): 

		question_count = QuizQuestion.objects.filter(contest = contest).count() 
		
		if question_count >= 10: 
			new_contests.append(contest)


	# Fetch latest two past contests 
	response['blog_posts'] = blog_posts
	response['users'] = users 
	response['new_contests'] = new_contests
	response['active_contests'] = active_contests
	response['players'] = players

	return render(request, 'index.html', response)

@login_required
def homepage(request):

	username = request.GET.get('user')
	user = request.user
	response = {} 
	current_time = datetime.datetime.now(pytz.timezone('UTC')) 
	new_contests = [] 
	active_contests = [] 

	# Fetch blogs 
	blog_posts = Post.objects.all().order_by("-time")[0:10]

	# Fetch leaderboard
	users = Profile.objects.all().order_by("-rating")[0:10] 

	# Fetch upcoming contests 
	for contest in Contest.objects.all().order_by('-time'):

		question_count = QuizQuestion.objects.filter(contest = contest).count() 

		# Append to active contests 
		time_difference = (contest.time - current_time).total_seconds() 
		time_difference /= 60 
		time_difference *= -1

		if time_difference >= 0 and time_difference <= contest.valid_for and question_count >= 10: 
			active_contests.append(contest) 


	for contest in Contest.objects.all().filter(time__gt = current_time).order_by('time'): 

		question_count = QuizQuestion.objects.filter(contest = contest).count() 
		
		if question_count >= 10: 
			new_contests.append(contest)


	# Fetch latest two past contests 
	response['blog_posts'] = blog_posts
	response['users'] = users 
	response['new_contests'] = new_contests
	response['active_contests'] = active_contests
	response['user'] = user

	return render(request, 'homepage.html', response)
		
# Function for registering a user

def register(request):

	if request.method == 'POST':

		form = RegisterForm(request.POST)
	
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
			request.user = user
			return homepage(request) 
		
		else:

			return render(request, 'register.html', {'form' : form})
			
	else:

		form = RegisterForm()

	return render(request, 'register.html', {'form' : form})

# Function for logging in
def login_view(request):

	# Redirecting to homepage if user already authenticated 
	if request.user.is_authenticated:
		return homepage(request)

	# If not authenticated, authenticate using Django authentication system 
	if request.method == 'POST':

		form = AuthenticationForm(request.POST)

		# Retrieve username and password
		username = request.POST.get('username')
		passwd = request.POST.get('password')

		if form.is_valid:

			# Authenticate the user 

			print('Form is valid') 

			try:

				user = authenticate(username = username, password = passwd)

				login(request, user)

				next_page_url = 'home?username=' + username

				print(next_page_url) 

				return redirect('home')

			except:

				# Authentication error - redirect to login page with message 

				return render(request, 'login.html', {'form' : form, 'error' : 'Username/Password incorrect'})
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

	# Fetch question and user data

	question_id = request.GET.get('question_id') 
	author = request.GET.get('user') 
	user = request.user 

	# Make a DB call 

	question = Question.objects.get(id = question_id) 
	author = User.objects.get(username = author) 

	# Check if valid request 

	if author != user: 

		# Invalid request 

		return HttpResponseRedirect('view') 

	# Valid request 

	if request.method == 'POST': 

		# Check action 

		action = request.POST.get('action') 

		if action == 'Cancel': 

			# Cancel and return to list 

			return HttpResponseRedirect('view') 

		# Delete question 

		question.delete() 

		# Return with message 

		return HttpResponseRedirect('view?message={}'.format('delete_q_success')) 

	else:

		# Update context 

		args = {'user' : user, 'question' : question}  

		return render(request, 'question_delete.html', args) 

# Method to find all distinct genres from list 
@login_required
def find_all_genres(genre_list): 

	genre_set = [] 

	for genre in genre_list: 
		if genre['title'] is not None: 
			genre_set.append(genre['title'].strip())

	return set(genre_set)  

@login_required
def list_questions(request):

	author = request.user.username
	current_time = datetime.datetime.now(timezone.utc)

	print('Author = {}'.format(author))
	# Fetch all blogs 

	blogs = Post.objects.all().order_by('-time') 
	blogList = [] 

	# Fetch top rated users 

	top_rated_users = list(Profile.objects.all().order_by('-rating'))  
	top_rated_user_list = [None] * min(5, len(top_rated_users))

	i = 0
	for i in range(min(5, len(top_rated_users))): 

		top_rated_user_list[i] = top_rated_users[i]
		i += 1 

	print('Number of blog posts = ', len(blogs)) 

	for i in range(min(5, len(blogs))): 

		blogs[i].title = blogs[i].title.strip() 
		blogList.append(blogs[i]) 

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
					args = {'q_list' : q_list, 'g_list' : g_set, 'ques' : q, 'q_times' : question_times, 'author' : author, 'blogs' : blogList, 'top_rated_users': top_rated_user_list}
					return render(request, 'question_list_display_genre.html', args)

				else:

					args = {'q_list' : q_list, 'g_list' : g_set, 'ques' : q, 'author' : author, 'q_times' : question_times, 'blogs' : blogList,'top_rated_users': top_rated_user_list}
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
				'q_times' : question_times, 'author' : author, 'blogs' : blogList, 'top_rated_users': top_rated_user_list}
				return render(request, 'question_list_display_genre.html', args)

			else:

				args = {'q_list' : q_list, 'g_list' : g_set, 'top_rated_users': top_rated_user_list, 'ques' : q, 'comments' : comments, 'q_times' : question_times, 'author' : author, 'blogs' : blogList}
				return render(request, 'questions_list_display.html', args)	


		elif act == "Delete": 

			# Delete question 
			
			args = {'ques' : question, 'author' : author} 

			# return redirect('delete?q={}')

			return HttpResponseRedirect('delete_feed_question?question_id={}&user={}'.format(question.id, author)) 

		elif act == "Edit": 

			# Edit question 

			return HttpResponseRedirect('edit_feed_question?question_id={}&user={}'.format(question.id, author)) 

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
				'q_times' : question_times, 'author' : author, 'answer' : question.answer, 'top_rated_users': top_rated_user_list}
				return render(request, 'question_list_display_genre.html', args)

			else:

				args = {'q_list' : q_list, 'g_list' : g_set, 'ques' : q, 'q_times' : question_times, 
				'author' : author, 'answer' : question.answer, 'top_rated_users': top_rated_user_list}
				return render(request, 'questions_list_display.html', args)	

	else:

		# Designing an efficient Questions feed ranking system  

		query = request.GET.get('query')

		if query != None and query != ' ' and query != '':

			# Redirecting to search page

			return HttpResponseRedirect('search?query={}'.format(query))

		else:

			# Fetch all questions and rank them 

			question_list = list(Question.objects.all().order_by('-time'))
			
			# Fetch chosen genre from request object  

			genre = request.GET.get('genre')
		
			# All the genres of questions 
			
			genre_list = list(Question.objects.values('title')) 
			genre_set = find_all_genres(genre_list) 

			# Dictionary for time elapsed for every question  

			question_times = {}

			for elem in question_list:	
				question_times.update({elem.question : (current_time - elem.time).total_seconds() / 3600 })
			
			# Check if user has clicked on specific genre 

			if genre != None and genre != ' ':

				# Display genre questions 

				list_of_questions = list(Question.objects.filter(title = genre).order_by('-time'))
				genre_question_times = {} 

				# Update the question times for genre 

				for question in list_of_questions: 

					genre_question_times.update({question.question : (current_time - question.time).total_seconds() / 3600 })

				args = {'q_list' : list_of_questions, 'g_list' : genre_set, 'q_times' : genre_question_times, 'author' : author, 'blogs' : blogList, 'top_rated_users': top_rated_user_list}
				
				return render(request, 'question_list_display_genre.html', args)

			else:

				# Display generic questions feed 

				args = {'q_list' : question_list, 'g_list' : genre_set, 'q_times' : question_times, 'author' : author, 'blogs' : blogList, 'top_rated_users': top_rated_user_list}
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

# Method to edit a question 

@login_required
def edit_question(request): 

	# Fetch question and user data

	question_id = request.GET.get('question_id') 
	author = request.GET.get('user') 
	user = request.user 

	# Make a DB call 

	question = Question.objects.get(id = question_id) 
	author = User.objects.get(username = author) 

	# Check if valid request 

	if author != user: 

		# Invalid request 

		return HttpResponseRedirect('view') 

	# Valid request 

	if request.method == 'POST': 

		# Check action 

		action = request.POST.get('action') 

		if action == 'Cancel': 

			# Cancel and return to list 

			return HttpResponseRedirect('view') 

		# Extract data from request 

		title = request.POST.get('title') 
		content = request.POST.get('question')
		answer = request.POST.get('answer') 

		# Edit the question object 

		question.title = title 
		question.question = content 
		question.answer = question.answer 

		# Save object 

		question.save() 

		# Return with message 

		return HttpResponseRedirect('view?message={}'.format('edit_q_success')) 

	else:

		# Update context 

		args = {'user' : user, 'question' : question}  

		return render(request, 'question_edit_base.html', args) 


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