# Turns an uploaded PDF of quiz questions into a flat list of simplified
# question/answer dicts, using the free-tier Gemini API (google-genai) plus
# PyMuPDF. Pages are processed in batches of BATCH_SIZE: every page image in
# a batch is sent to Gemini in a single call, with a prompt that (a) finds
# the questions first, (b) separately finds their answers - which often
# appear on a later page/slide within the same batch, not the question's own
# page - matching them up in order rather than letting the model compute or
# guess an answer itself, (c) skips pages that are just facts/rules, (d)
# picks only one question per page even if several are present, and (e)
# writes each kept question as a short context passage, not a bare one-liner.

import json
import time

import pymupdf
from django.conf import settings
from google import genai
from google.genai import types

MAX_PDF_PAGES = 300

BATCH_SIZE = 30

PAGE_RENDER_ZOOM = 2.0

EXTRACTION_MODEL = 'gemini-3.1-flash-lite'

EXTRACTION_PROMPT = (
	"You will be shown several consecutive pages/slides from a quiz "
	"document, in order (the first image is the earliest page in this "
	"batch). Many such documents separate questions from their answers: "
	"the questions appear first, and the correct answers are revealed "
	"later - often on their own slide(s), such as an answer key - not on "
	"the question's own page.\n\n"
	"Work in two passes:\n\n"
	"PASS 1 - find the questions: go through the pages in order and "
	"identify every page that poses a real, self-contained question, as "
	"opposed to a page that's just facts, rules, instructions, section "
	"headers, or an answer-reveal slide. A real question typically ends "
	"in a question mark. If a page shows two or three candidate "
	"questions, pick only the single one that best represents that page "
	"- never more than one question per page.\n\n"
	"PASS 2 - find the answers: separately, go back through the pages "
	"looking for where each question's answer is actually revealed. "
	"Match answers to questions strictly by order of appearance - the "
	"first answer you find corresponds to the first question you found, "
	"the second answer to the second question, and so on. Only keep a "
	"question if you can find its matching answer somewhere in this "
	"batch. If a question's answer cannot be found, drop that question "
	"entirely - never compute, infer, or guess an answer yourself from "
	"general knowledge.\n\n"
	"For every kept question, rewrite it as a short passage of 2-4 "
	"lines: a couple of lines of context/background in plain language "
	"(stripped of any multi-part/branching structure), followed by the "
	"question itself, answerable from the passage alone without seeing "
	"the original pages. For the answer, copy it exactly as written "
	"wherever it was revealed - do not alter, correct, or compute it.\n\n"
	"Return the kept questions in the same order they originally "
	"appeared."
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


def _batch_ranges(page_count):

	for start in range(0, page_count, BATCH_SIZE):
		yield start, min(start + BATCH_SIZE, page_count)


def extract_questions_from_pdf(pdf_bytes):
	"""Returns (questions, elapsed_seconds).

	questions is a list of {'question', 'answer'} dicts, at most one per
	PDF page (pages with no real question - just facts/rules - or whose
	question has no matched answer anywhere in its batch, contribute none).

	Pages are sent to Gemini BATCH_SIZE at a time (one call per batch, all
	of that batch's page images in the one call) so the model can match a
	question to an answer that appears on a later page within the batch,
	rather than being asked to invent one.

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

	for batch_start, batch_end in _batch_ranges(document.page_count):

		image_parts = [
			types.Part.from_bytes(data = _render_page_to_png(document[i]), mime_type = 'image/png')
			for i in range(batch_start, batch_end)
		]

		try:
			response = client.models.generate_content(
				model = EXTRACTION_MODEL,
				contents = [EXTRACTION_PROMPT] + image_parts,
				config = config,
			)
		except Exception as ex:
			raise PdfExtractionError('Gemini could not process the PDF: {}'.format(ex)) from ex

		try:
			batch_questions = json.loads(response.text)
		except (ValueError, TypeError) as ex:
			raise PdfExtractionError('Gemini returned an unexpected response.') from ex

		if not isinstance(batch_questions, list):
			continue

		for item in batch_questions:

			if not isinstance(item, dict):
				continue

			question = (item.get('question') or '').strip()
			answer = (item.get('answer') or '').strip()

			if question and answer:
				questions.append({'question': question, 'answer': answer})

	elapsed_seconds = time.monotonic() - start_time

	return questions, elapsed_seconds
