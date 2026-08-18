from datetime import timezone

import requests
from django.conf import settings
from django.utils.dateparse import parse_datetime

from .base import BaseJobSource, ExternalJob


JOOBLE_API_BASE_URL = "https://de.jooble.org/api"


class JoobleJobSource(BaseJobSource):
    source_name = "jooble"

    def __init__(
        self,
        timeout=25,
    ):
        self.timeout = timeout


    # =====================================================
    # FETCH JOBS
    # =====================================================

    def fetch_jobs(
        self,
        *,
        query=None,
        location=None,
        page=1,
    ):
        api_key = (
            settings.JOOBLE_API_KEY
            or ""
        ).strip()

        if not api_key:
            raise ValueError(
                "JOOBLE_API_KEY is not configured."
            )

        url = (
            f"{JOOBLE_API_BASE_URL}/"
            f"{api_key}"
        )

        payload = {
            "keywords": (
                str(query).strip()
                if query
                else ""
            ),
            "location": (
                self._clean_location(
                    location
                )
            ),
            "page": int(
                page
                or 1
            ),
        }

        response = requests.post(
            url,
            json=payload,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "JobCopilot/1.0",
            },
            timeout=self.timeout,
        )

        if response.status_code != 200:
            raise RuntimeError(
                (
                    "Jooble API request failed. "
                    f"Status={response.status_code}. "
                    f"Body={response.text[:500]}"
                )
            )

        data = response.json()

        raw_jobs = (
            data.get("jobs")
            or []
        )

        if not isinstance(
            raw_jobs,
            list,
        ):
            raise ValueError(
                "Unexpected Jooble response format."
            )

        results = []

        for raw_job in raw_jobs:
            try:
                job = self.normalize_job(
                    raw_job
                )

                if job is not None:
                    results.append(
                        job
                    )

            except Exception as exc:
                print(
                    "JOOBLE NORMALIZE ERROR:",
                    repr(exc),
                )

        return results


    # =====================================================
    # NORMALIZE JOB
    # =====================================================

    def normalize_job(
        self,
        raw_job,
    ):
        if not isinstance(
            raw_job,
            dict,
        ):
            return None

        title = str(
            raw_job.get(
                "title"
            )
            or ""
        ).strip()

        company = str(
            raw_job.get(
                "company"
            )
            or ""
        ).strip()

        location = str(
            raw_job.get(
                "location"
            )
            or ""
        ).strip()

        description = str(
            raw_job.get(
                "snippet"
            )
            or raw_job.get(
                "description"
            )
            or ""
        ).strip()

        url = str(
            raw_job.get(
                "link"
            )
            or raw_job.get(
                "url"
            )
            or ""
        ).strip()

        external_id = str(
            raw_job.get(
                "id"
            )
            or url
            or ""
        ).strip()

        if not title:
            return None

        if not external_id:
            return None

        published_at = (
            self._parse_date(
                raw_job.get(
                    "updated"
                )
                or raw_job.get(
                    "created"
                )
            )
        )

        remote = (
            self._detect_remote(
                title=title,
                location=location,
                description=description,
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


    # =====================================================
    # LOCATION
    # =====================================================

    def _clean_location(
        self,
        location,
    ):
        if not location:
            return ""

        value = str(
            location
        ).strip()

        normalized = (
            value
            .lower()
            .replace("ä", "ae")
            .replace("ö", "oe")
            .replace("ü", "ue")
            .replace("ß", "ss")
        )

        # Country-wide Germany search.
        # Jooble's German endpoint already scopes us
        # to the German market, so broad country names
        # can be omitted.
        if normalized in {
            "germany",
            "deutschland",
            "de",
        }:
            return ""

        return value


    # =====================================================
    # DATE
    # =====================================================

    def _parse_date(
        self,
        value,
    ):
        if not value:
            return None

        value = str(
            value
        ).strip()

        parsed = parse_datetime(
            value
        )

        if not parsed:
            return None

        if parsed.tzinfo is None:
            parsed = parsed.replace(
                tzinfo=timezone.utc
            )

        return parsed


    # =====================================================
    # REMOTE
    # =====================================================

    def _detect_remote(
        self,
        *,
        title,
        location,
        description,
    ):
        text = " ".join(
            [
                title or "",
                location or "",
                description or "",
            ]
        ).casefold()

        terms = [
            "remote",
            "homeoffice",
            "home office",
            "mobiles arbeiten",
            "mobile arbeit",
            "telearbeit",
        ]

        return any(
            term in text
            for term in terms
        )