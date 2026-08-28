# Question of the Day: a single daily question, separate from timed
# contests. Only the account named QOTD_RELEASER_USERNAME can release
# (create/update) the day's question; everyone, including that account,
# can play it.

import datetime

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse

from blogposts.models import Post
from quiz.analysis_views import similarity_quotient
from quiz.models import QuestionOfTheDay, QOTDSubmission

QOTD_RELEASER_USERNAME = 'avinashm2427'


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


@login_required
def qotd_home(request):

	today = datetime.date.today()
	qotd = QuestionOfTheDay.objects.filter(date = today).first()
	profile = request.user.profile
	submission = None

	if qotd:
		submission = QOTDSubmission.objects.filter(user = request.user, qotd = qotd).first()

	if request.method == 'POST' and qotd and submission is None:

		answer = request.POST.get('answer', '').strip()
		answered_correctly = is_qotd_answer_correct(answer, qotd)

		submission = QOTDSubmission.objects.create(
			user = request.user, qotd = qotd, answer = answer, is_correct = answered_correctly
		)

		update_streak(profile, today, answered_correctly)

	context = {
		'qotd': qotd,
		'submission': submission,
		'profile': profile,
		'can_release': request.user.username == QOTD_RELEASER_USERNAME,
	}

	return render(request, 'qotd_home.html', context)


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
	}

	return render(request, 'qotd_release.html', context)
