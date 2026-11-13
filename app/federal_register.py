"""One customer-initiated retrieval from the public Federal Register API.

The destination and query are built from an allowlist. A customer URL is never requested.
A returned document is not evidence until the customer imports it.
A proposed rule or a notice is not an enacted requirement.
"""

from __future__ import annotations

import json
import re
import urllib.parse
from datetime import date
from typing import Any

from app.public_retrieval import (
    PublicRetrievalError,
    _is_blocked_host,
    open_public,
)

SOURCE_ID = "federal-register"
SOURCE_HOST = "www.federalregister.gov"
SOURCE_NAME = "Federal Register"
DOCUMENT_CLASSES = (
    ("proposed_rule", "Proposed rule"),
    ("final_rule", "Final rule"),
    ("notice", "Notice"),
)
_TYPE_BY_CLASS = {
    "proposed_rule": "PRORULE",
    "final_rule": "RULE",
    "notice": "NOTICE",
}
_CLASS_BY_RETURNED = {
    "Proposed Rule": "proposed_rule",
    "Rule": "final_rule",
    "Notice": "notice",
}
_FIELDS = ("title", "type", "abstract", "publication_date", "html_url", "document_number")
_TERM = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 .,'-]{0,79}$")
_DOCUMENT_NUMBER = re.compile(r"^[A-Za-z0-9-]{1,40}$")
_STALE_DAYS = 540
LIMITATION = (
    "Federal Register documents are public notices and rules. A proposed rule or a notice is not an enacted requirement. "
    "A final rule is not verified as applicable to this business. This record does not clear INSUFFICIENT_DEMAND_EVIDENCE, "
    "does not approve the assessment, and is not a live feed."
)
_CLASS_STATEMENT = {
    "proposed_rule": "Proposed rule. This is not an enacted requirement.",
    "final_rule": "Final rule. Publication does not verify that it applies to this business.",
    "notice": "Notice. This is not a rule and is not an enacted requirement.",
}


def clean_term(value: str) -> str:
    term = " ".join(str(value or "").split())
    if not _TERM.fullmatch(term):
        return ""
    return term


def assert_register_url(url: str) -> None:
    """Accept only the documented documents search with the fixed query."""
    parsed = urllib.parse.urlsplit(str(url or ""))
    host = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme != "https" or host != SOURCE_HOST or _is_blocked_host(host):
        raise PublicRetrievalError("not_allowed")
    if parsed.username or parsed.password or parsed.fragment or parsed.port not in {None, 443}:
        raise PublicRetrievalError("not_allowed")
    if parsed.path != "/api/v1/documents.json":
        raise PublicRetrievalError("not_allowed")
    query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    allowed = {"conditions[term]", "conditions[type][]", "per_page", "order", "fields[]"}
    if set(query) != allowed:
        raise PublicRetrievalError("not_allowed")
    if query["per_page"] != ["5"] or query["order"] != ["newest"]:
        raise PublicRetrievalError("not_allowed")
    if query["conditions[type][]"] not in (["PRORULE"], ["RULE"], ["NOTICE"]):
        raise PublicRetrievalError("not_allowed")
    if query["fields[]"] != list(_FIELDS):
        raise PublicRetrievalError("not_allowed")
    if not clean_term(query["conditions[term]"][0]):
        raise PublicRetrievalError("not_allowed")


def guarded_register_fetch(url: str) -> str:
    assert_register_url(url)
    return open_public(url)


def register_url(term: str, document_class: str) -> str:
    cleaned = clean_term(term)
    rule_type = _TYPE_BY_CLASS.get(document_class)
    if not cleaned or rule_type is None:
        raise PublicRetrievalError("not_allowed")
    query = urllib.parse.urlencode(
        [
            ("conditions[term]", cleaned),
            ("conditions[type][]", rule_type),
            ("per_page", "5"),
            ("order", "newest"),
            ("fields[]", "title"),
            ("fields[]", "type"),
            ("fields[]", "abstract"),
            ("fields[]", "publication_date"),
            ("fields[]", "html_url"),
            ("fields[]", "document_number"),
        ]
    )
    url = f"https://{SOURCE_HOST}/api/v1/documents.json?{query}"
    assert_register_url(url)
    return url


def freshness(published_on: str, retrieved_on: str) -> str:
    """Keep the publication date separate from the day RUGD retrieved the record."""
    if not published_on:
        return "Publication date is not recorded. Freshness is incomplete."
    try:
        published = date.fromisoformat(published_on)
        retrieved = date.fromisoformat(retrieved_on)
    except ValueError:
        return "Publication date is not a recorded calendar date. Freshness is incomplete."
    age = (retrieved - published).days
    if age < 0:
        return "Publication date is later than the retrieval date. Freshness is incomplete."
    if age > _STALE_DAYS:
        return "Publication date is more than 18 months before the retrieval date. Treat this document as stale."
    return "Publication date and retrieval date are both recorded. The document is inside 18 months of retrieval."


def _official_document_url(value: str) -> str:
    parsed = urllib.parse.urlsplit(str(value or ""))
    host = (parsed.hostname or "").lower().rstrip(".")
    if (
        parsed.scheme == "https"
        and host == SOURCE_HOST
        and parsed.path.startswith("/documents/")
        and not parsed.username
        and not parsed.query
        and not parsed.fragment
    ):
        return parsed.geturl()
    return ""


def retrieve_register(
    term: str,
    document_class: str,
    *,
    transport=None,
    retrieved_on: str,
) -> dict[str, Any]:
    """Return at most five review records. Nothing is saved here."""
    source_url = register_url(term, document_class)
    reader = transport or guarded_register_fetch
    try:
        body = reader(source_url)
    except PublicRetrievalError:
        raise
    except TimeoutError:
        raise PublicRetrievalError("timeout") from None
    except ValueError:
        raise PublicRetrievalError("invalid") from None
    if not isinstance(body, str) or len(body.encode("utf-8")) > 1_000_000:
        raise PublicRetrievalError("too_large" if isinstance(body, str) else "invalid")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise PublicRetrievalError("invalid") from None
    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list):
        raise PublicRetrievalError("invalid")
    records = []
    seen = set()
    for item in results:
        if len(records) >= 5 or not isinstance(item, dict):
            continue
        number = str(item.get("document_number") or "")
        if not _DOCUMENT_NUMBER.fullmatch(number) or number in seen:
            continue
        seen.add(number)
        kind = _CLASS_BY_RETURNED.get(str(item.get("type") or ""), "")
        if kind != document_class:
            continue
        published = str(item.get("publication_date") or "")
        if published and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", published):
            published = ""
        title = " ".join(str(item.get("title") or "Federal Register document").split())[:300]
        records.append(
            {
                "source": SOURCE_ID,
                "source_name": SOURCE_NAME,
                "measure": title,
                "value": _CLASS_STATEMENT[kind],
                "document_class": kind,
                "published_on": published,
                "measurement_period": published,
                "freshness": freshness(published, retrieved_on),
                "source_url": _official_document_url(str(item.get("html_url") or "")),
                "identity": f"fr:{number}",
                "document_number": number,
                "limitations": LIMITATION,
            }
        )
    notice = (
        "No public document was returned for this search."
        if not records
        else "Review these public documents. Nothing is saved until you import a selection. A proposed rule or a notice is not an enacted requirement."
    )
    return {
        "source": SOURCE_ID,
        "source_name": SOURCE_NAME,
        "source_url": source_url,
        "parameters": {"term": clean_term(term), "document_class": document_class},
        "retrieved_on": retrieved_on,
        "limitations": LIMITATION,
        "status": "review",
        "records": records,
        "notice": notice,
        "error_category": "",
    }


def evidence_from_register(record: dict[str, Any], retrieved_on: str) -> dict[str, str]:
    """Copy one reviewed Federal Register document. It is not a verified business requirement."""
    kind = str(record.get("document_class") or "")
    statement = _CLASS_STATEMENT.get(kind, "Unclassified Federal Register document. Applicability is not verified.")
    published = str(record.get("published_on") or "")
    title = str(record.get("measure") or "Federal Register document")
    return {
        "evidence_class": "retrieved_public",
        "source_title": title,
        "source_organization": "Office of the Federal Register",
        "source_url": str(record.get("source_url") or ""),
        "published_on": published,
        "retrieved_on": retrieved_on,
        "geography": "",
        "industry": "",
        "category": "regulatory",
        "finding": (
            f"{title}. {statement} Publication date {published or 'not recorded'}. "
            f"Retrieval date {retrieved_on}. {record.get('freshness') or ''}"
        ),
        "excerpt": "",
        "source_type": "official public retrieval",
        "source_identity": str(record.get("identity") or ""),
        "limitations": str(record.get("limitations") or LIMITATION),
    }
