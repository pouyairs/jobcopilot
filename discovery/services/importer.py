from django.db import transaction

from discovery.models import DiscoveredJob


@transaction.atomic
def save_external_job(external_job):
    """
    Save one normalized ExternalJob into DiscoveredJob.

    Returns:
        (job, created)
    """

    if not external_job:
        return None, False

    if not external_job.source:
        return None, False

    if not external_job.external_id:
        return None, False

    if not external_job.title:
        return None, False

    if not external_job.url:
        return None, False


    job, created = (
        DiscoveredJob.objects.update_or_create(
            source=external_job.source,
            external_id=external_job.external_id,

            defaults={
                "title": external_job.title,
                "company": external_job.company or "",
                "location": external_job.location or "",
                "description": external_job.description or "",
                "url": external_job.url,
                "remote": bool(
                    external_job.remote
                ),
                "published_at": external_job.published_at,
                "is_active": True,
            },
        )
    )

    return job, created


def import_from_source(
    source,
    *,
    query=None,
    location=None,
    pages=1,
):
    """
    Fetch jobs from one source connector and save them
    into the shared DiscoveredJob table.

    Example:
        source = ArbeitnowJobSource()

        import_from_source(
            source,
            query="IT Support",
            location="Germany",
            pages=2,
        )
    """

    if pages < 1:
        raise ValueError(
            "pages must be at least 1"
        )

    stats = {
        "source": (
            source.source_name
            or source.__class__.__name__
        ),
        "fetched": 0,
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "failed": 0,
    }


    external_jobs = source.search(
        query=query,
        location=location,
        pages=pages,
    )


    for external_job in external_jobs:

        stats["fetched"] += 1


        try:

            job, created = (
                save_external_job(
                    external_job
                )
            )


            if job is None:

                stats["skipped"] += 1
                continue


            if created:

                stats["created"] += 1

            else:

                stats["updated"] += 1


        except Exception as exc:

            stats["failed"] += 1

            print(
                "JOB IMPORT ERROR:",
                {
                    "source": (
                        external_job.source
                        if external_job
                        else "unknown"
                    ),
                    "external_id": (
                        external_job.external_id
                        if external_job
                        else "unknown"
                    ),
                    "error": repr(
                        exc
                    ),
                },
            )


    return stats


def import_sources(
    sources,
    *,
    query=None,
    location=None,
    pages=1,
):
    """
    Import jobs from multiple source connectors.

    Returns:
        {
            "sources": [...],
            "totals": {...}
        }
    """

    results = []

    totals = {
        "fetched": 0,
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "failed": 0,
    }


    for source in sources:

        try:

            result = import_from_source(
                source,
                query=query,
                location=location,
                pages=pages,
            )


        except Exception as exc:

            result = {
                "source": (
                    source.source_name
                    or source.__class__.__name__
                ),
                "fetched": 0,
                "created": 0,
                "updated": 0,
                "skipped": 0,
                "failed": 1,
                "error": repr(
                    exc
                ),
            }


        results.append(
            result
        )


        for key in totals:

            totals[key] += int(
                result.get(
                    key,
                    0,
                )
            )


    return {
        "sources": results,
        "totals": totals,
    }