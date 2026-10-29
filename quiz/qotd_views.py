# Question of the Day: a single daily question, separate from timed
# contests. Only the account named QOTD_RELEASER_USERNAME can release
# (create/update) the day's question; everyone, including that account,
# can play it.

import datetime
import random

from django.contrib.auth.decorators import login_required
from django.db.models import Max
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from blogposts.models import Post
from blogsite.guest_auth import ensure_guest_login
from quiz.analysis_views import similarity_quotient
from quiz.models import QuestionOfTheDay, QOTDSubmission, QOTDSuggestion

QOTD_RELEASER_USERNAME = 'avinashm2427'


def can_user_release(user):

	return user.is_authenticated and user.username == QOTD_RELEASER_USERNAME


def next_queue_date():

	# The day after whatever's already scheduled, so a freshly allocated
	# suggestion never overwrites today's question or jumps the queue
	latest_date = QuestionOfTheDay.objects.aggregate(Max('date'))['date__max']
	today = datetime.date.today()

	return max(latest_date or today, today) + datetime.timedelta(days = 1)


def is_qotd_answer_correct(given_answer, qotd):

	if not given_answer:
		return False

	if similarity_quotient(given_answer, qotd.answer) >= 0.85:
		return True

	if qotd.second_answer and similarity_quotient(given_answer, qotd.second_answer) >= 0.85:
		return True

	if qotd.third_answer and similarity_quotient(given_answer, qotd.third_answer) >= 0.85:
		return True

	return False


def update_streak(profile, qotd_date, answered_correctly):

	if answered_correctly:

		if profile.last_qotd_date == qotd_date - datetime.timedelta(days = 1):
			profile.current_streak = (profile.current_streak or 0) + 1
		else:
			profile.current_streak = 1

		profile.last_qotd_date = qotd_date

		if profile.current_streak > (profile.longest_streak or 0):
			profile.longest_streak = profile.current_streak

	else:

		profile.current_streak = 0

	profile.save()


def announce_qotd(qotd, releaser):

	title = 'Question of the day: {}'.format(qotd.date.isoformat())
	content = '<p>Today\'s question is live. <a href="{}">Go play it</a>.</p>'.format(
		reverse('qotd_home')
	)

	Post.objects.update_or_create(
		title = title, author = releaser, defaults = {'content': content, 'anon': False}
	)


def qotd_home(request):

	today = datetime.date.today()
	qotd = QuestionOfTheDay.objects.filter(date = today).first()
	submission = None

	if qotd and request.user.is_authenticated:
		submission = QOTDSubmission.objects.filter(user = request.user, qotd = qotd).first()

	if request.method == 'POST' and 'question' in request.POST:

		# A suggested question, not an answer to today's one - distinguished
		# by the presence of a 'question' field, which the answer form
		# doesn't have. Handled (and the request ended) here regardless of
		# login state, so it can never fall through to the answer-submission
		# branch below and get mistaken for an answer to today's question.
		if request.user.is_authenticated:
			QOTDSuggestion.objects.create(
				question = request.POST.get('question', '').strip(),
				answer = request.POST.get('answer', '').strip(),
				second_answer = request.POST.get('second_answer', '').strip(),
				third_answer = request.POST.get('third_answer', '').strip(),
				image_url = request.POST.get('image_url', '').strip(),
				image = request.FILES.get('image'),
				submitted_by = request.user,
			)

		return redirect('qotd_home')

	if request.method == 'POST' and qotd and submission is None:

		# Only create a guest account once someone actually commits to
		# playing - not just for browsing the page
		user = ensure_guest_login(request)

		answer = request.POST.get('answer', '').strip()
		answered_correctly = is_qotd_answer_correct(answer, qotd)

		submission = QOTDSubmission.objects.create(
			user = user, qotd = qotd, answer = answer, is_correct = answered_correctly
		)

		update_streak(user.profile, today, answered_correctly)

	profile = request.user.profile if request.user.is_authenticated else None
	can_release = can_user_release(request.user)

	context = {
		'qotd': qotd,
		'submission': submission,
		'profile': profile,
		'can_release': can_release,
	}

	if request.user.is_authenticated:
		context['my_suggestions'] = QOTDSuggestion.objects.filter(
			submitted_by = request.user
		).order_by('-created_at')[:30]

	if can_release:
		context['pending_suggestions'] = QOTDSuggestion.objects.filter(status = 'pending').order_by('created_at')
		context['default_allocate_date'] = next_queue_date()

	return render(request, 'qotd_home.html', context)


def qotd_archive(request):

	today = datetime.date.today()
	past_qotds = QuestionOfTheDay.objects.filter(date__lt = today).order_by('-date')[:30]

	my_submissions = {}

	if request.user.is_authenticated:

		submissions = QOTDSubmission.objects.filter(user = request.user, qotd__in = past_qotds)
		my_submissions = {submission.qotd_id: submission for submission in submissions}

	archive = [
		{'qotd': qotd, 'my_submission': my_submissions.get(qotd.id)}
		for qotd in past_qotds
	]

	context = {
		'archive': archive,
		'can_release': can_user_release(request.user),
	}

	return render(request, 'qotd_archive.html', context)


@login_required
def release_qotd(request):

	if request.user.username != QOTD_RELEASER_USERNAME:
		return redirect('qotd_home')

	today = datetime.date.today()

	if request.method == 'POST':

		date_str = request.POST.get('date') or str(today)

		try:
			release_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
		except ValueError:
			release_date = today

		qotd, created = QuestionOfTheDay.objects.update_or_create(
			date = release_date,
			defaults = {
				'question': request.POST.get('question', '').strip(),
				'answer': request.POST.get('answer', '').strip(),
				'second_answer': request.POST.get('second_answer', '').strip(),
				'third_answer': request.POST.get('third_answer', '').strip(),
				'image_url': request.POST.get('image_url', '').strip(),
				'created_by': request.user,
			}
		)

		image = request.FILES.get('image')

		if image:
			qotd.image = image
			qotd.save()

		if release_date == today:
			announce_qotd(qotd, request.user)

		return redirect('qotd_release')

	context = {
		'today': today,
		'todays_qotd': QuestionOfTheDay.objects.filter(date = today).first(),
		'upcoming': QuestionOfTheDay.objects.filter(date__gt = today).order_by('date'),
		'can_release': True,
	}

	return render(request, 'qotd_release.html', context)


@login_required
def review_qotd_suggestion(request, suggestion_id):

	if request.user.username != QOTD_RELEASER_USERNAME or request.method != 'POST':
		return redirect('qotd_home')

	suggestion = QOTDSuggestion.objects.filter(id = suggestion_id, status = 'pending').first()

	if suggestion is None:
		return redirect('qotd_home')

	action = request.POST.get('action')

	if action == 'allocate':

		date_str = request.POST.get('date', '').strip()

		try:
			allocate_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
		except ValueError:
			allocate_date = next_queue_date()

		qotd, created = QuestionOfTheDay.objects.update_or_create(
			date = allocate_date,
			defaults = {
				'question': suggestion.question,
				'answer': suggestion.answer,
				'second_answer': suggestion.second_answer,
				'third_answer': suggestion.third_answer,
				'image': suggestion.image,
				'image_url': suggestion.image_url,
				'created_by': request.user,
			}
		)

		suggestion.status = 'approved'
		suggestion.released_as = qotd

	elif action == 'reject':

		suggestion.status = 'rejected'

	else:
		return redirect('qotd_home')

	suggestion.reviewed_at = timezone.now()
	suggestion.save()

	return redirect('qotd_home')


@login_required
def randomize_qotd_queue(request):

	if request.user.username != QOTD_RELEASER_USERNAME or request.method != 'POST':
		return redirect('qotd_release')

	today = datetime.date.today()
	upcoming = list(QuestionOfTheDay.objects.filter(date__gt = today).order_by('date'))

	if len(upcoming) >= 2:

		fields = ['question', 'answer', 'second_answer', 'third_answer', 'image', 'image_url']
		shuffled_content = [{field: getattr(qotd, field) for field in fields} for qotd in upcoming]
		random.shuffle(shuffled_content)

		for qotd, content in zip(upcoming, shuffled_content):

			for field, value in content.items():
				setattr(qotd, field, value)

			qotd.save()

	return redirect('qotd_release')
