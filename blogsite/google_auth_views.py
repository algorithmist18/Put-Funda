# Google Sign-In (Google Identity Services): verifies the ID token the
# front-end button hands us, then logs the user in - creating an account
# on first sign-in, or linking to an existing account with the same email.

from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

USERNAME_MAX_LENGTH = 15


def generate_unique_username(email):

	base = email.split('@')[0]
	base = ''.join(ch for ch in base if ch.isalnum() or ch in '.+-_')
	base = base[:USERNAME_MAX_LENGTH] or 'user'

	if not User.objects.filter(username = base).exists():
		return base

	suffix = 1

	while True:

		candidate = '{}{}'.format(base[:USERNAME_MAX_LENGTH - len(str(suffix))], suffix)

		if not User.objects.filter(username = candidate).exists():
			return candidate

		suffix += 1


@require_POST
@csrf_protect
def google_login(request):

	if not settings.GOOGLE_OAUTH_CLIENT_ID:
		return JsonResponse({'error': 'Google sign-in is not configured.'}, status = 503)

	token = request.POST.get('credential')

	if not token:
		return JsonResponse({'error': 'Missing Google credential.'}, status = 400)

	try:

		payload = id_token.verify_oauth2_token(
			token, google_requests.Request(), settings.GOOGLE_OAUTH_CLIENT_ID
		)

	except ValueError:

		return JsonResponse({'error': 'Invalid Google credential.'}, status = 400)

	if not payload.get('email_verified'):
		return JsonResponse({'error': 'Google account email is not verified.'}, status = 400)

	email = payload['email']
	user = User.objects.filter(email = email).first()

	if user is None:

		user = User(
			username = generate_unique_username(email),
			email = email,
			first_name = payload.get('given_name', '')[:30],
			last_name = payload.get('family_name', '')[:150],
		)
		user.set_unusable_password()
		user.save()

	if not user.profile.email_confirmed:

		user.profile.email_confirmed = True
		user.profile.save()

	login(request, user, backend = 'django.contrib.auth.backends.ModelBackend')

	return JsonResponse({'redirect': '/home'})
