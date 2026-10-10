# Turns an uploaded PDF of quiz questions into a flat list of simplified
# question/answer dicts, using the free-tier Gemini API (google-genai) plus
# PyMuPDF. One Gemini call per page: each page is rendered to an image and
# sent with a prompt asking for short, self-contained questions rewritten
# in plain language.

import json

import pymupdf
from django.conf import settings
from google import genai
from google.genai import types

MAX_PDF_PAGES = 12

PAGE_RENDER_ZOOM = 2.0

EXTRACTION_MODEL = 'gemini-2.5-flash'

EXTRACTION_PROMPT = (
	"You are helping turn a page from a quiz/trivia document into simple "
	"quiz questions for an app. Look at the page image and find every "
	"self-contained question that has a clear, short answer. For each one, "
	"rewrite the question in plain, simple language, at most 2-3 sentences, "
	"removing any multi-part/branching structure or irrelevant context, but "
	"keeping it answerable from the rewritten text alone. Skip anything "
	"that is not actually a question with a determinable answer (section "
	"headers, instructions, decorative text). Give each question the "
	"single best short answer. If there is no question content on this "
	"page, return an empty list."
)

RESPONSE_SCHEMA = {
	"type": "array",
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
	"""Returns a list of {'question', 'answer'} dicts extracted from the PDF.

	Raises PdfExtractionError for anything that stops this from producing
	usable questions (missing API key, unreadable PDF, too many pages,
	Gemini/network failure), so the caller can show the user a plain
	message instead of a 500.
	"""

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

	client = genai.Client(api_key = api_key)
	config = types.GenerateContentConfig(
		response_mime_type = 'application/json',
		response_schema = RESPONSE_SCHEMA,
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

		for item in page_questions:

			if not isinstance(item, dict):
				continue

			question = (item.get('question') or '').strip()
			answer = (item.get('answer') or '').strip()

			if question and answer:
				questions.append({'question': question, 'answer': answer})

	return questions
