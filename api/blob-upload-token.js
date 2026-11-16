// Node.js serverless function, separate from the rest of this (Python/
// Django) app. It only exists so a browser can upload a contest's question
// file (PDF/CSV) directly to Vercel Blob storage instead of through Django -
// Vercel's serverless functions (ours included) reject any request body
// over 4.5MB, which a Django-side upload would otherwise hit for anything
// but small files. @vercel/blob's client-upload helper (handleUpload) that
// makes this possible only ships for Node, not Python, hence this one file.
//
// Two things call this, both driven by @vercel/blob/client's upload()
// (see quiz_schedule.html/quiz_edit_contest.html): first the browser, to
// get a short-lived token to upload with; then Vercel's own servers, once
// that upload finishes. Neither request is the file itself - the browser
// talks to Vercel Blob's storage directly for that part.
//
// onBeforeGenerateToken is the only gate here, so it has to check the
// caller is actually someone who just loaded the schedule/edit-contest page
// while logged into Django - see quiz/upload_tickets.py for the other half
// of this (same secret, same HMAC scheme, deliberately simple enough to
// reproduce exactly in both languages).

const crypto = require('crypto');
const { handleUpload } = require('@vercel/blob/client');

function verifyUploadTicket(ticket, secret) {

	if (!ticket) {
		throw new Error('Missing upload ticket.');
	}

	const parts = ticket.split('.');

	if (parts.length !== 2) {
		throw new Error('Malformed upload ticket.');
	}

	const [payloadBase64, signatureHex] = parts;

	const expectedSignature = crypto
		.createHmac('sha256', secret)
		.update(payloadBase64)
		.digest('hex');

	const given = Buffer.from(signatureHex, 'utf8');
	const expected = Buffer.from(expectedSignature, 'utf8');

	if (given.length !== expected.length || !crypto.timingSafeEqual(given, expected)) {
		throw new Error('Invalid upload ticket.');
	}

	const payload = JSON.parse(Buffer.from(payloadBase64, 'base64').toString('utf8'));

	if (!payload.exp || Date.now() > payload.exp) {
		throw new Error('Upload ticket has expired - reload the page and try again.');
	}
}

async function readJsonBody(req) {

	if (req.body && typeof req.body === 'object') {
		return req.body;
	}

	const raw = await new Promise(function (resolve, reject) {

		let data = '';
		req.on('data', function (chunk) { data += chunk; });
		req.on('end', function () { resolve(data); });
		req.on('error', reject);
	});

	return raw ? JSON.parse(raw) : {};
}

module.exports = async function (req, res) {

	if (req.method !== 'POST') {
		res.status(405).json({ error: 'Method not allowed.' });
		return;
	}

	const ticketSecret = process.env.BLOB_UPLOAD_TICKET_SECRET;

	if (!ticketSecret) {
		res.status(500).json({ error: 'Direct-to-blob uploads are not configured on this deployment.' });
		return;
	}

	try {

		const body = await readJsonBody(req);

		const result = await handleUpload({
			body: body,
			request: req,
			onBeforeGenerateToken: async function (pathname, clientPayload) {

				verifyUploadTicket(clientPayload, ticketSecret);

				return {
					allowedContentTypes: ['application/pdf', 'text/csv', 'text/plain'],
					maximumSizeInBytes: 50 * 1024 * 1024,
					addRandomSuffix: true,
				};
			},
		});

		res.status(200).json(result);

	} catch (error) {

		res.status(400).json({ error: error.message || 'Upload token request failed.' });
	}
};
