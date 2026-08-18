from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ExternalJob:
    """
    Standard job format used by every JobCopilot source.

    Every external connector must convert its own
    API/site response into this structure.
    """

    source: str

    external_id: str

    title: str

    company: str

    location: str

    description: str

    url: str

    remote: bool = False

    published_at: Optional[datetime] = None


class BaseJobSource:
    """
    Base interface for all JobCopilot job sources.

    Examples:
    - Arbeitnow
    - Bundesagentur
    - Indeed
    - future company career pages
    """

    source_name = None

    def fetch_jobs(
        self,
        *,
        query=None,
        location=None,
        page=1,
    ):
        """
        Fetch jobs from the external source.

        Must return:

        list[ExternalJob]
        """

        raise NotImplementedError(
            "Job source must implement fetch_jobs()."
        )


    def search(
        self,
        *,
        query=None,
        location=None,
        pages=1,
    ):
        """
        Fetch multiple pages and return one list.
        """

        results = []


        for page in range(
            1,
            pages + 1,
        ):

            jobs = self.fetch_jobs(
                query=query,
                location=location,
                page=page,
            )


            results.extend(
                jobs
            )


        return results