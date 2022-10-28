# Importing libraries

import difflib
from django.shortcuts import render
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.db import models
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import login, authenticate
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required 
from quiz.forms import QuizForm
from quiz.models import QuizQuestion, Contest, Submission, RatingHistory, Leaderboard
from blogsite.models import Profile
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
import codecs
import io
import csv
from quiz.rating_system import update_rating

# Class to represent custom data structure 

class ContestUser: 

	# Variables 

	def __init__(self, username, correct_answers, time_taken): 

		self.username = username 
		self.correct_answers = correct_answers
		self.time_taken = time_taken 

# Class to represent user, rank, old rating and new rating 

class RatingUser: 

	def __init__(self, username, rank, correct_answers, old_rating, new_rating): 

		self.username = username
		self.rank = rank
		self.correct_answers = correct_answers
		self.old_rating = old_rating
		self.new_rating = new_rating

# Method to compare two users 

def compare(x): 

	return x.correct_answers, -x.time_taken 

# Method to redirect to homepage 

@login_required
def homepage(request): 

	# Fetch all contests 

	user = request.user 
	user_contests = Contest.objects.filter(host = user) 
	all_contests = Contest.objects.all() 

	# Contests 

	contests = [] 
	past_contests = [] 
	new_contests = [] 
	active_contests = [] 

	current_time = datetime.datetime.now(pytz.timezone('UTC')) 
	
	# Fetching new and past contests  
	for contest in all_contests.order_by('-time'): 

		question_count = QuizQuestion.objects.filter(contest = contest).count() 

		# Append to active contests 
		time_difference = (contest.time - current_time).total_seconds() 
		time_difference /= 60 
		time_difference *= -1

		print(time_difference) 

		if time_difference >= 0 and time_difference <= contest.valid_for and question_count >= 10: 
			active_contests.append(contest) 

		elif time_difference >= 0 and time_difference > contest.valid_for and question_count >= 10: 
			past_contests.append(contest) 
	
	for contest in all_contests.filter(time__gt = current_time).order_by('time'): 

		question_count = QuizQuestion.objects.filter(contest = contest).count() 
		
		if question_count >= 10: 
			new_contests.append(contest)

	# Display only those contests who have all the questions done 
	for contest in all_contests: 
		questionCount = QuizQuestion.objects.filter(contest = contest).count() 
		if questionCount >= 10: 
			contests.append(contest) 

	# Update the context for this page 
	args = {'new_contests' : new_contests, 'active_contests' : active_contests, 
			'past_contests' : past_contests, 'user_contests' : user_contests, 
			'contests' : contests, 'new_contests_size' : len(new_contests),
			'active_contests_size' : len(active_contests)}

	return render(request, 'quiz_homepage.html', args) 

# Method to add a question 
def add_question(question, contest, answer, image, second_answer, third_answer): 

	quiz_question = QuizQuestion(question = question, answer = answer, contest = contest, 
	image = image, second_answer = second_answer, third_answer = third_answer)     
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
		valid_for = request.POST.get('valid-for') 
		time_per_question = request.POST.get('seconds-per-question') 
		tsv_file = request.FILES.get('tsv-question-file') 

		contestTime = date + ' ' + time + ':00'

		# Check whether date and time is valid
		validDate, message = time_diff(contestTime, contest_id = 0) 

		if validDate == 'NO': 

			print(validDate, message) 
			return HttpResponseRedirect('schedule?message={}'.format(message)) 

		# Save contest 
		contest = Contest(host = user, genre = genre, time = date + ' ' + time, valid_for = int(valid_for), time_per_question = int(time_per_question)) 

		# Persist to database
		contest.save() 
		contest_id = contest.id 

		# Parse the questions if file is present
		if tsv_file is not None: 

			# Add questions from tsv file 
			result, err = parse_csv_file(contest, tsv_file)  
			
			if result == True:
				print('Successfully inserted questions from TSV!') 
			else: 
				print("Exception has occurred") 

		return HttpResponseRedirect('view_contest?contest_id={}'.format(contest_id)) 

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
# Name it better
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
					correct_subs, total_subs = fetch_question_attempts_accuracy(submission.question)
					contest_submission.append([submission.question.question, submission.answer, submission.question.answer, '1', 
					correct_subs, total_subs])

				else: 

					# Incorrect answer 
					correct_subs, total_subs = fetch_question_attempts_accuracy(submission.question)
					contest_submission.append([submission.question.question, submission.answer, submission.question.answer, '0',
					correct_subs, total_subs])

		args.update({'played_contest' : 'YES', 'submission' : contest_submission, 
		'correct_answers' : correct_answer, 'time_taken' : round(time_taken, 3)})

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
		valid_for = request.POST.get('valid-for') 
		time_per_question = request.POST.get('seconds-per-question')
		csv_file = request.FILES.get('tsv-question-file') 

		# TODO: Check if timings clash

		# Edit operation 
		contest.genre = genre
		contest.time = date + ' ' +  time 
		contest.valid_for = int(valid_for) 
		contest.time_per_question = request.POST.get('seconds-per-question')

		# Save edits 
		contest.save() 

		# Parse the questions if file is present
		if csv_file is not None: 

			# Add questions from tsv file 
			result, err = parse_csv_file(contest, tsv_file)  
			if result == True:
				print('Successfully inserted questions from TSV!') 
			else:
				print("Exception has occurred") 
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

	# Check if they are invalid
	if question_id is None or contest_id is None:
		return redirect('quiz_home') 

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

		# Pre-process incoming data
		if answer == None: 
			answer = "" 

		if time_taken == None: 
			time_taken = 0

		time_taken = int(time_taken) / 1000

		# Fetch question 
		question = QuizQuestion.objects.get(id = question_id) 

		# Check if user has submitted this question before 
		submissions = Submission.objects.filter(user = user, question = question) 

		if len(submissions) == 0:

			# Create submission object 
			submission = Submission(user = user, question = question, 
			answer = answer, time_taken = time_taken) 
			submission.save() 

		# Route to next question 
		message, next_question = fetch_next_question(question, user) 

		if message == 'FINISH': 

			# Add user game to leaderboard
			add_player_to_leaderboard(user, contest) 
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
			args['contest'] = contest 
			
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
	contest = Contest.objects.get(id = int(contest_id))

	questions = list(QuizQuestion.objects.filter(contest = contest)) 

	# Design leaderboard from submissions 
	contest_users = [] 
	users = users_in_contest(contest) 
	
	for user in users: 

		leaderboard_entry = list(Leaderboard.objects.filter(contest=contest, user=user)) 

		if len(leaderboard_entry) == 1: 

			print('Reading data straight from table') 
			contest_user = ContestUser(user.username, leaderboard_entry[0].correct_answers, 
			leaderboard_entry[0].time_taken) 
			contest_users.append(contest_user) 

			# Updating rating history
			try: 		
			
				rating_history = RatingHistory.objects.get(contest=contest, user=user) 
				rating_history.rating_before_contest = Profile.objects.get(user__username=user.username).rating
				rating_history.save() 

			except RatingHistory.DoesNotExist: 
				
				old_rating = Profile.objects.get(user__username=user.username).rating
				rating_history = RatingHistory(contest=contest, user=user, 
				rating_before_contest=old_rating) 
				rating_history.save() 

		else: 

			# This code will run only once
			print('About to calculate user performance')
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

			# Delete all the leaderboard entries first 
			for entry in leaderboard_entry: 
				entry.delete() 

			# Adding to leaderboard table
			user_from_db = User.objects.get(username=user.username)
			leaderboard_entry = Leaderboard(user=user_from_db, correct_answers=correct_answers, 
			time_taken=time_taken, contest=contest) 
			leaderboard_entry.save() 

			# Updating rating history 
			try: 
			
				rating_history = RatingHistory.objects.get(contest=contest, user=user) 
				rating_history.rating_before_contest = Profile.objects.get(user__username=user.username).rating
				rating_history.save() 

			except RatingHistory.DoesNotExist: 
				
				old_rating = Profile.objects.get(user__username=user.username).rating
				rating_history = RatingHistory(contest=contest, user=user, 
				rating_before_contest=old_rating) 
				rating_history.save() 


	# Sort the submissions
	contest_users = sorted(sorted(contest_users, key = lambda x: x.time_taken), key = lambda x: x.correct_answers, reverse = True)  

	# Update context 
	args = {} 
	args.update({'user' : original_user, 'contest' : contest, 'users' : contest_users})
	return render(request, 'quiz_display_leaderboard.html', args) 

# Method to fetch number of contests user has played from certan contest
def fetch_no_of_contests_played(start_contest_id, username):

	submission_list = Submission.objects.filter(user__username = username, question__contest__id__gt = start_contest_id - 1)
	list_of_contest_ids = [] 

	for submission in submission_list: 
		list_of_contest_ids.append(submission.question.contest.id) 

	return len(set(list_of_contest_ids)) 

# Method to update rankings for contest user 
def update_ratings(request): 

	# Check if contest is invalid
	response = {} 

	if request.method == 'GET': 

		# Fetch request data
		contest_id = request.GET.get('contest_id') 
		contest = Contest.objects.get(id = int(contest_id)) 

		print(contest_id) 

		# Check if contest needs some update
		if contest.has_rating_updated == True: 

			print('Contest ratings have already been updated') 
			return display_leaderboard(request) 

		if request.user.username != 'Avinash': 

			return display_leaderboard(request) 


		current_time = datetime.datetime.now(pytz.timezone('UTC')) 

		# Append to active contests 
		time_difference = (contest.time - current_time).total_seconds() 
		time_difference /= 60 
		time_difference *= -1

		if time_difference <= contest.valid_for: 

			response.update({'success': 'false', 'message': 'Contest is still going on'})
			return JsonResponse(response) 

		# Fetch the leaderboard 
		contest_users = [] 
		users = users_in_contest(contest) 

		for user in users: 

			is_user_present = list(Leaderboard.objects.filter(contest_id=contest.id, user_id=user.id)) 

			if is_user_present is not None: 

				# Ideally, there should only be one 
				# entry in the leaderboard 
				no_of_entries = len(is_user_present) 
				if no_of_entries > 0: 

					print('Leaderboard entries for ', user.username, ' = ', no_of_entries) 
					# Delete all other entries 
					# except the last one 
					if no_of_entries > 1: 

						if no_of_entries >= 2:
							leaderboard_entries_deleted = list(is_user_present)[0 : no_of_entries - 2]
						else:
							leaderboard_entries_deleted = list(is_user_present)[0] 

						for entry in leaderboard_entries_deleted: 
							entry.delete() 
					else:

						is_user_present_single = is_user_present[0] 
			else:

				# Add them to leaderboard
				add_player_to_leaderboard(user, contest) 
				is_user_present_single = list(Leaderboard.objects.filter(contest_id=contest.id, user_id=user.id))[0] 

			print('is_user_present', is_user_present_single)
			
			if type(is_user_present_single) == list:  
				contest_user = ContestUser(user.username, is_user_present_single[0].correct_answers, is_user_present_single[0].time_taken) 
			else:
				contest_user = ContestUser(user.username, is_user_present_single.correct_answers, is_user_present_single.time_taken) 

			contest_users.append(contest_user) 

		# Sort the submissions
		contest_users = sorted(sorted(contest_users, key = lambda x: x.time_taken), key = lambda x: x.correct_answers, reverse = True)  
		rankings = []
		rank = 0
		correct_answer_array = []
		rating_array = []
		volatility_array = []
		question_ratings = [] 
		no_of_contests_played = [] 

		# Fetch question levels 
		questions = QuizQuestion.objects.filter(contest = contest) 
		question_score = [0] * len(list(QuizQuestion.objects.filter(contest = contest)))
		differential_score_array = [] 

		# Fetch number of people who played the contest
		print(contest.id)
		no_of_contest_players = len(list(Leaderboard.objects.filter(contest__id=contest.id))) 
		print('No of people who played this contest =', no_of_contest_players) 

		i = 0 

		for user in contest_users: 

			if user.correct_answers != 0: 
				rank = rank+1
			else:
				rank = no_of_contest_players

			rankings.append(rank)
			print(user.username, user.correct_answers, user.time_taken) 
			
			# Adding to leaderboard
			user_from_db = User.objects.get(username=user.username) # This is from user table
			# TODO: Handling bugs with multiple leaderboard entries for 
			# one contest and one user 
			leaderboard_entries = list(Leaderboard.objects.filter(user = user_from_db, contest = contest)) 
			entries_size = len(leaderboard_entries) 
			leaderboard_entry = leaderboard_entries[entries_size - 1] 
			print('Leaderboard entries', entries_size) 

			if entries_size > 1: 
				# Delete rest of them 
				leaderboard_entries = leaderboard_entries[0 : entries_size - 1] 
				for entry in leaderboard_entries: 
					# Delete 
					print('Deleting', entry.id) 
					entry.delete() 

			else: 
				# Only one entry, no problem 
				leaderboard_entry = leaderboard_entries[0] 

			leaderboard_entry = Leaderboard.objects.get(user=user_from_db, contest=contest)

			if leaderboard_entry.rank == 0: 

				# Save only when necessary
				leaderboard_entry.rank = rank
				leaderboard_entry.save() 

			correct_answer_array.append(user.correct_answers)

			# Updating ratings and volatility
			try:

				rating_history = RatingHistory.objects.get(contest = contest, user__username = user.username) 
				old_rating = rating_history.rating_before_contest

			except RatingHistory.DoesNotExist: 

				old_rating = Profile.objects.get(user__username = user.username).rating

			rating_array.append(old_rating) 
			volatility_array.append(Profile.objects.get(user__username = user.username).volatility)
			no_of_contests_played.append(Profile.objects.get(user__username = user.username).no_of_contests_played)  

			i = 0
			for question in list(QuizQuestion.objects.filter(contest = contest)): 

				try:
					submission = Submission.objects.get(user__username = user.username, question = question) 
					if is_correct(submission, question): 
						question_score[i] += 1 

					i += 1

				except Submission.DoesNotExist:
					print('Submission does not exist') 

		# Updating differential score 
		for user in contest_users:

			differential_score = 0 
			i = 0

			for question in list(QuizQuestion.objects.filter(contest = contest)): 

				try: 
					submission = Submission.objects.get(user__username = user.username, question = question) 

					if is_correct(submission, question): 
						differential_score += (1 - (question_score[i] / len(contest_users)))

					i += 1

				except Submission.DoesNotExist: 
					print('Submission does not exist')  

			differential_score_array.append(differential_score) 

		new_rating, new_volatility = update_rating(rating_array, volatility_array, rankings, 
		correct_answer_array, len(rating_array), no_of_contests_played) 

		i = 0 
		delta = 0 
		sum_of_old_rating = 0 
		sum_of_new_rating = 0 
		rated_users = [] 

		for user in contest_users: 

			try: 

				rating_history = RatingHistory.objects.get(contest = contest, user__username = user.username) 
				old_rating = rating_history.rating_before_contest

			except RatingHistory.DoesNotExist: 

				old_rating = Profile.objects.get(user__username = user.username).rating
			
			sum_of_old_rating += old_rating

			print('Old rating: ', old_rating) 
			print('Rank: ', rankings[i]) 
			print('Differential score: ', differential_score_array[i])
			print('New rating: ', (new_rating[i]))
			print('Contest played: ', no_of_contests_played[i])

			delta += (new_rating[i]) - Profile.objects.get(user__username = user.username).rating

			# Updating rating 
			user_profile = Profile.objects.get(user__username = user.username)
			user_profile.rating = new_rating[i]
			user_profile.volatility = new_volatility[i] 
			user_profile.save() 
	
			rated_user = RatingUser(user.username, rankings[i], user.correct_answers, rating_array[i], new_rating[i]) 
			rated_users.append(rated_user) 

			try: 

				rating_history = RatingHistory.objects.get(contest = contest, user__username = user.username) 
				rating_history.rating = new_rating[i]
				rating_history.save() 

			except RatingHistory.DoesNotExist: 
				
				user_object = User.objects.get(username=user.username) 
				rating_history = RatingHistory(contest=contest, user=user_object, 
				rating=new_rating[i], rating_before_contest=old_rating) 
				rating_history.save() 
			
			i += 1
		
		for user in contest_users: 

			user_profile = Profile.objects.get(user__username = user.username)
			sum_of_new_rating += user_profile.rating 
		
		response.update({'success' : 'true'})
		response.update({'users' : rated_users})
		response.update({'contest': contest})

		# Updating the contest
		contest.has_rating_updated = True
		contest.save() 

		print('Sum of ratings before contest: ', sum_of_old_rating) 
		print('Sum of ratings after contest: ', sum_of_new_rating) 
		print('Average rating (Old): ', sum_of_old_rating / (len(contest_users))) 
		print('Average rating (New): ', sum_of_new_rating / (len(contest_users)))
		print('Old rating \t New rating') 

		i = 0 

		for user in contest_users: 

			user_profile = Profile.objects.get(user__username = user.username) 
			print(rating_array[i], '\t', user_profile.rating)
			i += 1

		return render(request, 'quiz_updated_ratings.html', response) 

	else: 

		return JsonResponse(response) 

# Method to add players to the leaderboard
def add_player_to_leaderboard(user, contest): 

	user_submissions = Submission.objects.filter(question__contest = contest, user = user) 
	correct_answers = 0 
	time_taken = 0 

	for submission in user_submissions: 

		given_answer = submission.answer.lower() 
		correct_answer = submission.question.answer.lower() 

		if is_correct(submission, submission.question): 

			correct_answers += 1 
			time_taken += submission.time_taken 

	print(user.username, contest.id, correct_answers, time_taken) 

	# Check if already present before making inserts
	already_present = Leaderboard.objects.filter(contest = contest, user = user) 

	if len(list(already_present)) > 0: 

		leaderboard_entry = list(already_present)[0] 
		leaderboard_entry.correct_answers = correct_answers
		leaderboard_entry.time_taken = time_taken 
		leaderboard_entry.save()

	else:

		leaderboard_entry = Leaderboard(contest=contest, user=user, 
		correct_answers=correct_answers, time_taken=time_taken) 
		leaderboard_entry.save() 

# Method to restore ratings for this contest 
@login_required
def restore_ratings(request): 

	if request.method == 'GET': 

		contest_id = int(request.GET.get('contest_id'))  
		contest = Contest.objects.get(id=contest_id) 
		contest.has_rating_updated = False
		contest.save()
		
		# For every user on the leaderboard, update profile
		leaderboard = list(Leaderboard.objects.filter(contest=contest)) 

		for entry in leaderboard: 

			user = User.objects.get(username=entry.user.username) 
			rating_history = RatingHistory.objects.get(contest=contest, user=user) 
			user_profile = Profile.objects.get(user__username=user.username) 
			user_profile.rating = rating_history.rating_before_contest
			user_profile.save() 

		return display_leaderboard(request)

	else:

		return display_leaderboard(request) 

"""
	Method to view question analytics
"""
@login_required
def view_question_analytics(request): 

	if request.method == 'GET': 

		contest_id = int(request.GET.get('contest_id'))
		contest = Contest.objects.get(id=contest_id)
		question_list = QuizQuestion.objects.filter(contest=contest) 

		response = {} 
		question_stats = [] 

		for question in question_list: 

			correct_subs, total_subs = fetch_question_attempts_accuracy(question) 
			question_stats.append([question, correct_subs, total_subs])

		response['question_stats'] = question_stats

		return render(request, 'quiz_view_analytics.html', response)

	else:

		return display_leaderboard(request) 

# Method to fetch question data (how many questions answered) 
def fetch_question_attempts_accuracy(question): 

	# From a question object fetch how many people answered it out of total [returning a %age]
	
	# Fetching all submissions 
	submission_list = list(Submission.objects.filter(question = question)) 

	# Checking how many correct
	correct_subs = 0
	total_subs   = len(submission_list)

	for submission in submission_list: 
		if is_correct(submission, submission.question): 
			correct_subs += 1

	return correct_subs, total_subs


# Method to read TSV file and add questions
def parse_csv_file(contest, csv_file): 

	# Uploading the TSV file into a contest
	encoded_csv_file = csv_file.read().decode('utf-8') 
	io_string = io.StringIO(encoded_csv_file) 
	csv_file_reader = csv.DictReader(io_string) 

	try:

		for row in csv_file_reader: 

			# Parse the csv row 
			question_txt = row['questionText']
			answer = row['answerText']
			second_answer = row['secondAnswerText']
			image_url = row['imageUrl']

			third_answer = None 
			try: 
				if row['thirdAnswerText'] is not None: 
					third_answer = row['thirdAnswerText'] 
			except: 
				print('Exception has occurred') 

			# Add question to database
			quiz_question = QuizQuestion(contest = contest, question = question_txt, answer = answer)  

			if second_answer is not None:
				quiz_question.second_answer = second_answer

			if image_url is not None:
				quiz_question.image_url = image_url

			if second_answer is not None:
				quiz_question.second_answer = second_answer

			if third_answer is not None: 
				quiz_question.third_answer = third_answer

			quiz_question.save()

	except Exception as ex: 

		print('Exception occurred while parsing CSV file') 
		message = "Exception occurred while parsing CSV file" 
		print(ex) 
		return False, ex 

	except KeyError as error: 

		print("Key error while parsing csv file") 
		message = "Key error while parsing csv file" 
		print(error) 
		return False, error

	return True, "" 
