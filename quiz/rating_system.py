
# Importing libraries
import random, math 
from quiz.models import Contest, QuizQuestion

# Global variable
no_of_contest_played = 0

# Method to compute rating weight based on matches played 
def rating_weight(no_of_matches_played): 

	return ((0.5 * no_of_matches_played) + 0.1) / ((0.25 * no_of_matches_played) + 0.2) 

# Method to compute volatility weight based on matches played 
def volatility_weight(no_of_matches_played): 

	return ((0.2 * no_of_matches_played) + 0.01) / ((0.1 * no_of_matches_played) + 0.02) 

# Method to compute elo-rated probability
def elo_probability(rating_a, rating_b, volatility_a, volatility_b): 

	return 1 / (1 + 4 ** ((rating_a - rating_b) / (volatility_a * volatility_a + volatility_b * volatility_b) ** 0.5))

# Method to check the probability of a person answering the question
def elo_question_probability(rating_a, rating_b, vol_a, vol_b): 

	return 1 / (1 + 10 ** ((rating_a - rating_b) / (400)))

# Method to compute expected rating from contest
def expected_rank(index, ratings, volatility): 

	expected_rank_sum = 1.0

	for i in range(len(ratings)): 

		if i != index:

			expected_rank_sum += elo_probability(ratings[index], rating[i], volatility[index], volatility[i])

	return expected_rank_sum

# Method to compute performance
def performance(no_of_players, rank): 

	return math.log(no_of_players / rank) 

# Method to compute correct answers factor
def compute_score_factor(correct_answers, no_of_questions): 

	return math.log(correct_answers / no_of_questions) 


# Method to fetch ranking from correct answers 
def fetch_ranking(correct_answers):

	ranking = [None] * len(correct_answers) 
	correct_ans = {} 

	for i in range(len(correct_answers)): 

		correct_ans.update({i : correct_answers[i]})

	rank = 0

	for k, v in sorted(correct_ans.items(), key = lambda kv: kv[1], reverse = True): 

		print(k, v) 
		ranking[k] = rank + 1
		rank += 1

	return ranking


# Method to simulate contest rankings and questions 
def update_rating(rating_array, volatility_array, ranking, correct_answers, no_of_players, no_of_contest_played): 		

	#no_of_questions = len(question_ratings)
	new_rating = [None] * no_of_players
	new_volatility = [None] * no_of_players

	# Average rating
	rating_avg = 0 
	i = 0 

	for rating in rating_array:
		rating_avg += rating_array[i] 

	rating_avg /= no_of_players

	# Contest over, calculate rating
	for i in range(no_of_players): 

		expected_rank = 1.0
		actual_rank = ranking[i] 
		actual_correct_answers = correct_answers[i] 
		rms_mean = 0
		volatility_sum = 0 

		for j in range(no_of_players): 

			if i != j: 

				expected_rank += elo_question_probability(rating_array[i], 
				rating_array[j], volatility_array[i], volatility_array[j])

				volatility_sum += volatility_array[j] ** 2
				rms_mean += (rating_array[j] - rating_avg) ** 2
	
		print('Expected rank: ', expected_rank) 
	
		expected_rank_ratio = 100 * ((no_of_players + 1) - expected_rank) / (no_of_players)# * (1 - (1 / (expected_rank)))
		actual_rank_ratio = 100 * ((no_of_players + 1) - actual_rank) / (no_of_players) #* (1 - (1 / (actual_rank))) 

		print('Expected pct of people player will beat: ', expected_rank_ratio) 
		print('Actual pct of people player did beat: ', actual_rank_ratio) 

		volatility_sum += volatility_array[i] ** 2
		rms_mean += (rating_array[i] - rating_avg) ** 2

		actual_performance = ((actual_rank_ratio))
		expected_performance = ((expected_rank_ratio)) 

		rating_weight = ((0.4 * no_of_contest_played[i] + (0.2)) / ((0.7 * no_of_contest_played[i]) + (0.6)))
		volatility_weight = ((0.5 * no_of_contest_played[i] + (0.8)) / ((no_of_contest_played[i]) + (0.6)))

		print(rating_weight, volatility_weight, actual_performance, expected_performance) 

		new_rating[i] = rating_array[i] + 1.5 * (actual_performance - expected_performance)

		# Compute new volatility
		new_volatility[i] = (new_rating[i] - rating_array[i]) ** 2
		new_volatility[i] += volatility_weight
		new_volatility[i] += (volatility_array[i] * volatility_array[i])  
		new_volatility[i] /= (volatility_weight + 1.1)
		new_volatility[i] = (new_volatility[i] ** 0.5)

	# Return new set of question_rating
	return new_rating, new_volatility
	
