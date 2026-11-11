"""One customer-initiated retrieval from the public BLS QCEW file.

The destination is built from an allowlist. A customer URL is never requested.
A returned row is not evidence until the customer imports it.
"""

from __future__ import annotations

import ipaddress
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable

from app.market import (
    PUBLIC_SOURCE,
    _GEOGRAPHIES,
    _INDUSTRIES,
    _PUBLIC_LIMITATION,
    BlsQcewProvider,
    NotCovered,
)

SOURCE_ID = "bls-qcew"
SOURCE_HOST = "data.bls.gov"
SOURCE_NAME = "U.S. Bureau of Labor Statistics, Quarterly Census of Employment and Wages"
RETRIEVAL_YEARS = ("2024", "2023")
MAX_BODY = 5_000_000
MAX_BATCHES = 3
TIMEOUT_SECONDS = 15
ALLOWED_FIPS = {spec[0] for spec in _GEOGRAPHIES.values()}
INDUSTRY_CHOICES = tuple(_INDUSTRIES)
GEOGRAPHY_CHOICES = tuple(_GEOGRAPHIES)
Fetch = Callable[[str], str]


class PublicRetrievalError(RuntimeError):
    """A failed retrieval reduced to a category. The response body is not kept."""

    def __init__(self, category: str) -> None:
        self.category = category
        super().__init__(f"public retrieval failed: {category}")


class _RejectRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ARG002
        raise PublicRetrievalError("redirect")


def retrieval_allowed(existing_batches: int) -> bool:
    return existing_batches < MAX_BATCHES


def assert_allowed_url(url: str) -> None:
    """Accept only the documented QCEW file URL. Private and local addresses are rejected."""
    parsed = urllib.parse.urlsplit(str(url or ""))
    host = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme != "https" or host != SOURCE_HOST:
        raise PublicRetrievalError("not_allowed")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise PublicRetrievalError("not_allowed")
    if parsed.port not in {None, 443}:
        raise PublicRetrievalError("not_allowed")
    if _is_blocked_host(host):
        raise PublicRetrievalError("not_allowed")
    parts = [part for part in parsed.path.split("/") if part]
    if (
        len(parts) != 7
        or parts[:3] != ["cew", "data", "api"]
        or parts[3] not in RETRIEVAL_YEARS
        or parts[4] != "a"
        or parts[5] != "area"
        or not parts[6].endswith(".csv")
    ):
        raise PublicRetrievalError("not_allowed")
    area = parts[6][: -len(".csv")]
    if area not in ALLOWED_FIPS:
        raise PublicRetrievalError("not_allowed")


def _is_blocked_host(host: str) -> bool:
    if host in {"localhost", "metadata.google.internal"}:
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_multicast
        or address.is_unspecified
    )


def guarded_fetch(url: str) -> str:
    """One HTTPS GET. Redirects are not followed and the body is size-capped."""
    assert_allowed_url(url)
    opener = urllib.request.build_opener(_RejectRedirect)
    request = urllib.request.Request(url, headers={"User-Agent": "RUGD-Analyze-prototype"})
    try:
        with opener.open(request, timeout=TIMEOUT_SECONDS) as response:
            payload = response.read(MAX_BODY + 1)
    except PublicRetrievalError:
        raise
    except TimeoutError:
        raise PublicRetrievalError("timeout") from None
    except urllib.error.HTTPError as exc:
        raise PublicRetrievalError(_http_category(exc)) from None
    except urllib.error.URLError as exc:
        raise PublicRetrievalError(_url_category(exc)) from None
    if len(payload) > MAX_BODY:
        raise PublicRetrievalError("too_large")
    return payload.decode("utf-8", "replace")


def _http_category(exc: urllib.error.HTTPError) -> str:
    code = int(getattr(exc, "code", 0) or 0)
    if code == 408:
        return "timeout"
    if code in {400, 401, 403, 404, 429}:
        return f"http_{code}"
    if 500 <= code <= 599:
        return "http_5xx"
    return "http_error"


def _url_category(exc: urllib.error.URLError) -> str:
    reason = getattr(exc, "reason", exc)
    if isinstance(reason, TimeoutError) or "timed out" in str(reason).lower():
        return "timeout"
    text = str(reason).lower()
    if "getaddrinfo" in text or "name or service not known" in text:
        return "dns"
    if "certificate" in text or "tls" in text or "ssl" in text:
        return "tls"
    return "connection"


def retrieve_qcew(
    industry: str,
    geography: str,
    year: str,
    *,
    transport: Fetch | None = None,
    retrieved_on: str,
) -> dict[str, Any]:
    """Return review records for one allowlisted selection. Nothing is saved here."""
    if year not in RETRIEVAL_YEARS or industry not in _INDUSTRIES or geography not in _GEOGRAPHIES:
        raise PublicRetrievalError("not_covered" if industry not in _INDUSTRIES or geography not in _GEOGRAPHIES else "not_allowed")
    area_fips = _GEOGRAPHIES[geography][0]
    source_url = f"https://{SOURCE_HOST}/cew/data/api/{year}/a/area/{area_fips}.csv"
    assert_allowed_url(source_url)

    def _read(url: str) -> str:
        assert_allowed_url(url)
        reader = transport or guarded_fetch
        try:
            body = reader(url)
        except PublicRetrievalError:
            raise
        except TimeoutError:
            raise PublicRetrievalError("timeout") from None
        except urllib.error.HTTPError as exc:
            raise PublicRetrievalError(_http_category(exc)) from None
        except urllib.error.URLError as exc:
            raise PublicRetrievalError(_url_category(exc)) from None
        if not isinstance(body, str):
            raise PublicRetrievalError("invalid")
        if len(body.encode("utf-8")) > MAX_BODY:
            raise PublicRetrievalError("too_large")
        return body

    provider = BlsQcewProvider(year=year, transport=_read, retrieved_on=retrieved_on)
    try:
        rows = provider.observations(industry, geography)
    except NotCovered:
        raise PublicRetrievalError("not_covered") from None
    except LookupError:
        rows = []
    except PublicRetrievalError:
        raise
    except ValueError:
        raise PublicRetrievalError("invalid") from None
    records = []
    for item in rows[:12]:
        if not isinstance(item, dict):
            continue
        records.append(
            {
                "measure": str(item.get("measure") or ""),
                "value": str(item.get("value") or ""),
                "measurement_period": str(item.get("measurement_period") or ""),
                "geographic_coverage": str(item.get("geographic_coverage") or ""),
                "industry_classification": str(item.get("industry_classification") or ""),
                "limitations": str(item.get("limitations") or _PUBLIC_LIMITATION),
                "source": PUBLIC_SOURCE,
                "source_url": source_url,
            }
        )
    notice = (
        "No public observation was returned for this industry and geography."
        if not records
        else "Review these public records. Nothing is saved until you import a selection."
    )
    return {
        "source": SOURCE_ID,
        "source_name": SOURCE_NAME,
        "source_url": source_url,
        "parameters": {"industry": industry, "geography": geography, "year": year},
        "retrieved_on": retrieved_on,
        "limitations": _PUBLIC_LIMITATION,
        "status": "review",
        "records": records,
        "notice": notice,
        "error_category": "",
    }


def evidence_from_observation(record: dict[str, Any], retrieved_on: str) -> dict[str, str]:
    """Copy one reviewed public row into an evidence document. It is not a verified conclusion."""
    measure = str(record.get("measure") or "Public measure")
    value = str(record.get("value") or "not returned")
    period = str(record.get("measurement_period") or "period not recorded")
    return {
        "evidence_class": "retrieved_public",
        "source_title": "Quarterly Census of Employment and Wages",
        "source_organization": "U.S. Bureau of Labor Statistics",
        "source_url": str(record.get("source_url") or ""),
        "published_on": "",
        "retrieved_on": retrieved_on,
        "geography": str(record.get("geographic_coverage") or ""),
        "industry": str(record.get("industry_classification") or ""),
        "category": "trends",
        "finding": (
            f"{measure}: {value}. Measurement period {period}. "
            "This is covered employment or wages for an industry and geography, not revenue or demand for this business."
        ),
        "excerpt": "",
        "source_type": "official public retrieval",
        "limitations": str(record.get("limitations") or _PUBLIC_LIMITATION),
    }
