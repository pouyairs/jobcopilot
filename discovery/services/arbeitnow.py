import hashlib
from datetime import datetime, timezone

import requests
from django.utils.dateparse import parse_datetime

from discovery.models import DiscoveredJob


ARBEITNOW_API_URL = "https://www.arbeitnow.com/api/job-board-api"


def _clean_text(value):
    if value is None:
        return ""

    return str(value).strip()


def _build_external_id(job_data):
    """
    Arbeitnow may provide a slug or URL that can identify
    a vacancy. If not, we create a stable fallback hash.
    """

    slug = _clean_text(
        job_data.get("slug")
    )

    if slug:
        return slug


    url = _clean_text(
        job_data.get("url")
    )

    if url:
        return hashlib.sha256(
            url.encode("utf-8")
        ).hexdigest()


    fallback = "|".join(
        [
            _clean_text(job_data.get("title")),
            _clean_text(job_data.get("company_name")),
            _clean_text(job_data.get("location")),
        ]
    )

    return hashlib.sha256(
        fallback.encode("utf-8")
    ).hexdigest()


def _parse_published_at(value):
    """
    Convert API date values into timezone-aware datetime.
    """

    if not value:
        return None


    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(
                value,
                tz=timezone.utc,
            )
        except (
            ValueError,
            OSError,
            OverflowError,
        ):
            return None


    value = str(value).strip()


    parsed = parse_datetime(
        value
    )

    if parsed:
        if parsed.tzinfo is None:
            parsed = parsed.replace(
                tzinfo=timezone.utc
            )

        return parsed


    try:
        timestamp = int(value)

        return datetime.fromtimestamp(
            timestamp,
            tz=timezone.utc,
        )

    except (
        ValueError,
        OSError,
        OverflowError,
    ):
        return None


def fetch_arbeitnow_page(
    page=1,
    timeout=20,
):
    """
    Fetch one page of vacancies from Arbeitnow.
    """

    response = requests.get(
        ARBEITNOW_API_URL,
        params={
            "page": page,
        },
        timeout=timeout,
        headers={
            "User-Agent": (
                "JobCopilot/1.0 "
                "(job discovery service)"
            ),
            "Accept": "application/json",
        },
    )

    response.raise_for_status()

    payload = response.json()

    jobs = payload.get(
        "data",
        [],
    )

    if not isinstance(
        jobs,
        list,
    ):
        raise ValueError(
            "Unexpected Arbeitnow API response."
        )

    return {
        "jobs": jobs,
        "links": payload.get(
            "links",
            {},
        ),
        "meta": payload.get(
            "meta",
            {},
        ),
    }


def save_arbeitnow_job(
    job_data,
):
    """
    Normalize one Arbeitnow vacancy and save/update it.
    """

    title = _clean_text(
        job_data.get("title")
    )

    url = _clean_text(
        job_data.get("url")
    )


    if not title or not url:
        return None, False


    external_id = _build_external_id(
        job_data
    )


    company = _clean_text(
        job_data.get("company_name")
    )

    location = _clean_text(
        job_data.get("location")
    )

    description = _clean_text(
        job_data.get("description")
    )

    remote = bool(
        job_data.get("remote")
    )

    published_at = _parse_published_at(
        job_data.get("created_at")
    )


    job, created = (
        DiscoveredJob.objects.update_or_create(
            source="arbeitnow",
            external_id=external_id,

            defaults={
                "title": title,
                "company": company,
                "location": location,
                "description": description,
                "url": url,
                "remote": remote,
                "published_at": published_at,
                "is_active": True,
            },
        )
    )

    return job, created


def import_arbeitnow_jobs(
    pages=3,
):
    """
    Import multiple pages from Arbeitnow.

    Returns basic statistics.
    """

    created_count = 0
    updated_count = 0
    skipped_count = 0
    fetched_count = 0


    for page in range(
        1,
        pages + 1,
    ):

        payload = fetch_arbeitnow_page(
            page=page
        )


        for job_data in payload["jobs"]:

            fetched_count += 1


            job, created = (
                save_arbeitnow_job(
                    job_data
                )
            )


            if job is None:
                skipped_count += 1
                continue


            if created:
                created_count += 1

            else:
                updated_count += 1


    return {
        "fetched": fetched_count,
        "created": created_count,
        "updated": updated_count,
        "skipped": skipped_count,
    }