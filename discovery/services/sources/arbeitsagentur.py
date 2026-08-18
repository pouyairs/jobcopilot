import base64
import hashlib
import html
from datetime import datetime, timezone

import requests
from django.utils.dateparse import parse_datetime

from discovery.models import DiscoveredJob

from .base import BaseJobSource, ExternalJob


SEARCH_URL = (
    "https://rest.arbeitsagentur.de/"
    "jobboerse/jobsuche-service/pc/v6/jobs"
)

DETAIL_URL = (
    "https://rest.arbeitsagentur.de/"
    "jobboerse/jobsuche-service/pc/v4/jobdetails"
)


class ArbeitsagenturJobSource(BaseJobSource):
    source_name = "arbeitsagentur"

    def __init__(
        self,
        timeout=25,
        fetch_details=True,
        reuse_existing_description=True,
    ):
        self.timeout = timeout

        self.fetch_details = (
            fetch_details
        )

        self.reuse_existing_description = (
            reuse_existing_description
        )


    # =====================================================
    # HEADERS
    # =====================================================

    def _headers(self):
        return {
            "Accept": "application/json",
            "X-API-Key": "jobboerse-jobsuche",
            "User-Agent": "JobCopilot/1.0",
        }


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
        params = {
            "angebotsart": 1,
            "page": page,
            "size": 50,
        }

        if query:
            params["was"] = str(
                query
            ).strip()

        if location:
            params["wo"] = str(
                location
            ).strip()

        response = requests.get(
            SEARCH_URL,
            headers=self._headers(),
            params=params,
            timeout=self.timeout,
        )

        response.raise_for_status()

        payload = response.json()

        raw_jobs = (
            payload.get(
                "ergebnisliste"
            )
            or []
        )

        if not isinstance(
            raw_jobs,
            list,
        ):
            raise ValueError(
                "Unexpected Arbeitsagentur "
                "response format."
            )

        # -------------------------------------------------
        # Load existing BA jobs in ONE database query.
        #
        # This prevents one DB query for each search result.
        # -------------------------------------------------

        reference_numbers = []

        for raw_job in raw_jobs:
            reference = str(
                raw_job.get(
                    "referenznummer"
                )
                or ""
            ).strip()

            if reference:
                reference_numbers.append(
                    reference
                )

        existing_jobs = {}

        if (
            self.reuse_existing_description
            and reference_numbers
        ):
            queryset = (
                DiscoveredJob.objects.filter(
                    source=self.source_name,
                    external_id__in=(
                        reference_numbers
                    ),
                )
                .only(
                    "external_id",
                    "description",
                )
            )

            existing_jobs = {
                job.external_id: job
                for job in queryset
            }

        # -------------------------------------------------
        # Normalize
        # -------------------------------------------------

        results = []

        for raw_job in raw_jobs:
            try:
                reference = str(
                    raw_job.get(
                        "referenznummer"
                    )
                    or ""
                ).strip()

                existing_job = (
                    existing_jobs.get(
                        reference
                    )
                )

                job = self.normalize_job(
                    raw_job,
                    existing_job=existing_job,
                )

                if job is not None:
                    results.append(
                        job
                    )

            except Exception as exc:
                print(
                    "ARBEITSAGENTUR "
                    "NORMALIZE ERROR:",
                    repr(exc),
                )

        return results


    # =====================================================
    # NORMALIZE JOB
    # =====================================================

    def normalize_job(
        self,
        raw_job,
        existing_job=None,
    ):
        reference_number = str(
            raw_job.get(
                "referenznummer"
            )
            or ""
        ).strip()

        title = str(
            raw_job.get(
                "stellenangebotsTitel"
            )
            or ""
        ).strip()

        company = str(
            raw_job.get(
                "firma"
            )
            or ""
        ).strip()

        location = (
            self._extract_location(
                raw_job
            )
        )

        published_at = (
            self._extract_published_at(
                raw_job
            )
        )

        description = ""
        detail_data = {}

        # =================================================
        # EXISTING DESCRIPTION CACHE
        # =================================================
        #
        # If this vacancy already exists in our DB and has
        # a full description, reuse it.
        #
        # No BA Detail API request is made.
        # =================================================

        if (
            existing_job is not None
            and existing_job.description
        ):
            description = (
                existing_job.description
            )

        # =================================================
        # DETAIL REQUEST
        # =================================================
        #
        # Only fetch details when:
        # - detail fetching is enabled
        # - reference exists
        # - we do NOT already have a description
        # =================================================

        elif (
            self.fetch_details
            and reference_number
        ):
            try:
                detail_data = (
                    self.fetch_job_details(
                        reference_number
                    )
                )

                description = (
                    self._extract_description(
                        detail_data
                    )
                )

                if not title:
                    title = str(
                        detail_data.get(
                            "stellenangebotsTitel"
                        )
                        or ""
                    ).strip()

                if not company:
                    company = str(
                        detail_data.get(
                            "firma"
                        )
                        or ""
                    ).strip()

                if not location:
                    location = (
                        self._extract_location(
                            detail_data
                        )
                    )

            except Exception as exc:
                print(
                    "ARBEITSAGENTUR "
                    "DETAIL ERROR:",
                    reference_number,
                    repr(exc),
                )

        if not title:
            return None

        external_id = (
            reference_number
            or self._fallback_id(
                raw_job
            )
        )

        url = self._build_public_url(
            reference_number
        )

        remote = self._detect_remote(
            raw_job=raw_job,
            detail_data=detail_data,
            description=description,
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
    # DETAILS
    # =====================================================

    def fetch_job_details(
        self,
        reference_number,
    ):
        encoded_reference = (
            base64.b64encode(
                str(
                    reference_number
                ).encode(
                    "utf-8"
                )
            )
            .decode(
                "utf-8"
            )
        )

        url = (
            f"{DETAIL_URL}/"
            f"{encoded_reference}"
        )

        response = requests.get(
            url,
            headers=self._headers(),
            timeout=self.timeout,
        )

        response.raise_for_status()

        payload = response.json()

        if isinstance(
            payload,
            dict,
        ):
            return payload

        return {}


    # =====================================================
    # DESCRIPTION
    # =====================================================

    def _extract_description(
        self,
        data,
    ):
        if not isinstance(
            data,
            dict,
        ):
            return ""

        candidates = [
            "stellenangebotsBeschreibung",
            "beschreibung",
            "stellenbeschreibung",
            "aufgaben",
        ]

        for key in candidates:
            value = data.get(
                key
            )

            if value:
                return self._clean_text(
                    value
                )

        for value in data.values():
            if isinstance(
                value,
                dict,
            ):
                nested = (
                    self._extract_description(
                        value
                    )
                )

                if nested:
                    return nested

        return ""


    # =====================================================
    # LOCATION
    # =====================================================

    def _extract_location(
        self,
        data,
    ):
        if not isinstance(
            data,
            dict,
        ):
            return ""

        locations = (
            data.get(
                "stellenlokationen"
            )
            or data.get(
                "arbeitsorte"
            )
            or []
        )

        if isinstance(
            locations,
            dict,
        ):
            locations = [
                locations
            ]

        if not isinstance(
            locations,
            list,
        ):
            return ""

        location_strings = []

        for item in locations:
            if not isinstance(
                item,
                dict,
            ):
                continue

            address = (
                item.get(
                    "adresse"
                )
                or item
            )

            if not isinstance(
                address,
                dict,
            ):
                continue

            parts = []

            for key in [
                "plz",
                "ort",
                "region",
                "land",
            ]:
                value = address.get(
                    key
                )

                if value:
                    value = str(
                        value
                    ).strip()

                    if (
                        value
                        and value not in parts
                    ):
                        parts.append(
                            value
                        )

            if parts:
                location_strings.append(
                    " ".join(
                        parts
                    )
                )

        if not location_strings:
            return ""

        return ", ".join(
            location_strings[:3]
        )


    # =====================================================
    # PUBLISHED DATE
    # =====================================================

    def _extract_published_at(
        self,
        raw_job,
    ):
        value = (
            raw_job.get(
                "datumErsteVeroeffentlichung"
            )
            or (
                raw_job.get(
                    "veroeffentlichungszeitraum"
                )
                or {}
            ).get(
                "von"
            )
            or raw_job.get(
                "aenderungsdatum"
            )
        )

        return self._parse_date(
            value
        )


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

        for date_format in [
            "%Y-%m-%d",
            "%d.%m.%Y",
        ]:
            try:
                parsed = datetime.strptime(
                    value,
                    date_format,
                )

                return parsed.replace(
                    tzinfo=timezone.utc
                )

            except ValueError:
                continue

        return None


    # =====================================================
    # REMOTE
    # =====================================================

    def _detect_remote(
        self,
        *,
        raw_job,
        detail_data,
        description,
    ):
        text = " ".join(
            [
                str(
                    raw_job
                ),
                str(
                    detail_data
                ),
                description or "",
            ]
        ).casefold()

        remote_terms = [
            "remote",
            "homeoffice",
            "home office",
            "mobiles arbeiten",
            "mobile arbeit",
            "telearbeit",
        ]

        return any(
            term in text
            for term in remote_terms
        )


    # =====================================================
    # PUBLIC URL
    # =====================================================

    def _build_public_url(
        self,
        reference_number,
    ):
        if not reference_number:
            return (
                "https://www.arbeitsagentur.de/"
                "jobsuche/"
            )

        return (
            "https://www.arbeitsagentur.de/"
            "jobsuche/jobdetail/"
            f"{reference_number}"
        )


    # =====================================================
    # FALLBACK ID
    # =====================================================

    def _fallback_id(
        self,
        raw_job,
    ):
        value = repr(
            sorted(
                raw_job.items(),
                key=lambda item: str(
                    item[0]
                ),
            )
        )

        return hashlib.sha256(
            value.encode(
                "utf-8"
            )
        ).hexdigest()


    # =====================================================
    # CLEAN TEXT
    # =====================================================

    def _clean_text(
        self,
        value,
    ):
        if not value:
            return ""

        if isinstance(
            value,
            list,
        ):
            value = "\n".join(
                str(item)
                for item in value
            )

        if isinstance(
            value,
            dict,
        ):
            value = "\n".join(
                str(item)
                for item in value.values()
            )

        value = str(
            value
        )

        # Decode nested HTML entities.
        #
        # Example:
        # &amp;#xA;
        # ->
        # &#xA;
        # ->
        # newline
        for _ in range(3):
            decoded = html.unescape(
                value
            )

            if decoded == value:
                break

            value = decoded

        value = value.replace(
            "\r\n",
            "\n",
        )

        value = value.replace(
            "\r",
            "\n",
        )

        while "\n\n\n" in value:
            value = value.replace(
                "\n\n\n",
                "\n\n",
            )

        return value.strip()