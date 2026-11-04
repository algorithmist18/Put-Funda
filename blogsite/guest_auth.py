# Lets an unregistered visitor play a contest or Question of the Day
# without signing up. The rest of the app (Submission, QOTDSubmission,
# Leaderboard, ratings) all key off a real User row, so rather than
# rewriting that machinery to tolerate an anonymous player, we quietly
# create a throwaway "guest" account and log the visitor into it the
# moment they try to actually play something.

import random

from django.contrib.auth import login
from django.contrib.auth.models import User

GUEST_USERNAME_MIN = 100000
GUEST_USERNAME_MAX = 999999


def generate_guest_username():

	while True:

		candidate = 'guest{}'.format(random.randint(GUEST_USERNAME_MIN, GUEST_USERNAME_MAX))

		if not User.objects.filter(username = candidate).exists():
			return candidate


def ensure_guest_login(request):
	"""Returns an authenticated user for this request, creating and
	logging in a guest account first if the visitor isn't signed in."""

	if request.user.is_authenticated:
		return request.user

	guest = User(username = generate_guest_username())
	guest.set_unusable_password()
	guest.save()

	guest.profile.is_guest = True
	guest.profile.save()

	login(request, guest, backend = 'django.contrib.auth.backends.ModelBackend')

	return guest
