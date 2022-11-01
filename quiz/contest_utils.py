# Importing libraries 
import pytz, datetime 
from quiz.models import QuizQuestion, Contest, Submission, RatingHistory, Leaderboard
from blogsite.models import Profile
from .models import User 

# Method to check whether a contest is active
def is_contest_active(contest): 

	# Fetch current date 
	current_time = datetime.datetime.now(pytz.timezone('UTC')) 

	time_difference = (contest.time - current_time).total_seconds() 
	time_difference /= 60 
	time_difference *= -1

	return time_difference <= contest.valid_for