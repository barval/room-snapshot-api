"""Tests for language selection and localized room names."""

from app.config import Camera
from app.i18n import (
    parse_accept_language,
    resolve_lang,
    room_name,
    room_names,
    supported_languages,
)

CAMERAS = {
    "kuh": Camera(code="kuh", ip="1.1.1.1", stream="554/s1", name="Kitchen", url="rtsp://1.1.1.1:554/s1")
}
I18N = {"kuh": {"ru": "Кухня", "en": "Kitchen"}}


def test_parse_accept_language_orders_by_quality():
    assert parse_accept_language("ru;q=0.9, en;q=0.8") == ["ru", "en"]


def test_parse_accept_language_strips_region_and_dedupes():
    assert parse_accept_language("en-US,en;q=0.9") == ["en"]


def test_parse_accept_language_empty_header():
    assert parse_accept_language(None) == []
    assert parse_accept_language("") == []


def test_parse_accept_language_single_unknown():
    assert parse_accept_language("de") == ["de"]


def test_resolve_lang_prefers_query():
    assert resolve_lang("ru", "en", "en", ["ru", "en"]) == "ru"


def test_resolve_lang_uses_accept_when_no_query():
    assert resolve_lang(None, "ru", "en", ["ru", "en"]) == "ru"


def test_resolve_lang_unknown_falls_back_to_default():
    assert resolve_lang("de", "de", "en", ["ru", "en"]) == "en"
    assert resolve_lang(None, None, "en", ["ru", "en"]) == "en"


def test_resolve_lang_unsupported_query_falls_back():
    assert resolve_lang("de", None, "en", ["ru", "en"]) == "en"


def test_room_name_uses_translation():
    assert room_name("kuh", "en", CAMERAS, I18N) == "Kitchen"
    assert room_name("kuh", "ru", CAMERAS, I18N) == "Кухня"


def test_room_name_falls_back_to_camera_name():
    assert room_name("kuh", "de", CAMERAS, I18N) == "Kitchen"
    assert room_name("kuh", "en", CAMERAS, {}) == "Kitchen"


def test_room_names_includes_default_and_translations():
    assert room_names("kuh", CAMERAS, I18N) == {
        "default": "Kitchen",
        "ru": "Кухня",
        "en": "Kitchen",
    }


def test_room_names_default_only_without_translations():
    assert room_names("kuh", CAMERAS, {}) == {"default": "Kitchen"}


def test_supported_languages_default_first():
    assert supported_languages(I18N, "en") == ["en", "ru"]
    assert supported_languages(I18N, "ru") == ["ru", "en"]
