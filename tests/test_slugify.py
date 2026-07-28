"""Unit tests for slug generation (dynamic-categories).

Slugs are the immutable public keys for taxonomy terms and appear in filter
URLs, so their derivation — Cyrillic transliteration, accent stripping, the
empty-input fallback, and collision suffixing — is exercised directly here.
"""

from app.utils.slugify import slugify, unique_slug


class TestSlugify:
    def test_basic_lowercase_hyphenation(self):
        assert slugify("Winter Gift") == "winter-gift"

    def test_collapses_punctuation_runs(self):
        assert slugify("Winter   Gift!!!") == "winter-gift"

    def test_trims_leading_and_trailing_hyphens(self):
        assert slugify("  --Hello--  ") == "hello"

    def test_strips_latin_accents_to_ascii(self):
        assert slugify("Café Déjà") == "cafe-deja"

    def test_transliterates_bulgarian_cyrillic(self):
        # Was the core bug: Cyrillic used to collapse to "item".
        assert slugify("Зима") == "zima"
        assert slugify("Свещи") == "sveshti"
        assert slugify("Коледа") == "koleda"

    def test_numeric_only_is_preserved(self):
        assert slugify("300") == "300"

    def test_empty_input_falls_back_to_item(self):
        assert slugify("") == "item"

    def test_all_punctuation_falls_back_to_item(self):
        assert slugify("$$$ !!!") == "item"

    def test_whitespace_only_falls_back_to_item(self):
        assert slugify("   ") == "item"


class TestUniqueSlug:
    def test_returns_base_when_free(self):
        assert unique_slug("gift", set()) == "gift"

    def test_suffixes_on_first_collision(self):
        assert unique_slug("gift", {"gift"}) == "gift-2"

    def test_increments_past_multiple_collisions(self):
        assert unique_slug("gift", {"gift", "gift-2"}) == "gift-3"

    def test_skips_already_taken_suffixes(self):
        assert unique_slug("gift", {"gift", "gift-2", "gift-3"}) == "gift-4"

    def test_does_not_mutate_existing_set(self):
        existing = {"gift"}
        unique_slug("gift", existing)
        assert existing == {"gift"}
