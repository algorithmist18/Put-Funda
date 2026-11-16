# Signs short-lived "upload tickets" that authorize a browser to upload a
# contest's question file (PDF/CSV) directly to Vercel Blob, via
# api/blob-upload-token.js - see that file and BLOB_UPLOAD_TICKET_SECRET in
# blog/settings.py for the full picture.
#
# This only signs tickets; api/blob-upload-token.js is the one that verifies
# them (using the same secret), since it's the side deciding whether to hand
# out a real Vercel Blob client token. The scheme is a plain HMAC over a
# base64 JSON payload - deliberately not Django's own signing helpers, so
# the exact same two steps are trivial to reproduce in that Node function.

import base64
import hashlib
import hmac
import json
import time


def make_upload_ticket(secret, ttl_seconds = 600):

	payload = json.dumps({'exp': int((time.time() + ttl_seconds) * 1000)}).encode('utf-8')
	payload_b64 = base64.b64encode(payload).decode('ascii')
	signature = hmac.new(secret.encode('utf-8'), payload_b64.encode('ascii'), hashlib.sha256).hexdigest()

	return '{}.{}'.format(payload_b64, signature)
