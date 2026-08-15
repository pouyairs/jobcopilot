from .i18n import TRANSLATIONS


def ui_language(request):

    lang = request.session.get("ui_language")

    if not lang and request.user.is_authenticated:
        try:
            lang = request.user.profile.preferred_language
        except Exception:
            lang = "en"

    if lang not in TRANSLATIONS:
        lang = "en"

    return {
        "ui_lang": lang,
        "t": TRANSLATIONS[lang],
    }