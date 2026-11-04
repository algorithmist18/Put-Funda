# Django Storage backend backed by Vercel Blob (https://vercel.com/docs/vercel-blob),
# used in production via STORAGES['default'] in blog/settings.py - only
# when BLOB_READ_WRITE_TOKEN is set, which is how Vercel injects it once
# Blob storage is connected to the project. Local dev and PythonAnywhere
# don't set that var, so they keep using plain FileSystemStorage instead.
#
# Every stored "name" is the blob's full public URL rather than a bare
# filename - Vercel Blob appends a random suffix to the path to avoid
# collisions, so the only name guaranteed to still resolve later is
# whatever URL the upload call actually returns.

import os
import tempfile

import requests
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible


@deconstructible
class VercelBlobStorage(Storage):

	def __init__(self, token = None):

		self.token = token or os.environ.get('BLOB_READ_WRITE_TOKEN')

	def _client(self):

		from vercel.blob import BlobClient

		return BlobClient(token = self.token) if self.token else BlobClient()

	# Vercel Blob already avoids collisions server-side (by randomising the
	# stored path), so there's no need to pre-check availability here -
	# doing so would just be an extra network round-trip per upload.
	def get_available_name(self, name, max_length = None):

		return name

	def _save(self, name, content):

		content.seek(0)
		data = content.read()
		content_type = getattr(content, 'content_type', None) or 'application/octet-stream'

		tmp = tempfile.NamedTemporaryFile(delete = False)

		try:
			tmp.write(data)
			tmp.close()

			result = self._client().upload_file(
				tmp.name, name, access = 'public', content_type = content_type
			)
		finally:
			os.unlink(tmp.name)

		return result.url

	def _open(self, name, mode = 'rb'):

		response = requests.get(name)
		response.raise_for_status()

		return ContentFile(response.content, name = name)

	def exists(self, name):

		try:
			response = requests.head(name, allow_redirects = True)
		except requests.RequestException:
			return False

		return response.status_code == 200

	def delete(self, name):

		try:
			self._client().delete([name])
		except Exception:
			# Best-effort: a stale DB row pointing at an already-gone blob
			# shouldn't block whatever the caller (e.g. re-uploading a
			# profile picture) was doing.
			pass

	def url(self, name):

		return name

	def size(self, name):

		try:
			response = requests.head(name, allow_redirects = True)
			return int(response.headers.get('Content-Length', 0))
		except requests.RequestException:
			return 0
