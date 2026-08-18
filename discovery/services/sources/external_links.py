from urllib.parse import quote_plus


def _clean(value):
    if not value:
        return ""

    return str(value).strip()


def _slugify_for_path(value):
    """
    Simple URL path slug for sites such as StepStone/XING.
    Keeps this dependency-free and predictable.
    """

    value = _clean(value).lower()

    replacements = {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss",
        "/": "-",
        "\\": "-",
        "_": "-",
        " ": "-",
    }

    for old, new in replacements.items():
        value = value.replace(
            old,
            new,
        )

    while "--" in value:
        value = value.replace(
            "--",
            "-",
        )

    return value.strip("-")


# =========================================================
# LINK BUILDERS
# =========================================================

def build_linkedin_search_url(
    title,
    location="",
):
    """
    LinkedIn public job search.

    Example:
    /jobs/search/?keywords=IT+Support&location=Germany
    """

    title = _clean(
        title
    )

    location = _clean(
        location
    )

    params = []

    if title:
        params.append(
            f"keywords={quote_plus(title)}"
        )

    if location:
        params.append(
            f"location={quote_plus(location)}"
        )

    query_string = "&".join(
        params
    )

    base_url = (
        "https://www.linkedin.com/jobs/search/"
    )

    if query_string:
        return (
            f"{base_url}?{query_string}"
        )

    return base_url


def build_indeed_search_url(
    title,
    location="",
):
    """
    Indeed Germany job search.

    q = query
    l = location
    """

    title = _clean(
        title
    )

    location = _clean(
        location
    )

    params = []

    if title:
        params.append(
            f"q={quote_plus(title)}"
        )

    if location:
        params.append(
            f"l={quote_plus(location)}"
        )

    query_string = "&".join(
        params
    )

    base_url = (
        "https://de.indeed.com/jobs"
    )

    if query_string:
        return (
            f"{base_url}?{query_string}"
        )

    return base_url


def build_arbeitsagentur_search_url(
    title,
    location="",
    radius_km=None,
):
    """
    Bundesagentur für Arbeit Jobsuche.

    was = keyword / job title
    wo = location
    umkreis = radius
    """

    title = _clean(
        title
    )

    location = _clean(
        location
    )

    params = [
        "angebotsart=1",
        "sort=Relevanz",
    ]

    if title:
        params.append(
            f"was={quote_plus(title)}"
        )

    if location:
        params.append(
            f"wo={quote_plus(location)}"
        )

    if radius_km:

        try:
            radius_value = int(
                radius_km
            )

            if radius_value > 0:
                params.append(
                    f"umkreis={radius_value}"
                )

        except (
            TypeError,
            ValueError,
        ):
            pass

    return (
        "https://www.arbeitsagentur.de/"
        "jobsuche/suche?"
        + "&".join(params)
    )


def build_stepstone_search_url(
    title,
    location="",
):
    """
    StepStone Germany SEO-style search URL.

    Example:
    /jobs/it-support/in-berlin
    """

    title_slug = (
        _slugify_for_path(
            title
        )
    )

    location_slug = (
        _slugify_for_path(
            location
        )
    )

    base_url = (
        "https://www.stepstone.de/jobs"
    )

    if (
        title_slug
        and location_slug
    ):
        return (
            f"{base_url}/"
            f"{quote_plus(title_slug)}"
            f"/in-"
            f"{quote_plus(location_slug)}"
        )

    if title_slug:
        return (
            f"{base_url}/"
            f"{quote_plus(title_slug)}"
        )

    return base_url


def build_xing_search_url(
    title,
    location="",
):
    """
    XING does not expose the same simple public query parameter
    pattern as LinkedIn/Indeed.

    For MVP we use XING's keyword/job-title path where possible.
    """

    title_slug = (
        _slugify_for_path(
            title
        )
    )

    if title_slug:
        return (
            "https://www.xing.com/jobs/"
            f"{quote_plus(title_slug)}"
        )

    return (
        "https://www.xing.com/jobs"
    )


# =========================================================
# ALL SOURCES FOR ONE TARGET
# =========================================================

def build_external_search_links(
    target,
):
    """
    Build all external search links for one JobSearchTarget.

    Returns a list ready for the template.
    """

    title = _clean(
        target.title
    )

    location = _clean(
        target.location
    )

    radius_km = getattr(
        target,
        "radius_km",
        None,
    )

    return [
        {
            "key": "linkedin",
            "name": "LinkedIn",
            "url": build_linkedin_search_url(
                title=title,
                location=location,
            ),
        },

        {
            "key": "indeed",
            "name": "Indeed",
            "url": build_indeed_search_url(
                title=title,
                location=location,
            ),
        },

        {
            "key": "stepstone",
            "name": "StepStone",
            "url": build_stepstone_search_url(
                title=title,
                location=location,
            ),
        },

        {
            "key": "xing",
            "name": "XING",
            "url": build_xing_search_url(
                title=title,
                location=location,
            ),
        },

        {
            "key": "arbeitsagentur",
            "name": "Agentur für Arbeit",
            "url": build_arbeitsagentur_search_url(
                title=title,
                location=location,
                radius_km=radius_km,
            ),
        },
    ]


# =========================================================
# ALL TARGETS FOR ONE USER
# =========================================================

def build_user_external_searches(
    user,
):
    """
    Build external-search groups for all active targets
    belonging to one user.
    """

    targets = (
        user.job_search_targets
        .filter(
            active=True
        )
        .order_by(
            "title"
        )
    )

    results = []

    for target in targets:

        results.append(
            {
                "target": target,
                "links": (
                    build_external_search_links(
                        target
                    )
                ),
            }
        )

    return results