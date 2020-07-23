# Importing libraries

from django.shortcuts import render
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.db import models
from django.contrib.auth import login, authenticate
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required 
from quiz.forms import QuizForm
from quiz.models import QuizQuestion, Contest, Submission
from django.dispatch import receiver
from django.contrib.auth.forms import AuthenticationForm
from django.http import HttpResponseRedirect, JsonResponse
from django.contrib.auth.signals import user_logged_in, user_logged_out
import datetime, collections
from datetime import timezone
from graphos.sources.simple import SimpleDataSource
from graphos.renderers.gchart import PieChart 
from django.core.files.storage import FileSystemStorage 

# Create your views here.

# Method to redirect to homepage 

def homepage(request): 

	user = request.user 

	user_contests = Contest.objects.filter(host = user) 

	# Update the context for this page 

	args = {'user_contests' : user_contests}

	return render(request, 'quiz_homepage.html', args) 

# Method to add a question 

def add_question(question, options, contest, answer, image): 

	quiz_question = QuizQuestion(question = question, options = options, answer = answer, contest = contest, image = image)    

	quiz_question.save() 

	return quiz_question, 'OK' 

# Method to schedule a Quiz 

def schedule_quiz(request): 

	user = request.user 

	if request.method == 'POST': 

		# Redirect to adding questions page 

		date = request.POST.get('date') 
		time = request.POST.get('time') 
		genre = request.POST.get('genre') 

		contest = Contest(host = user, genre = genre, time = date + ' ' + time) 

		contest.save() 

		contest_id = contest.id 

		return HttpResponseRedirect('contest?contest_id={}'.format(contest_id)) 

	else:

		return render(request, 'quiz_schedule.html') 

# Method to check if a contest is valid or not 

def is_valid_contest(contest): 

	questions = QuizQuestion.objects.filter(contest = contest) 

	no_of_questions = len(questions) 

	if no_of_questions < 10: 

		return 'INVALID_LESSQUESTIONS'

	return 'OK'

# Method to add questions to a contest 

@login_required
def create_contest(request): 

	# Getting user and contest ID 

	user = request.user 

	contest_id = request.GET.get('contest_id') 

	# DB call to fetch contest 

	args = {'user' : user, 'id' : contest_id} 

	contest = Contest.objects.get(id = contest_id) 

	if request.method == 'POST': 

		action = request.POST.get('action') 

		if action == 'Add question': 

			# Add question 

			question = request.POST.get('question') 

			# Fetching options from request data 

			option_1 = request.POST.get('option_1') 
			option_2 = request.POST.get('option_2') 
			option_3 = request.POST.get('option_3') 
			option_4 = request.POST.get('option_4') 

			# Fetcing answer from request data  

			answer = request.POST.get('answer') 

			# Fetching image from request data 

			image = request.FILES.get('image')

			if image is not None: 

				# Assign image to profile 

				file_storage = FileSystemStorage() 
				filename = file_storage.save(image.name, image) 
				file_url = file_storage.url(filename) 

			options = option_1 + ',' + option_2 + ',' + option_3 + ',' + option_4

			question_object, msg = add_question(question = question, contest = contest, options = options, answer = answer, image = image) 

			return HttpResponseRedirect('contest?contest_id={}&message={}'.format(contest_id, msg)) 

		else:

			# Finish question 

			# Check if number of questions are 20 

			msg = is_valid_contest(contest) 

			if msg == 'OK': 

				return redirect('quiz_home') 

			else: 

				return HttpResponseRedirect('contest?contest_id={}&message={}'.format(contest_id, msg)) 

	else: 

		message = request.GET.get('message') 

		if message is not None:

			args.update({'message' : message})
		
		msg = is_valid_contest(contest) 

		if msg == 'OK': 

			return HttpResponseRedirect('view_contest?contest_id={}'.format(contest_id)) 

		else: 

			return render(request, 'quiz_contest_base.html', args) 


# Method to view a contest 

@login_required
def view_contest(request): 

	user = request.user 

	contest_id = request.GET.get('contest_id') 

	contest = Contest.objects.get(id = contest_id) 

	questions = QuizQuestion.objects.filter(contest = contest)

	args = {'user' : user, 'contest' : contest, 'questions' : questions, 'first_question' : questions[0]}  

	if contest.host == user: 

		# Show questions

		args.update({'show_questions' : 'YES'})

	else: 

		# Show contest details only 

		args.update({'show_questions' : 'NO'}) 

	return render(request, 'quiz_view_contest.html', args) 


# Method to edit question 

@login_required
def edit_question(request): 

	user = request.user 

	question_id = request.GET.get('question_id') 

	question = QuizQuestion.objects.get(id = question_id) 

	contest = Contest.objects.get(id = question.contest.id) 

	# Unpacking options 

	option_1 = question.option_list[0] 
	option_2 = question.option_list[1]
	option_3 = question.option_list[2] 
	option_4 = question.option_list[3] 

	# Defining context for the page 

	args = {'user' : user, 'question' : question, 'contest' : contest, 'option_1' : option_1, 'option_2' : option_2, 'option_3' : option_3, 'option_4' : option_4}

	if request.method == 'POST': 

		# Check if question is valid 

		question_content = request.POST.get('question') 

		option_1 = request.POST.get('option_1') 
		option_2 = request.POST.get('option_2') 
		option_3 = request.POST.get('option_3') 
		option_4 = request.POST.get('option_4') 

		image = request.FILES.get('image') 
		
		answer = request.POST.get('answer') 

		options = option_1 + ',' + option_2 + ',' + option_3 + ',' + option_4

		# Validation check 

		# Edit the question

		question.question = question_content 

		question.options = options 

		question.answer = answer 

		if image is not None: 

			question.image = image

		# Save the question 

		question.save() 

		return HttpResponseRedirect('view_contest?contest_id={}'.format(question.contest.id))  

	else: 

		return render(request, 'quiz_edit_question.html', args)  


# Method to delete a question 

@login_required
def delete_question(request): 

	user = request.user 
	question_id = request.GET.get('question_id') 

	# Fetch question from database 

	question = QuizQuestion.objects.get(id = question_id) 

	option_1 = question.option_list[0] 
	option_2 = question.option_list[1]
	option_3 = question.option_list[2] 
	option_4 = question.option_list[3] 

	# Get contest id 

	contest_id = question.contest.id 

	# Update context 

	args = {'user' : user, 'question' : question, 'contest_id' : contest_id, 'option_1' : option_1, 'option_2' : option_2, 'option_3' : option_3, 'option_4' : option_4} 

	if request.method == 'POST': 

		action = request.POST.get('action') 

		if action == 'Confirm delete': 

			# Delete the question  

			question.delete() 

		return HttpResponseRedirect('view_contest?contest_id={}'.format(contest_id)) 

	else: 

		return render(request, 'quiz_delete_question.html', args) 


# Method to fetch next question 

def fetch_next_question(question, user): 

	contest = question.contest 

	questions = QuizQuestion.objects.filter(contest = contest)  

	# Find questions which have already been submitted by user 

	for i in range(len(questions)): 

		if questions[i].id == question.id: 

			break 

	if i == len(questions) - 1: 

		# Contest finished

		message = 'FINISH' 
		next_question = None

	else: 

		# Contest is on

		message = 'CONTINUE'
		next_question = questions[i + 1]  

	return message, next_question 


@login_required
def play_contest(request): 

	# Fetch data from request 

	user = request.user 
	question_id = request.GET.get('question_id')
	contest_id = request.GET.get('contest_id') 

	contest = Contest.objects.get(id = contest_id) 

	# Fetch data from database call 

	question = QuizQuestion.objects.get(id = question_id) 

	args = {'user' : user, 'question' : question, 'options' : question.option_list, 'contest' : contest} 

	if request.method == 'POST': 

		# Fetch request data 

		answer = request.POST.get('answer') 
		question_id = request.GET.get('question_id') 
		time_taken = request.POST.get('time_taken') 

		# Fetch question 

		question = QuizQuestion.objects.get(id = question_id) 

		# Create submission object 

		submission = Submission(user = user, question = question, answer = answer, time_taken = time_taken) 
		submission.save() 

		# Route to next question 

		message, next_question = fetch_next_question(question, user) 

		if message == 'FINISH': 

			return redirect('quiz_home') 

		else:

			# Update context

			args['question'] = next_question
			args['options'] = next_question.option_list 

			return render(request, 'quiz_play_contest.html', args) 

	else: 

		return render(request, 'quiz_play_contest.html', args) 

