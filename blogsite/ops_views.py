# TEMPORARY. Lets `migrate` be triggered over HTTP once, from inside
# Vercel's own runtime - where DATABASE_URL is genuinely available even
# though it's marked "Sensitive" and can't be exported to a local machine
# via `vercel env pull` or the dashboard. Protected by a token that only
# matches if MIGRATE_TOKEN is set as a Vercel env var; wrong/missing token
# or wrong HTTP method both just 404, so this doesn't advertise itself.
#
# Delete this file and its URL entry (blog/urls.py) once migrations are
# confirmed applied - this should not stay live permanently.

import io
import os
import traceback

from django.core.management import call_command
from django.http import Http404, HttpResponse


def run_migrate_once(request):

	if request.method != 'GET':
		raise Http404()

	expected_token = os.environ.get('MIGRATE_TOKEN')
	given_token = request.GET.get('token')

	if not expected_token or given_token != expected_token:
		raise Http404()

	output = io.StringIO()

	try:
		call_command('migrate', interactive=False, verbosity=2, stdout=output, stderr=output)
	except Exception:
		output.write('\n\nMIGRATE FAILED:\n')
		output.write(traceback.format_exc())
		return HttpResponse(output.getvalue(), content_type='text/plain', status=500)

	output.write('\n\nDone. Remove this endpoint (blogsite/ops_views.py + its URL) now.')

	return HttpResponse(output.getvalue(), content_type='text/plain')
