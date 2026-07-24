"""Jinja2 template rendering for emails.

Templates are plain-text `.txt` files under `templates/{locale}/`, subject on
the first line, blank line, then body (Decision 5). autoescape is OFF — for
plain text, HTML-escaping is a bug (`Ben & Co` must stay literal, Decision 20).
When HTML/multipart templates are added later, autoescape MUST be enabled for
`.html`.
"""

from pathlib import Path

import structlog
from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape

logger = structlog.get_logger(__name__)

_TEMPLATES_DIR = Path(__file__).parent / "templates"

# autoescape=False for .txt; select_autoescape leaves the door open for .html.
_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(enabled_extensions=("html",), default=False),
    trim_blocks=True,
    lstrip_blocks=True,
)

_FALLBACK_LOCALE = "en"


class TemplateMissingError(Exception):
    """Raised when neither the requested-locale nor the EN fallback exists."""


def _template_filename(event: str) -> str:
    """Map an EmailEvent to its template file.

    admin_new_order keeps its own name; the customer events use the
    `order_{event}.txt` form (Decision 19).
    """
    if event in {"admin_new_order", "contact_message"}:
        return f"{event}.txt"
    return f"order_{event}.txt"


def render_template(event: str, locale: str, context: dict) -> tuple[str, str]:
    """Render an email template to `(subject, body)`.

    Locale fallback: requested locale → English → raise TemplateMissingError.
    The subject is the first rendered line; the body is everything after the
    first blank-line separator (a single '\\n' split, so a template with no
    blank line still yields an empty-ish body rather than crashing).
    """
    filename = _template_filename(event)
    candidates = [f"{locale}/{filename}"]
    if locale != _FALLBACK_LOCALE:
        candidates.append(f"{_FALLBACK_LOCALE}/{filename}")

    template = None
    for candidate in candidates:
        try:
            template = _env.get_template(candidate)
            if candidate != candidates[0]:
                logger.warning(
                    "email_template_locale_fallback",
                    email_event=event,
                    requested_locale=locale,
                    used=candidate,
                )
            break
        except TemplateNotFound:
            continue

    if template is None:
        logger.error(
            "email_template_missing",
            email_event=event,
            locale=locale,
            filename=filename,
            searched=candidates,
        )
        raise TemplateMissingError(
            f"No template for event={event} locale={locale} (searched {candidates})"
        )

    rendered = template.render(**context)
    subject, _, body = rendered.partition("\n\n")
    return subject.strip(), body.strip()
