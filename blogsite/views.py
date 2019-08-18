#Importing libraries
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.db import models
from django.contrib.auth import login, authenticate
from django.contrib.auth import logout
from blogsite.forms import RegisterForm
from blogsite.models import Question
from django.dispatch import receiver
from django.contrib.auth.forms import AuthenticationForm
from django.http import HttpResponseRedirect
from .models import Comment, User
from django.contrib.auth.signals import user_logged_in, user_logged_out
import datetime
from datetime import timezone
# Create your views here.

def index(request):
	return render(request, 'index.html')

def homepage(request):

	username = request.GET.get('user')

	if username == None:
		return render(request, 'homepage.html', {'user' : request.user})
		

#Function for registering a user
def register(request):

	print('Control here.')

	if request.method == 'POST':
		form = RegisterForm(request.POST)
		print(form.errors)
		if form.is_valid:
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
			print('Form invalid?')
	else:

		form = RegisterForm()

	return render(request, 'register.html', {'form' : form})

#Function for logging in
def login_view(request):

	if request.user.is_authenticated:
		print('{} is already logged in.'.format(request.user.username))
		return render(request, 'homepage.html', {'user' : request.user})

	if request.method == 'POST':

		form = AuthenticationForm(request.POST)
		username = request.POST.get('username')
		passwd = request.POST.get('password')
		
		if form.is_valid:
			print('Logged in.')
			try:
				user = authenticate(username = username, password = passwd)
				login(request, user)
				next_page_url = 'home?username=' + username
				return redirect('home')
			except:
				print('Authentication error.')
				return render(request, 'login.html', {'form' : form, 'error' : 'Username/Password invalid'})
		else:
			print(form.errors)
	else:
		form = AuthenticationForm()

	return render(request, 'login.html', {'form' : form})

#Function for logging a person out
def logout_view(request):

	logout(request)
	return redirect('index')

def questions(request):

	return render(request, 'questions.html')

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
		q = Question(title = title, question = question, answer = answer, time = datetime.datetime.now(), author = request.user)
		q.save()

	return render(request, 'questions.html')

def load_comments(request, ques, comments):

	q_list = Question.objects.all().order_by('-time')
	genres = Question.objects.values('title')
	g = request.GET.get('genre')
	l = list(genres.values('title'))
	g_list = []
	for d in l:
		g_list.append(d['title'])
	g_set = set(g_list)
	#print(comments[0])
	if g != None and g != ' ':
		q_list = Question.objects.filter(title = g).order_by('-time')
		args = {'q_list' : q_list, 'g_list' : g_set, 'question' : ques, 'q_times' : question_times, 'comments' : comments}
		return render(request, 'question_list_display_genre.html', args)
	else:
		args = {'q_list' : q_list, 'g_list' : g_set, 'question' : ques, 'q_times' : question_times, 'comments' : comments}
		return render(request, 'questions_list_display.html', args)

def render_page(request):

	pass

def list_questions(request):

	author = request.user.username
	current_time = datetime.datetime.now(timezone.utc)

	if request.method == 'POST':

		act = request.POST.get('act')
		show = request.POST.get('show')
		
		#Getting details of question in context

		q = request.POST.get('questions')
		question = Question.objects.filter(question = q)[0]		
		q_list = Question.objects.all().order_by('-time')

		question_times = {}

		for elem in q_list:
			question_times.update({elem.question : (current_time - elem.time).total_seconds() / 3600 })

		#Displaying data according to act variable

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

		elif act == 'Load':

			comments = Comment.objects.filter(question = question).order_by('-time')

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

		else: 

			#Show answer to the question
			
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

			#Redirecting to search page

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
				args = {'q_list' : q_list, 'g_list' : g_set, 'q_times' : question_times}
				return render(request, 'question_list_display_genre.html', args)

			else:

				args = {'q_list' : q_list, 'g_list' : g_set, 'q_times' : question_times}
				return render(request, 'questions_list_display.html', args)

def add_comment(request):

	comm = request.POST.get('comment')
	ques = request.POST.get('questions')
	question = Question.objects.filter(question = ques)[0]

	if comm != None and comm != ' ' and comm != '':

		comment = Comment(content = comm, time = datetime.datetime.now(), author = request.user, question = question)
		comment.save()

def show_user(request):

	username = request.GET.get('user') 
	user = User.objects.get(username = username)
	print(user.first_name)
	current_time = datetime.datetime.now(timezone.utc)
	questions = Question.objects.filter(author = user).order_by('-time')
	print('Number of questions asked by {} = {}'.format(user.first_name, len(questions)))
	genre_lists = []
	question_list = []

	for question in questions:

		question_list.append(question)
		genre_lists.append(question.title)

	genre_lists = set(genre_lists)
	args = {'user' : user, 'q_list' : question_list, 'no_of_questions' : len(questions), 'genres' : genre_lists}

	if request.method == 'POST':

		#A question has been answered

		act = request.POST.get('act')
		show = request.POST.get('show')
		
		#Getting details of question in context

		q = request.POST.get('questions')
		question = Question.objects.filter(question = q)[0]		
		q_list = Question.objects.all().order_by('-time')

		question_times = {}

		for elem in q_list:
			question_times.update({elem.question : (current_time - elem.time).total_seconds() / 3600 })

		#Displaying data according to act variable

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

		elif act == 'Load':

			comments = Comment.objects.filter(question = question).order_by('-time')
			
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

			#Show answer to the question
			
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

	#Get user profile information
	return render(request, 'user_display.html', args)

def show_search(request):

	author = request.user.username
	current_time = datetime.datetime.now(timezone.utc)

	query = request.GET.get('query')

	#Defining data to pass to templates
	
	question_list = []
	question_times = {}

	#Searching for data

	questions = Question.objects.all()

	for element in questions:
		s = element.question 
		if s != None:
			if s.find(query) != -1:
				question_list.append(element)

	for elem in question_list:
		question_times.update({elem.question : (current_time - elem.time).total_seconds() / 3600 })

	#Show search results of questions

	if request.method == 'GET':

		if query != None and query != ' ' and query != '':

			#Redirect to search page
			print('Searching for {}'.format(query))

			return render(request, 'search_results.html', {'q_list' : question_list, 'q_times' : question_times})

		else:

			return render(request, 'search_results.html', {'q_list' : {}, 'q_times' : {}})

	else: 

		#Load/Submit comment or Show the answer

		act = request.POST.get('act')
		
		#Getting details of question in context

		q = request.POST.get('questions')
		question = Question.objects.filter(question = q)[0]

		#Taking action according to act variable

		if act == 'Submit':
			#Submit comment
			add_comment(request)
			args = {'q_list' : question_list, 'ques' : q, 'author' : author, 'q_times' : question_times}
			return render(request, 'search_results.html', args)

		elif act == 'Load':
			#Load comments
			comments = Comment.objects.filter(question = question).order_by('-time')
			args = {'q_list' : question_list, 'ques' : q, 'comments' : comments, 'q_times' : question_times, 'author' : author}
			return render(request, 'search_results.html', args)	

		else:
			#Show answer
			args = {'q_list' : question_list, 'ques' : q, 'answer' : question.answer, 'q_times' : question_times, 'author' : author}
			return render(request, 'search_results.html', args)

def search_users(request):

	user_name = request.GET.get('q')

	print('User to be searched = {}'.format(user_name))

	users_by_firstname = User.objects.all().filter(first_name = user_name)
	users_by_lastname = User.objects.all().filter(last_name = user_name)

	user_list = []

	for users in users_by_firstname:
		user_list.append(users)

	for users in users_by_lastname:
		user_list.append(users)

	print(user_list)

	return render(request, 'search_user_page.html', {'user_list' : user_list, 'query' : user_name})

#Receiver signals: to check whether user is logged in or not
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