"""infrastructure/telegram_handler.py's reply formatting — Telegram's
HTML parse_mode is more forgiving than MarkdownV2's ~18-character escape
requirement, but still needs the assistant's actual markdown constructs
(bold, links, code, headings, bullets) translated deliberately, and long
replies split under Telegram's 4096-char message cap."""

from metaforge_api.infrastructure.telegram_handler import markdown_to_telegram_html, split_for_telegram


def test_bold_italic_code():
    out = markdown_to_telegram_html("**bold** and *italic* and `code`", base_url=None)
    assert out == "<b>bold</b> and <i>italic</i> and <code>code</code>"


def test_fenced_code_block():
    out = markdown_to_telegram_html("```\nline1\nline2\n```", base_url=None)
    assert out == "<pre>line1\nline2\n</pre>"


def test_internal_link_with_base_url():
    out = markdown_to_telegram_html("[Acme Corp](/vendors/abc-123)", base_url="http://localhost:5173")
    assert out == '<a href="http://localhost:5173/vendors/abc-123">Acme Corp</a>'


def test_internal_link_without_base_url_drops_to_plain_label():
    out = markdown_to_telegram_html("[Acme Corp](/vendors/abc-123)", base_url=None)
    assert out == "Acme Corp"


def test_external_or_non_module_link_not_absolutized():
    # Only "/module/id"-shaped targets get absolutized; anything else is
    # left as plain label text rather than risking a bad href.
    out = markdown_to_telegram_html("[docs](https://example.com/x)", base_url="http://localhost:5173")
    assert "example.com" not in out
    assert out == "docs"


def test_html_special_chars_escaped_in_prose():
    out = markdown_to_telegram_html("A & B < C > D", base_url=None)
    assert out == "A &amp; B &lt; C &gt; D"


def test_heading_and_bullets():
    out = markdown_to_telegram_html("# Title\n- one\n- two", base_url=None)
    assert out == "<b>Title</b>\n• one\n• two"


def test_split_under_limit_passthrough():
    text = "short reply"
    assert split_for_telegram(text, limit=4000) == [text]


def test_split_breaks_at_newline():
    text = ("a" * 10 + "\n") * 500  # well over the limit, has newlines to break on
    parts = split_for_telegram(text, limit=100)
    assert len(parts) > 1
    assert all(len(p) <= 100 for p in parts)
    assert "".join(parts).replace("\n", "") == text.replace("\n", "")


def test_split_hard_cuts_a_monster_line_with_no_newlines():
    text = "x" * 250
    parts = split_for_telegram(text, limit=100)
    assert len(parts) == 3
    assert "".join(parts) == text


def test_split_preserves_order():
    text = "\n".join(f"line{i} " + "x" * 20 for i in range(50))
    parts = split_for_telegram(text, limit=200)
    assert len(parts) > 1
    assert "\n".join(parts) == text
