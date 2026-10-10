# Question of the Day: a single daily question, separate from timed
# contests. Only the account named QOTD_RELEASER_USERNAME can release
# (create/update) the day's question; everyone, including that account,
# can play it.

import datetime

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse

from blogposts.models import Post
from blogsite.guest_auth import ensure_guest_login
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


def qotd_home(request):

	today = datetime.date.today()
	qotd = QuestionOfTheDay.objects.filter(date = today).first()
	submission = None

	if qotd and request.user.is_authenticated:
		submission = QOTDSubmission.objects.filter(user = request.user, qotd = qotd).first()

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

	context = {
		'qotd': qotd,
		'submission': submission,
		'profile': profile,
		'can_release': request.user.username == QOTD_RELEASER_USERNAME,
	}

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

	context = {'archive': archive}

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
	}

	return render(request, 'qotd_release.html', context)
