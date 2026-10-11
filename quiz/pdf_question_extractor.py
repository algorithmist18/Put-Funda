# Turns an uploaded PDF of quiz questions into a flat list of simplified
# question/answer dicts, using the free-tier Gemini API (google-genai) plus
# PyMuPDF. One Gemini call per page: each page is rendered to an image and
# sent with a prompt that (a) skips pages that are just facts/rules rather
# than an actual question, (b) picks only ONE question per page even if
# several are present, and (c) writes that question as a short context
# passage followed by the question itself, not a bare one-liner.

import json
import time

import pymupdf
from django.conf import settings
from google import genai
from google.genai import types

MAX_PDF_PAGES = 30

PAGE_RENDER_ZOOM = 2.0

EXTRACTION_MODEL = 'gemini-3.1-flash-lite'

EXTRACTION_PROMPT = (
	"You are helping turn a page from a quiz/trivia document into a single "
	"quiz question for an app. Look at the page image.\n\n"
	"First, decide whether the page actually poses a question AND shows its "
	"answer, both on this same page - as opposed to just facts, rules, "
	"instructions, section headers, or a question with no answer given "
	"anywhere on this page. A real question typically ends in a question "
	"mark and its answer is explicitly written on the page (for example, "
	"next to 'Answer:' or similar). If the page is purely "
	"factual/instructional, or poses a question but doesn't show its "
	"answer on this same page, return an empty list. It is far better to "
	"return nothing than to invent a question or guess at an answer that "
	"isn't actually shown.\n\n"
	"If the page does contain one or more such questions, pick exactly "
	"ONE - whichever best represents the page's content - even if the "
	"page has two or three. Never return more than one question for a "
	"page.\n\n"
	"Write that one question as a short passage of 2-4 lines: a couple of "
	"lines giving the context/background needed to understand it (in "
	"plain, simple language, stripped of any multi-part/branching "
	"structure), followed by the question itself. It must be answerable "
	"from the passage alone, without seeing the original page.\n\n"
	"For the answer: copy it exactly as it is written on the page. Do not "
	"compute, guess, correct or substitute your own answer, even if you "
	"believe you know better - use only what the page itself states."
)

RESPONSE_SCHEMA = {
	"type": "array",
	"maxItems": 1,
	"items": {
		"type": "object",
		"properties": {
			"question": {"type": "string"},
			"answer": {"type": "string"},
		},
		"required": ["question", "answer"],
	},
}


class PdfExtractionError(Exception):
	pass


def _render_page_to_png(page):

	pixmap = page.get_pixmap(matrix = pymupdf.Matrix(PAGE_RENDER_ZOOM, PAGE_RENDER_ZOOM))
	return pixmap.tobytes('png')


def extract_questions_from_pdf(pdf_bytes):
	"""Returns (questions, elapsed_seconds).

	questions is a list of {'question', 'answer'} dicts, at most one per
	PDF page (pages with no real question - just facts/rules - contribute
	none).

	Raises PdfExtractionError for anything that stops this from producing
	usable questions (missing API key, unreadable PDF, too many pages,
	Gemini/network failure), so the caller can show the user a plain
	message instead of a 500.
	"""

	start_time = time.monotonic()

	api_key = getattr(settings, 'GEMINI_API_KEY', '')

	if not api_key:
		raise PdfExtractionError('PDF import is not configured: set GEMINI_API_KEY to use it.')

	try:
		document = pymupdf.open(stream = pdf_bytes, filetype = 'pdf')
	except Exception as ex:
		raise PdfExtractionError('Could not read that file as a PDF.') from ex

	if document.page_count == 0:
		raise PdfExtractionError('That PDF has no pages.')

	if document.page_count > MAX_PDF_PAGES:
		raise PdfExtractionError(
			'That PDF has {} pages; only PDFs up to {} pages are supported.'.format(
				document.page_count, MAX_PDF_PAGES
			)
		)

	# Force the plain Gemini Developer API (not Vertex AI, which needs
	# OAuth credentials, not an API key). Without this, the client falls
	# back to whatever GOOGLE_GENAI_USE_VERTEXAI/_ENTERPRISE happen to be
	# set to in the environment it runs in, silently switching endpoints
	# and rejecting a perfectly valid API key with a confusing 401.
	client = genai.Client(api_key = api_key, vertexai = False)
	config = types.GenerateContentConfig(
		response_mime_type = 'application/json',
		response_schema = RESPONSE_SCHEMA,
		# Keep extraction literal/deterministic rather than creative -
		# this is transcription, not writing
		temperature = 0,
	)

	questions = []

	for page in document:

		image_part = types.Part.from_bytes(data = _render_page_to_png(page), mime_type = 'image/png')

		try:
			response = client.models.generate_content(
				model = EXTRACTION_MODEL,
				contents = [EXTRACTION_PROMPT, image_part],
				config = config,
			)
		except Exception as ex:
			raise PdfExtractionError('Gemini could not process the PDF: {}'.format(ex)) from ex

		try:
			page_questions = json.loads(response.text)
		except (ValueError, TypeError) as ex:
			raise PdfExtractionError('Gemini returned an unexpected response.') from ex

		if not isinstance(page_questions, list):
			continue

		# Only one question per page, even if the model returns more
		for item in page_questions[:1]:

			if not isinstance(item, dict):
				continue

			question = (item.get('question') or '').strip()
			answer = (item.get('answer') or '').strip()

			if question and answer:
				questions.append({'question': question, 'answer': answer})

	elapsed_seconds = time.monotonic() - start_time

	return questions, elapsed_seconds
