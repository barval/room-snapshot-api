"""Language selection and localized room names."""

from __future__ import annotations

from app.config import Camera


def parse_accept_language(header: str | None) -> list[str]:
    """Return language codes from an ``Accept-Language`` header, best first."""
    if not header:
        return []
    weighted: list[tuple[str, float]] = []
    for part in header.split(","):
        part = part.strip()
        if not part:
            continue
        lang, _, params = part.partition(";")
        lang = lang.strip().lower().split("-")[0]
        if not lang:
            continue
        quality = 1.0
        for param in params.split(";"):
            param = param.strip()
            if param.startswith("q="):
                try:
                    quality = float(param[2:])
                except ValueError:
                    quality = 1.0
        weighted.append((lang, quality))
    weighted.sort(key=lambda item: item[1], reverse=True)
    ordered: list[str] = []
    for lang, _ in weighted:
        if lang not in ordered:
            ordered.append(lang)
    return ordered


def resolve_lang(
    query_lang: str | None,
    accept_language: str | None,
    default: str,
    supported: list[str],
) -> str:
    """Resolve the request language: query, then Accept-Language, then default."""
    if query_lang:
        candidate = query_lang.strip().lower().split("-")[0]
        if candidate in supported:
            return candidate
    for candidate in parse_accept_language(accept_language):
        if candidate in supported:
            return candidate
    if default in supported:
        return default
    if supported:
        return supported[0]
    return default


def room_name(
    code: str, lang: str, cameras: dict[str, Camera], i18n: dict[str, dict[str, str]]
) -> str:
    """Return the room label in ``lang``, falling back to the camera's default name."""
    translations = i18n.get(code, {})
    if lang in translations:
        return translations[lang]
    camera = cameras.get(code)
    return camera.name if camera else code


def room_names(
    code: str, cameras: dict[str, Camera], i18n: dict[str, dict[str, str]]
) -> dict[str, str]:
    """Return every known label for a room, including the default fallback."""
    camera = cameras.get(code)
    names = {"default": camera.name if camera else code}
    names.update(i18n.get(code, {}))
    return names


def supported_languages(i18n: dict[str, dict[str, str]], default: str) -> list[str]:
    """Return all languages present in the translations, with the default first."""
    languages = {lang for names in i18n.values() for lang in names}
    if default:
        languages.add(default)
    ordered = sorted(languages)
    if default in ordered:
        ordered.remove(default)
        ordered.insert(0, default)
    return ordered
