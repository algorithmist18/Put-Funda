# Importing libraries 

from quiz.models import QuizQuestion, Contest, Submission, RatingHistory, Leaderboard
from blogsite.models import Profile
from .models import User 
from django.db import models
from django.core.exceptions import ObjectDoesNotExist
import difflib

# Method to return similarity of two strings 
def similarity_quotient(str1, str2): 

	# Convert everything to lower case 
	str1 = str1.lower()
	str2 = str2.lower() 

	# Compute similarity
	similarity = difflib.SequenceMatcher(None, str1, str2).ratio() 
	return similarity


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

# Method to fetch list of submissions for a user for a contest 
def fetch_submissions_by_user_contest(user, contest): 

	print('fetch_submissions_by_user_contest ', user.id, contest.id) 

	submissions = []
	try: 

		submissions = Submission.objects.filter(user = user, question__contest = contest) 
		
	except: 

		print('Exception caught while fetching submissions') 

	return submissions 


# Method to fetch users and their submissions with correct answers 
def fetch_correct_submissions(question): 

	print('Fetch correct submissions for', question.id) 

	# Fetch all the submissions 
	# See which one is correct 
	correct_submissions = []
	submissions = Submission.objects.filter(question = question) 
	print(submissions) 
	for submission in submissions: 
		
		given_answer = submission.answer.lower() 
		correct_answer = submission.question.answer.lower() 

		if is_correct(submission, submission.question): 
			correct_submissions.append(submission) 

	return correct_submissions 


