/** Minimal, safe markdown -> HTML for AI chat replies: bold, italic, inline
 * code, bullet/numbered lists, paragraphs, and links to ERP records
 * (`[label](/module/id)` — the system prompt in ai_chat.py instructs the
 * assistant to hotlink any specific record it mentions this way, using the
 * module/id from whatever tool result surfaced it). Deliberately not a
 * full CommonMark implementation — chat replies use a narrow subset, and a
 * hand-rolled version avoids pulling in a markdown dependency for what's
 * essentially a handful of regexes.
 *
 * Security: the input can contain LLM-echoed text sourced from database
 * records (vendor names, etc.), so it is HTML-escaped FIRST — every tag
 * this function emits is one it generates itself, never raw input. Link
 * targets are additionally allowlisted to the exact `/module/id` shape
 * (see isSafeInternalUrl) so a record name crafted to look like markdown
 * link syntax can never smuggle a `javascript:`/external/off-shape URL
 * past this renderer, even if it tricks the model into emitting one. */

function escapeHtml(s: string): string {
	return s
		.replace(/&/g, '&amp;')
		.replace(/</g, '&lt;')
		.replace(/>/g, '&gt;')
		.replace(/"/g, '&quot;')
		.replace(/'/g, '&#39;');
}

/** Only ERP record deep links: /{module}/{id} — module is a lowercase
 * snake_case name, id is whatever dynamic_tables.py's uuidv7() produces
 * (hex + hyphens). Rejects everything else: javascript:, http(s)://,
 * protocol-relative //, query strings/fragments, extra path segments. */
function isSafeInternalUrl(url: string): boolean {
	return /^\/[a-z][a-z0-9_]*\/[0-9a-zA-Z-]{8,64}$/.test(url);
}

function inline(text: string): string {
	return text
		.replace(/`([^`]+)`/g, '<code>$1</code>')
		.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (match, label: string, url: string) =>
			isSafeInternalUrl(url) ? `<a href="${url}" class="chat-link">${label}</a>` : label
		)
		.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
		.replace(/(?<!\*)\*([^*\n]+)\*(?!\*)/g, '<em>$1</em>');
}

/** Strips markdown down to speech-friendly plain text, for the "read
 * replies aloud" TTS feature — a raw reply like "see [Acme Steel
 * Supply](/vendors/019fff1c-...)" makes speechSynthesis read the record's
 * UUID/URL out loud character by character, which is what sounded "weird".
 * Links keep only their visible label, everything else drops its markup
 * but keeps its text. No LLM involved — this is a pure string transform on
 * the same reply already shown on screen, so it costs nothing extra to
 * compute and never adds a request. */
export function stripMarkdownForSpeech(raw: string): string {
	return raw
		.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
		.replace(/`([^`]+)`/g, '$1')
		.replace(/\*\*([^*]+)\*\*/g, '$1')
		.replace(/(?<!\*)\*([^*\n]+)\*(?!\*)/g, '$1')
		.replace(/^\s*[-*]\s+/gm, '')
		.replace(/^\s*\d+\.\s+/gm, '')
		.trim();
}

export function renderMarkdown(raw: string): string {
	const lines = escapeHtml(raw).split('\n');
	const out: string[] = [];
	let listType: 'ul' | 'ol' | null = null;

	function closeList() {
		if (listType) {
			out.push(listType === 'ul' ? '</ul>' : '</ol>');
			listType = null;
		}
	}

	for (const line of lines) {
		const bullet = line.match(/^\s*[-*]\s+(.*)$/);
		const numbered = line.match(/^\s*\d+\.\s+(.*)$/);
		if (bullet) {
			if (listType !== 'ul') {
				closeList();
				out.push('<ul>');
				listType = 'ul';
			}
			out.push(`<li>${inline(bullet[1])}</li>`);
		} else if (numbered) {
			if (listType !== 'ol') {
				closeList();
				out.push('<ol>');
				listType = 'ol';
			}
			out.push(`<li>${inline(numbered[1])}</li>`);
		} else if (line.trim() === '') {
			closeList();
		} else {
			closeList();
			out.push(`<p>${inline(line)}</p>`);
		}
	}
	closeList();
	return out.join('');
}
