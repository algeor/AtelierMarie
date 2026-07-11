"""Unit tests for app/utils/sanitize.py."""

from app.utils.sanitize import contains_blocked_word, is_url_only, sanitize_text


class TestSanitizeText:
    """Tests for html.escape behavior."""

    def test_escapes_angle_brackets(self):
        assert sanitize_text("<script>alert('xss')</script>") == (
            "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;"
        )

    def test_escapes_ampersand(self):
        assert sanitize_text("A & B") == "A &amp; B"

    def test_escapes_quotes(self):
        assert sanitize_text('She said "hello"') == "She said &quot;hello&quot;"

    def test_preserves_normal_text(self):
        text = "I love this candle! Great scent."
        assert sanitize_text(text) == text

    def test_preserves_comparison_symbols_as_entities(self):
        text = "I love candles < 8oz but > 4oz"
        result = sanitize_text(text)
        assert result == "I love candles &lt; 8oz but &gt; 4oz"
        # Content preserved (no data lost)
        assert "&lt;" in result
        assert "&gt;" in result

    def test_escapes_single_quotes(self):
        assert sanitize_text("it's great") == "it&#x27;s great"


class TestIsUrlOnly:
    """Tests for URL-only detection."""

    def test_http_url_detected(self):
        assert is_url_only("http://example.com") is True

    def test_https_url_detected(self):
        assert is_url_only("https://example.com/page?q=1") is True

    def test_url_with_whitespace_detected(self):
        assert is_url_only("  https://example.com  ") is True

    def test_url_embedded_in_text_allowed(self):
        assert is_url_only("Check out https://example.com for details") is False

    def test_no_protocol_not_detected(self):
        assert is_url_only("example.com") is False

    def test_ftp_not_detected(self):
        assert is_url_only("ftp://files.example.com") is False

    def test_plain_text_not_detected(self):
        assert is_url_only("I love this candle") is False

    def test_empty_string_not_detected(self):
        assert is_url_only("") is False


class TestContainsBlockedWord:
    """Tests for blocklist checking."""

    def test_blocked_word_detected(self):
        assert contains_blocked_word("I am the admin here") is True

    def test_case_insensitive(self):
        assert contains_blocked_word("ADMIN") is True
        assert contains_blocked_word("Admin") is True

    def test_substring_match(self):
        assert contains_blocked_word("administrator account") is True

    def test_clean_text_passes(self):
        assert contains_blocked_word("I love this candle!") is False

    def test_partial_overlap_not_in_list(self):
        # "ad" is not in blocklist even though "admin" is
        assert contains_blocked_word("This is a nice ad") is False
