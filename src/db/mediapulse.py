import os
import re

import psycopg

# Active (email, ticker) subscriptions. Read-only.
_SUBSCRIPTIONS_SQL = """
    select u.email, u.name, t.symbol as ticker, t.name as ticker_name
    from mediapulse.user_ticker ut
    join mediapulse.mediapulse_user u on u.id = ut.user_id
    join mediapulse.ticker t on t.id = ut.ticker_id
    where ut.enabled = true
      and ut.unsubscribed_at is null
      and ut.registration_confirmed_at is not null
"""


def _conninfo() -> str:
    # Drop the Prisma-style `?schema=` query. libpq does not accept it.
    return os.environ["MEDIAPULSE_DATABASE_URL"].split("?")[0]


def fetch_subscriptions(ticker: str | None = None, email: str | None = None) -> list[dict]:
    """Return active subscriptions as dicts: email, name, ticker, ticker_name. Read-only."""
    sql = _SUBSCRIPTIONS_SQL
    params: list = []

    if ticker:
        sql += " and t.symbol = %s"
        params.append(ticker)

    if email:
        sql += " and u.email = %s"
        params.append(email)

    sql += " order by u.email, t.symbol"

    with psycopg.connect(_conninfo(), connect_timeout=15) as conn:
        conn.read_only = True

        with conn.cursor() as cur:
            cur.execute(sql, params)
            columns = [column.name for column in cur.description]

            return [dict(zip(columns, row)) for row in cur.fetchall()]


_TICKER_SQL = """
    select name, metadata
    from mediapulse.ticker
    where upper(symbol) = upper(%s)
    limit 1
"""

# IDX listing metadata keys -> brief-friendly labels, in presentation order.
# Sector taxonomy first (these map onto the brief's Sector/Market), then company details.
_TAXONOMY = [
    ("Sektor", "Sector"),
    ("SubSektor", "Sub-sector"),
    ("Industri", "Industry"),
    ("SubIndustri", "Sub-industry"),
]
_DETAILS = [
    ("KegiatanUsahaUtama", "Main business"),
    ("PapanPencatatan", "Listing board"),
    ("TanggalPencatatan", "Listed since"),
    ("Website", "Website"),
    ("Alamat", "Headquarters"),
]


def _clean(value: object) -> str:
    """Collapse whitespace and newlines from a metadata value into a single trimmed line."""
    return re.sub(r"\s+", " ", str(value or "").replace("\r", " ").replace("\n", " ")).strip(" ,-")


def fetch_ticker_profile(ticker: str) -> dict[str, str] | None:
    """Return a curated company profile for a ticker, or None if unknown. Read-only."""
    if not (ticker and ticker.strip() and os.getenv("MEDIAPULSE_DATABASE_URL")):
        return None

    with psycopg.connect(_conninfo(), connect_timeout=15) as conn:
        conn.read_only = True

        with conn.cursor() as cur:
            cur.execute(_TICKER_SQL, [ticker.strip()])
            row = cur.fetchone()

    if not row:
        return None

    name, metadata = row[0], row[1] or {}
    profile: dict[str, str] = {"Company": name}

    # The four taxonomy fields are often identical (e.g. Bank/Bank/Bank); keep each value once.
    seen: set[str] = set()

    for key, label in _TAXONOMY:
        value = _clean(metadata.get(key))

        if value and value.lower() not in seen:
            profile[label] = value
            seen.add(value.lower())

    for key, label in _DETAILS:
        value = _clean(metadata.get(key))

        if not value:
            continue

        if label == "Listed since":
            value = value[:10]  # keep the date, drop the T00:00:00 time part

        profile[label] = value

    return profile
