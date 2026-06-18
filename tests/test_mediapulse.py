import db.mediapulse as mediapulse


class FakeCursor:
    def __init__(self, row):
        self._row = row

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params):
        self.sql = sql
        self.params = params

    def fetchone(self):
        return self._row


class FakeConn:
    def __init__(self, row):
        self._row = row
        self.read_only = False

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def cursor(self):
        return FakeCursor(self._row)


def test_conninfo_drops_prisma_schema_query(monkeypatch):
    monkeypatch.setenv("MEDIAPULSE_DATABASE_URL", "postgres://u:p@h/db?schema=mediapulse")
    assert mediapulse._conninfo() == "postgres://u:p@h/db"


def test_clean_collapses_whitespace_and_trims_punctuation():
    assert mediapulse._clean("  multi\nline\r value ,- ") == "multi line value"
    assert mediapulse._clean(None) == ""


def test_fetch_ticker_profile_none_without_env(monkeypatch):
    monkeypatch.delenv("MEDIAPULSE_DATABASE_URL", raising=False)
    assert mediapulse.fetch_ticker_profile("ACME") is None


def test_fetch_ticker_profile_none_for_blank_ticker(monkeypatch):
    monkeypatch.setenv("MEDIAPULSE_DATABASE_URL", "postgres://u:p@h/db")
    assert mediapulse.fetch_ticker_profile("   ") is None


def test_fetch_ticker_profile_none_when_ticker_not_listed(monkeypatch):
    monkeypatch.setenv("MEDIAPULSE_DATABASE_URL", "postgres://u:p@h/db")
    monkeypatch.setattr(mediapulse.psycopg, "connect", lambda *a, **k: FakeConn(None))
    assert mediapulse.fetch_ticker_profile("ACME") is None


def test_fetch_ticker_profile_shapes_metadata(monkeypatch):
    monkeypatch.setenv("MEDIAPULSE_DATABASE_URL", "postgres://u:p@h/db")
    metadata = {
        "Sektor": "Technology",
        "SubSektor": "Technology",  # identical -> deduped away
        "Industri": "Consumer Electronics",
        "KegiatanUsahaUtama": "Devices\nand services",
        "TanggalPencatatan": "2000-05-31T00:00:00.000Z",
        "Website": "https://example.com",
    }
    monkeypatch.setattr(mediapulse.psycopg, "connect", lambda *a, **k: FakeConn(("Acme Sample Corp", metadata)))

    profile = mediapulse.fetch_ticker_profile("acme")
    assert profile["Company"] == "Acme Sample Corp"
    assert profile["Sector"] == "Technology"
    assert "Sub-sector" not in profile  # duplicate "Technology" value dropped
    assert profile["Industry"] == "Consumer Electronics"
    assert profile["Main business"] == "Devices and services"
    assert profile["Listed since"] == "2000-05-31"  # time part trimmed
    assert profile["Website"] == "https://example.com"


def test_fetch_ticker_profile_handles_missing_metadata(monkeypatch):
    monkeypatch.setenv("MEDIAPULSE_DATABASE_URL", "postgres://u:p@h/db")
    monkeypatch.setattr(mediapulse.psycopg, "connect", lambda *a, **k: FakeConn(("Solo Name", None)))
    profile = mediapulse.fetch_ticker_profile("SOLO")
    assert profile == {"Company": "Solo Name"}
