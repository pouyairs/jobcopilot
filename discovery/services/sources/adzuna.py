from datetime import datetime, timezone

import requests
from django.conf import settings
from django.utils.dateparse import parse_datetime

from .base import BaseJobSource, ExternalJob


ADZUNA_SEARCH_URL = (
    "https://api.adzuna.com/v1/api/jobs/de/search"
)


GERMANY_WIDE_LOCATIONS = {
    "germany",
    "deutschland",
    "de",
}


class AdzunaJobSource(BaseJobSource):
    source_name = "adzuna"

    def __init__(
        self,
        timeout=25,
        results_per_page=50,
    ):
        self.timeout = timeout
        self.results_per_page = (
            results_per_page
        )


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
        app_id = (
            settings.ADZUNA_APP_ID
            or ""
        ).strip()

        app_key = (
            settings.ADZUNA_APP_KEY
            or ""
        ).strip()

        if not app_id:
            raise ValueError(
                "ADZUNA_APP_ID is not configured."
            )

        if not app_key:
            raise ValueError(
                "ADZUNA_APP_KEY is not configured."
            )

        url = (
            f"{ADZUNA_SEARCH_URL}/"
            f"{page}"
        )

        params = {
            "app_id": app_id,
            "app_key": app_key,
            "results_per_page": (
                self.results_per_page
            ),
            "content-type": (
                "application/json"
            ),
        }

        if query:
            params["what"] = str(
                query
            ).strip()

        cleaned_location = (
            self._clean_location(
                location
            )
        )

        if cleaned_location:
            params["where"] = (
                cleaned_location
            )

        response = requests.get(
            url,
            params=params,
            timeout=self.timeout,
        )

        response.raise_for_status()

        data = response.json()

        raw_jobs = (
            data.get("results")
            or []
        )

        if not isinstance(
            raw_jobs,
            list,
        ):
            raise ValueError(
                "Unexpected Adzuna response format."
            )

        results = []

        for raw_job in raw_jobs:
            try:
                job = self.normalize_job(
                    raw_job
                )

                if job:
                    results.append(
                        job
                    )

            except Exception as exc:
                print(
                    "ADZUNA NORMALIZE ERROR:",
                    repr(exc),
                )

        return results


    # =====================================================
    # NORMALIZE
    # =====================================================

    def normalize_job(
        self,
        raw_job,
    ):
        title = str(
            raw_job.get(
                "title"
            )
            or ""
        ).strip()

        company_data = (
            raw_job.get(
                "company"
            )
            or {}
        )

        company = str(
            company_data.get(
                "display_name"
            )
            or ""
        ).strip()

        location_data = (
            raw_job.get(
                "location"
            )
            or {}
        )

        location = str(
            location_data.get(
                "display_name"
            )
            or ""
        ).strip()

        description = str(
            raw_job.get(
                "description"
            )
            or ""
        ).strip()

        url = str(
            raw_job.get(
                "redirect_url"
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

        if (
            normalized
            in GERMANY_WIDE_LOCATIONS
        ):
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

        if parsed:
            if parsed.tzinfo is None:
                parsed = parsed.replace(
                    tzinfo=timezone.utc
                )

            return parsed

        try:
            parsed = datetime.fromisoformat(
                value.replace(
                    "Z",
                    "+00:00",
                )
            )

            if parsed.tzinfo is None:
                parsed = parsed.replace(
                    tzinfo=timezone.utc
                )

            return parsed

        except ValueError:
            return None


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