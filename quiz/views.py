# Importing libraries

import difflib
from django.shortcuts import render
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.db import models
from django.contrib.auth import login, authenticate
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required 
from quiz.forms import QuizForm
from quiz.models import QuizQuestion, Contest, Submission
from .models import User 
from django.dispatch import receiver
from django.contrib.auth.forms import AuthenticationForm
from django.http import HttpResponseRedirect, JsonResponse
from django.contrib.auth.signals import user_logged_in, user_logged_out
import datetime, collections
from graphos.sources.simple import SimpleDataSource
from graphos.renderers.gchart import PieChart 
from django.core.files.storage import FileSystemStorage 
from django.db.models import Min, Max, Count, Q 
from functools import cmp_to_key 
from django.urls import reverse 
import pytz

# Class to represent custom data structure 

class ContestUser: 

	# Variables 

	def __init__(self, username, correct_answers, time_taken): 

		self.username = username 
		self.correct_answers = correct_answers
		self.time_taken = time_taken 

# Method to compare two users 

def compare(x): 

	return x.correct_answers, -x.time_taken 

# Create your views here.

# Method to redirect to homepage 

@login_required
def homepage(request): 

	user = request.user 

	user_contests = Contest.objects.filter(host = user) 
	all_contests = Contest.objects.all() 

	contests = [] 

	# Display only those contests who have all the questions done 

	for contest in all_contests: 

		questionCount = QuizQuestion.objects.filter(contest = contest).count() 

		if questionCount >= 10: 

			contests.append(contest) 

	# Update the context for this page 

	args = {'user_contests' : user_contests, 'contests' : contests}

	return render(request, 'quiz_homepage.html', args) 

# Method to add a question 

def add_question(question, contest, answer, image, second_answer, third_answer): 

	quiz_question = QuizQuestion(question = question, answer = answer, contest = contest, image = image, second_answer = second_answer, third_answer = third_answer)     

	quiz_question.save() 

	return quiz_question, 'OK' 

# Method to compare date  

def time_diff(contestTime, contest_id):

	# Fetch timezones

	utc_tz = pytz.timezone('UTC') 
	local_tz = pytz.timezone('Asia/Kolkata')

	# Contest time is string 

	contestTime = local_tz.localize(datetime.datetime.strptime(contestTime, '%Y-%m-%d %H:%M:%S'))
	currentTime = datetime.datetime.now(local_tz) 

	# Fetch contests ahead of time 

	contests = Contest.objects.filter(time__gt = currentTime) 

	# Initialize variables 

	validDate = 'YES' 
	message = 'Time is valid'

	# Check whether contest is in the past 

	if contestTime < currentTime: 

		validDate = 'NO' 
		message = 'Time is in the past' 

		return validDate, message 

	# Check if contest time is clashing with other contests 

	for contest in contests:

		distance = (contest.time - contestTime).total_seconds()

		print(contest.time, contestTime) 
	
		if distance < 0: 

			distance *= -1 

		distance_in_minutes = (distance/60) 

		if distance_in_minutes <= 15:

			if contest.id is not contest_id: 

				validDate = 'NO' 
				message = 'Time is clashing. Choose another time.' 
				
				return validDate, message

	# All OK 

	return validDate, message

# Method to check date validation 

def is_valid_date(request):

	# Fetch request data 

	user = request.user 
	contest_id = request.GET.get('contest_id') 

	# Initialize response 

	response = {} 

	if request.method == 'GET': 

		contestTime = request.GET.get('contestTime')
		contestTime += ':00'

		validDate, message = time_diff(contestTime = contestTime, contest_id = contest_id)  

		response['validDate'] = validDate
		response['message'] = message 

		return JsonResponse(response) 

	else: 

		return JsonResponse('') 

# Method to schedule a Quiz 

@login_required
def schedule_quiz(request): 

	user = request.user 

	if request.method == 'POST': 

		# Redirect to adding questions page 

		date = request.POST.get('date') 
		time = request.POST.get('time') 
		genre = request.POST.get('genre') 

		contestTime = date + ' ' + time + ':00'

		print(contestTime) 

		# Check whether date and time is valid

		validDate, message = time_diff(contestTime, contest_id = 0) 

		if validDate == 'NO': 

			print(validDate, message) 
			return HttpResponseRedirect('schedule?message={}'.format(message)) 

		# Save contest 

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

			# Fetcing answer from request data  

			answer = request.POST.get('answer') 
			second_answer = request.POST.get('second_answer')
			third_answer = request.POST.get('third_answer') 

			# Fetching image from request data 

			image = request.FILES.get('image')

			if image is not None: 

				# Assign image to profile 

				file_storage = FileSystemStorage() 
				filename = file_storage.save(image.name, image) 
				file_url = file_storage.url(filename) 

			question_object, msg = add_question(question = question, contest = contest, answer = answer, image = image, second_answer = second_answer, third_answer = third_answer) 

			return HttpResponseRedirect('contest?contest_id={}&message={}'.format(contest_id, msg)) 

		else:

			# Finish question 
			
			msg = is_valid_contest(contest) 

			if msg == 'OK': 

				return redirect('quiz_home') 

			else: 
			
				return HttpResponseRedirect('contest?contest_id={}&message={}'.format(contest_id, msg))


			return HttpResponseRedirect('contest?contest_id={}&message={}'.format(contest_id, msg)) 

	else: 

		message = request.GET.get('message') 

		if message is not None:

			args.update({'message' : message})
		
		msg = is_valid_contest(contest) 

		'''
		if msg == 'OK': 

			return HttpResponseRedirect('view_contest?contest_id={}'.format(contest_id)) 

		else: 

			return render(request, 'quiz_contest_base.html', args) 
		'''

		return render(request, 'quiz_contest_base.html', args) 

# Method to view a contest 

@login_required
def view_contest(request): 

	user = request.user 
	contest_id = request.GET.get('contest_id') 
	contest = Contest.objects.get(id = contest_id) 
	questions = QuizQuestion.objects.filter(contest = contest)

	args = {'user' : user, 'contest' : contest, 'questions' : questions}  

	if len(questions) > 0: 

		args['first_question'] = questions[0] 

	else:

		args['first_question'] = 'No questions yet.'

	submissions = Submission.objects.filter(user = user)

	flag = False 

	for submission in submissions: 

		print(user.username, submission.question.contest.id) 

		if submission.question.contest == contest: 

			# User has played contest 

			flag = True 

			break

	if flag == True:

		# User has played the contest 

		contest_submission = [] 
		correct_answer = 0 
		time_taken = 0 

		for submission in submissions: 

			if submission.question.contest == contest:

				quotient = similarity_quotient(submission.question.answer, submission.answer) 

				if is_correct(submission, submission.question): 

					# Correct answer 

					time_taken += submission.time_taken
					correct_answer += 1 
					contest_submission.append([submission.question.question, submission.answer, submission.question.answer, '1'])

				else: 

					# Incorrect answer 

					contest_submission.append([submission.question.question, submission.answer, submission.question.answer, '0'])

		args.update({'played_contest' : 'YES', 'submission' : contest_submission, 'correct_answers' : correct_answer, 'time_taken' : round(time_taken, 3)})

	else:

		args.update({'played_contest' : 'NO'})

	if contest.host == user: 

		# Show questions

		args.update({'show_questions' : 'YES'})

	else: 

		# Show contest details only 

		args.update({'show_questions' : 'NO'}) 

	return render(request, 'quiz_view_contest.html', args) 

# Method to edit contest (timing, genre)  

@login_required
def edit_contest(request): 

	# Fetch request data 

	username = request.GET.get('user') 
	contest_id = request.GET.get('contest_id') 
	logged_in_user = request.user 

	# Fetching user from DB 

	user = User.objects.get(username = username) 

	# Check if user is logged in 

	if user != logged_in_user: 

		# Bad request 

		return HttpResponseRedirect('view_contest?contest_id={}&msg={}'.format(contest_id, 'bad_request'))

	# Fetch contest object from DB 
	
	contest = Contest.objects.get(id = contest_id) 

	# If contest has been played 

	current_date_time = datetime.datetime.now(pytz.timezone('Asia/Kolkata'))  
	contest_date_time = contest.time 

	distance = contest_date_time - current_date_time

	print(distance) 

	if contest_date_time < current_date_time: 

		# Cannot edit it again 

		return HttpResponseRedirect('view_contest?contest_id={}&msg={}'.format(contest_id, 'contest_past')) 

	# Populate context 

	args = {'user' : user, 'contest' : contest}  

	# Proceed to handle request 

	if request.method == 'POST': 

		# Fetch form data 

		genre = request.POST.get('genre') 
		time = request.POST.get('time') 
		date = request.POST.get('date') 

		# TODO: Check if timings clash

		# Edit operation 

		contest.genre = genre
		contest.time = date + ' ' +  time  

		# Save edits 

		contest.save() 

		# Redirect with acknowledgement 

		return HttpResponseRedirect('view_contest?contest_id={}&msg={}'.format(contest_id, 'edit_success'))
	
	else: 

		return render(request, 'quiz_edit_contest.html', args) 

# Method to edit question 

@login_required
def edit_question(request): 

	# Fetch request data 

	user = request.user 
	question_id = request.GET.get('question_id') 

	# Fetch data with a DB call 

	question = QuizQuestion.objects.get(id = question_id) 
	contest = Contest.objects.get(id = question.contest.id) 

	# Defining context for the page 

	args = {'user' : user, 'question' : question, 'contest' : contest}

	# Check if user is author 

	if user != question.contest.host: 

		url = reverse('quiz_home')
		return HttpResponseRedirect(url) 

	if request.method == 'POST': 

		# Check if question is valid 

		question_content = request.POST.get('question') 
		image = request.FILES.get('image') 		
		answer = request.POST.get('answer') 
		second_answer = request.POST.get('second_answer') 
		third_answer = request.POST.get('third_answer') 

		# Edit the question

		question.question = question_content 
		question.answer = answer 
		question.second_answer = second_answer
		question.third_answer = third_answer

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
	answer = question.answer 

	# Get contest id 

	contest_id = question.contest.id 

	# Check if user is author 

	if user != question.contest.host: 

		url = reverse('quiz_home')
		return HttpResponseRedirect(url) 

	# Update context 

	args = {'user' : user, 'question' : question, 'contest_id' : contest_id, 'answer' : answer} 

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

		if i < len(questions) - 1:
		
			submission = Submission.objects.filter(user = user, question = questions[i + 1]) 

		if questions[i].id == question.id and len(submission) == 0: 

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

# Method to check whether answer is correct 

def is_correct(submission, question): 

	# Fetching given and correct answers 

	submitted_answer = submission.answer 
	correct_answer = question.answer 

	# Fetching other accepted answers 

	answer1 = question.second_answer 
	answer2 = question.third_answer 

	# Check with original answer 

	if similarity_quotient(submitted_answer, correct_answer) >= 0.85: 

		return True 

	if len(answer1) > 0 and similarity_quotient(submitted_answer, answer1) >= 0.85: 

		return True 

	if len(answer2) > 0 and similarity_quotient(submitted_answer, answer2) >= 0.85: 

		return True 

	# Answer does not match with anything 

	return False 

# Method to return similarity of two strings 

def similarity_quotient(str1, str2): 

	# Convert everything to lower case 

	str1 = str1.lower()
	str2 = str2.lower() 

	# Compute similarity

	similarity = difflib.SequenceMatcher(None, str1, str2).ratio() 

	print(str1, str2, similarity) 

	return similarity

@login_required
def play_contest(request): 

	# Fetch data from request 

	user = request.user 
	question_id = request.GET.get('question_id')
	contest_id = request.GET.get('contest_id') 
	instruction = request.GET.get('instruction') 

	# Fetch data from database call 

	contest = Contest.objects.get(id = contest_id) 
	question = QuizQuestion.objects.get(id = question_id) 
	submissions = Submission.objects.filter(user = user, question = question) 
	contest_questions = QuizQuestion.objects.filter(contest = contest) 

	# TODO: If it has been ten minutes since contest started - leave 
	
	if len(submissions) == len(contest_questions): 

		return redirect('quiz_home') 

	index = len(submissions) 

	question = contest_questions[index] 

	args = {'user' : user, 'question' : question, 'contest' : contest} 

	if request.method == 'POST': 

		# Fetch request data 

		answer = request.POST.get('answer') 
		question_id = request.GET.get('question_id') 
		time_taken = request.POST.get('time_taken') 

		time_taken = int(time_taken) / 1000

		if answer == None: 

			answer = "" 

		# Fetch question 

		question = QuizQuestion.objects.get(id = question_id) 

		# Check if user has submitted this question before 

		submissions = Submission.objects.filter(user = user, question = question) 

		if len(submissions) == 0:

			# Create submission object 

			submission = Submission(user = user, question = question, answer = answer, time_taken = time_taken) 
			submission.save() 

		# Route to next question 

		message, next_question = fetch_next_question(question, user) 

		if message == 'FINISH': 

			return render(request, 'quiz_exit_window.html', args) 

		else:

			# Update context

			args['question'] = next_question

			return render(request, 'quiz_play_contest.html', args) 

	else: 

		if instruction == 'show': 

			# Updating arguments 

			args['contest_id'] = contest_id
			args['question_id'] = question_id

			questions = QuizQuestion.objects.filter(contest = contest_id)

			args['no_of_questions'] = len(questions)

			return render(request, 'quiz_contest_instructions.html', args) 

		else: 

			return render(request, 'quiz_play_contest.html', args) 

# Method to return a list of users which participated in the contest 
	
def users_in_contest(contest): 

	users_set = set([]) 

	submissions = Submission.objects.filter(question__contest = contest)  

	for submission in submissions: 

		users_set.add(submission.user) 

	return users_set 

# Method to return leaderboard for a contest 

@login_required
def display_leaderboard(request): 

	# Fetch required data 

	original_user = request.user 
	contest_id = request.GET.get('contest_id') 
	contest = Contest.objects.get(id = contest_id) 

	#submisssions = Submission.objects.get(contest = contest) 

	# Design leaderboard from submissions 

	contest_users = [] 

	users = users_in_contest(contest) 

	for user in users: 

		user_submissions = Submission.objects.filter(question__contest = contest, user = user) 

		correct_answers = 0 
		time_taken = 0 

		for submission in user_submissions: 

			given_answer = submission.answer.lower() 
			correct_answer = submission.question.answer.lower() 

			if is_correct(submission, submission.question): 

				correct_answers += 1 
				time_taken += submission.time_taken 


		contest_user = ContestUser(user.username, correct_answers, time_taken) 
		contest_users.append(contest_user) 

	# Sort the submissions

	contest_users = sorted(sorted(contest_users, key = lambda x: x.time_taken), key = lambda x: x.correct_answers, reverse = True)  
	
	for user in contest_users: 

		print(user.username, user.correct_answers, user.time_taken) 

	# Update context 

	args = {} 

	args.update({'user' : original_user, 'contest' : contest, 'users' : contest_users})

	return render(request, 'quiz_display_leaderboard.html', args) 
