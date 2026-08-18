import hashlib
from datetime import datetime, timezone

import requests
from django.utils.dateparse import parse_datetime

from .base import BaseJobSource, ExternalJob


ARBEITNOW_API_URL = (
    "https://www.arbeitnow.com/api/job-board-api"
)


def clean_text(value):
    if value is None:
        return ""

    return str(value).strip()


def build_external_id(job_data):
    """
    Build a stable external id.

    Priority:
    1. Arbeitnow slug
    2. URL hash
    3. Fallback content hash
    """

    slug = clean_text(
        job_data.get("slug")
    )

    if slug:
        return slug


    url = clean_text(
        job_data.get("url")
    )

    if url:
        return hashlib.sha256(
            url.encode("utf-8")
        ).hexdigest()


    fallback = "|".join(
        [
            clean_text(
                job_data.get("title")
            ),
            clean_text(
                job_data.get("company_name")
            ),
            clean_text(
                job_data.get("location")
            ),
        ]
    )

    return hashlib.sha256(
        fallback.encode("utf-8")
    ).hexdigest()


def parse_published_at(value):
    """
    Convert Arbeitnow date values into
    timezone-aware datetime.
    """

    if not value:
        return None


    if isinstance(
        value,
        (int, float),
    ):
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


    value = str(
        value
    ).strip()


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
        timestamp = int(
            value
        )

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


class ArbeitnowJobSource(
    BaseJobSource
):
    source_name = "arbeitnow"

    def __init__(
        self,
        timeout=20,
    ):
        self.timeout = timeout


    def fetch_jobs(
        self,
        *,
        query=None,
        location=None,
        page=1,
    ):
        """
        Fetch one page from Arbeitnow and convert
        results to JobCopilot ExternalJob objects.

        Arbeitnow's public endpoint does not need
        authentication for this MVP.
        """

        response = requests.get(
            ARBEITNOW_API_URL,
            params={
                "page": page,
            },
            timeout=self.timeout,
            headers={
                "User-Agent": (
                    "JobCopilot/1.0 "
                    "(job discovery service)"
                ),
                "Accept": (
                    "application/json"
                ),
            },
        )

        response.raise_for_status()

        payload = response.json()


        raw_jobs = payload.get(
            "data",
            [],
        )


        if not isinstance(
            raw_jobs,
            list,
        ):
            raise ValueError(
                "Unexpected Arbeitnow API response."
            )


        results = []


        for raw_job in raw_jobs:

            external_job = (
                self.normalize_job(
                    raw_job
                )
            )


            if external_job is None:
                continue


            # ---------------------------------------------
            # Optional local query filtering
            # ---------------------------------------------

            if query:

                query_value = (
                    str(query)
                    .strip()
                    .lower()
                )

                searchable = (
                    " ".join(
                        [
                            external_job.title,
                            external_job.company,
                            external_job.description,
                        ]
                    )
                    .lower()
                )

                if (
                    query_value
                    not in searchable
                ):
                    continue


            # ---------------------------------------------
            # Optional local location filtering
            # ---------------------------------------------

            if location:

                location_value = (
                    str(location)
                    .strip()
                    .lower()
                )

                job_location = (
                    external_job.location
                    .lower()
                )

                if (
                    location_value
                    not in job_location
                    and not external_job.remote
                ):
                    continue


            results.append(
                external_job
            )


        return results


    def normalize_job(
        self,
        raw_job,
    ):
        """
        Convert one Arbeitnow job into
        JobCopilot's standard ExternalJob format.
        """

        title = clean_text(
            raw_job.get("title")
        )

        url = clean_text(
            raw_job.get("url")
        )


        if not title or not url:
            return None


        external_id = (
            build_external_id(
                raw_job
            )
        )


        company = clean_text(
            raw_job.get(
                "company_name"
            )
        )


        location = clean_text(
            raw_job.get(
                "location"
            )
        )


        description = clean_text(
            raw_job.get(
                "description"
            )
        )


        remote = bool(
            raw_job.get(
                "remote"
            )
        )


        published_at = (
            parse_published_at(
                raw_job.get(
                    "created_at"
                )
            )
        )


        return ExternalJob(
            source=self.source_name,
            external_id=external_id,
            title=title,
            company=company,
            location=location,
            description=description,
            url=url,
            remote=remote,
            published_at=published_at,
        )