from datetime import datetime, timedelta

import pytest

from conftest import ADMIN_TOKEN, sql
import ai
import api
import geo
import maps


# --- Sources ---------------------------------------------------------------------------------

def test_generated_guides_list_their_sources(client, fake_ai):
    intel = client.post("/api/generate-intel", json={"destination": "Rome", "month": "May"}).json()["intel"]
    assert "## Sources\n* [example.com](https://www.example.com/guide)\n* [blog.example.org](https://blog.example.org/food)" in intel
    assert intel.index("## Sources") < intel.index("PAGE BREAK")


def test_research_runs_focused_queries_and_survives_a_failed_search(monkeypatch):
    queries = []

    class FakeTavily:
        def __init__(self, max_results):
            pass

        def invoke(self, query):
            queries.append(query)
            if "tipping" in query:
                return "HTTPError('rate limited')"  # what the tool returns on failure
            return [{"url": "https://a.example/x", "content": "A"}, {"url": f"https://b.example/{len(queries)}", "content": "B"}]

    monkeypatch.setattr(ai, "TavilySearchResults", FakeTavily)
    docs = ai.research("Lisbon", "June")
    assert len(queries) == 3 and any("June" in q for q in queries)
    assert [d["url"] for d in docs] == ["https://a.example/x", "https://b.example/1", "https://b.example/3"]


# --- Geocoding ---------------------------------------------------------------------------------------

@pytest.fixture
def fake_nominatim(monkeypatch):
    places = {
        "rome": [{"lat": "41.8933", "lon": "12.4829"}],
        "trastevere, rome": [{"lat": "41.8897", "lon": "12.4699"}],
        "colosseum, rome": [{"lat": "41.8902", "lon": "12.4922"}],
        "rome, georgia, rome": [{"lat": "34.2570", "lon": "-85.1647"}],  # a wrong match, far away
    }
    seen = []

    def fetch(query):
        seen.append(query)
        return places.get(query.lower(), [])

    geo._cache.clear()
    monkeypatch.setattr(geo, "_fetch", fetch)
    return seen


def test_pins_come_from_the_geocoder(fake_nominatim):
    guessed = [
        {"name": "Trastevere", "lat": 41.0, "lon": 12.0},          # model's guess, 100 km off
        {"name": "Colosseum", "lat": 41.89, "lon": 12.49},
        {"name": "Nowhere Square", "lat": 41.9, "lon": 12.5},       # not found: dropped
        {"name": "Rome, Georgia", "lat": 41.9, "lon": 12.5},        # found, but far away: dropped
    ]
    assert geo.verify_locations("Rome", guessed) == [
        {"name": "Trastevere", "lat": 41.8897, "lon": 12.4699},
        {"name": "Colosseum", "lat": 41.8902, "lon": 12.4922},
    ]


def test_geocoder_results_are_cached(fake_nominatim):
    geo.verify_locations("Rome", [{"name": "Colosseum", "lat": 0, "lon": 0}])
    geo.verify_locations("Rome", [{"name": "Colosseum", "lat": 0, "lon": 0}])
    assert fake_nominatim == ["Rome", "Colosseum, Rome"]


def test_when_the_geocoder_is_down_the_original_pins_are_kept(monkeypatch):
    def down(query):
        raise geo.GeocoderUnavailable("timeout")
    geo._cache.clear()
    monkeypatch.setattr(geo, "_fetch", down)
    guessed = [{"name": "Colosseum", "lat": 41.89, "lon": 12.49}]
    assert geo.verify_locations("Rome", guessed) == guessed


def test_verified_pins_are_written_into_the_cached_guide(client, fake_ai, monkeypatch):
    monkeypatch.setattr(api, "verify_locations", lambda d, locs: [{"name": "Old Town", "lat": 41.90123, "lon": 12.49567}])
    client.post("/api/generate-intel", json={"destination": "Rome", "month": "May"})
    again = client.post("/api/generate-intel", json={"destination": "Rome", "month": "May"}).json()
    assert again["cached"] and again["locations"] == [{"name": "Old Town", "lat": 41.90123, "lon": 12.49567}]


# --- Cache expiry ------------------------------------------------------------------------------------------

def test_old_cached_guides_are_regenerated(client, fake_ai):
    sql("INSERT INTO guide_cache (destination_key, month, guide_text, created_at) VALUES ('rome', 'May', 'stale guide', %s)",
        (datetime.now() - timedelta(days=120),))
    data = client.post("/api/generate-intel", json={"destination": "Rome", "month": "May"}).json()
    assert data["cached"] is False and "stale guide" not in data["intel"]
    assert sql("SELECT guide_text FROM guide_cache")[0][0] != "stale guide"


def test_recent_cached_guides_are_used(client, fake_ai):
    sql("INSERT INTO guide_cache (destination_key, month, guide_text, created_at) VALUES ('rome', 'May', 'fresh guide', %s)",
        (datetime.now() - timedelta(days=10),))
    assert client.post("/api/generate-intel", json={"destination": "Rome", "month": "May"}).json()["intel"] == "fresh guide"


# --- Client IP for rate limits ---------------------------------------------------------------------------

def test_rate_limit_uses_the_proxy_added_address(client, fake_ai):
    # Two visitors behind the same proxy get separate allowances; a forged
    # left-hand entry doesn't change who you are.
    for n in range(api.RATE_LIMIT):
        assert client.post("/api/generate-intel", json={"destination": f"Town{'x' * n}", "month": "May"},
                           headers={"X-Forwarded-For": f"6.6.6.{n}, 203.0.113.7"}).status_code == 200
    assert client.post("/api/generate-intel", json={"destination": "Other", "month": "May"},
                       headers={"X-Forwarded-For": "1.2.3.4, 203.0.113.7"}).status_code == 429
    assert client.post("/api/generate-intel", json={"destination": "Other", "month": "May"},
                       headers={"X-Forwarded-For": "198.51.100.9"}).status_code == 200


def test_client_ip_settings(monkeypatch):
    class Req:
        def __init__(self, headers):
            self.headers = {k.lower(): v for k, v in headers.items()}
            self.client = type("C", (), {"host": "10.0.0.1"})()
    assert api.client_ip(Req({})) == "10.0.0.1"
    assert api.client_ip(Req({"X-Forwarded-For": "1.1.1.1, 2.2.2.2"})) == "2.2.2.2"
    monkeypatch.setenv("FORWARDED_IP_INDEX", "2")
    assert api.client_ip(Req({"X-Forwarded-For": "1.1.1.1, 2.2.2.2"})) == "1.1.1.1"
    monkeypatch.setenv("CLIENT_IP_HEADER", "CF-Connecting-IP")
    assert api.client_ip(Req({"CF-Connecting-IP": "9.9.9.9", "X-Forwarded-For": "1.1.1.1"})) == "9.9.9.9"


def test_request_info_is_admin_only(client):
    assert client.get("/api/admin/request-info").status_code == 403
    info = client.get("/api/admin/request-info", headers={"X-Admin-Token": ADMIN_TOKEN, "X-Forwarded-For": "1.1.1.1, 2.2.2.2"}).json()
    assert info["headers"]["x-forwarded-for"] == "1.1.1.1, 2.2.2.2" and info["rate_limit_key"] == "2.2.2.2"


# --- Guide format and PDF ------------------------------------------------------------------------------------

def test_compose_and_extract_round_trip():
    text = maps.compose_guide("## Food\n* **Pastel:** Custard tart.\n\n(---PAGE BREAK---)\nold | 1 | 2",
                              ["https://www.visitlisboa.com/x"], [{"name": "Alfama", "lat": 38.7118, "lon": -9.1301}])
    assert maps.guide_body(text).endswith("* [visitlisboa.com](https://www.visitlisboa.com/x)")
    assert maps.extract_map_data(text) == [{"name": "Alfama", "lat": 38.7118, "lon": -9.1301}]
    assert "old | 1 | 2" not in text


def test_older_guides_without_a_page_break_still_give_pins():
    assert maps.extract_map_data("## Rome\nColosseum | 41.8902 | 12.4922") == [{"name": "Colosseum", "lat": 41.8902, "lon": 12.4922}]


def test_pdf_keeps_non_latin_characters(client):
    text = "## Łódź – “Old Town”\n* **Pierogi:** dumplings, 5–7 zł\n* **東京:** Tokyo in Japanese\n\n## Sources\n* [example.com](https://example.com)"
    r = client.post("/api/export-pdf", json={"destination": "Łódź", "month": "May", "guide_text": text})
    assert r.status_code == 200 and r.content[:4] == b"%PDF"
    assert b"DejaVu" in r.content, "a Unicode font is embedded"
    assert r.headers["content-disposition"] == "attachment; filename=\"odz_May.pdf\"; filename*=UTF-8''%C5%81%C3%B3d%C5%BA%20May.pdf"


# --- Database connection retry and PDF layout -----------------------------------------------------

def test_a_failed_connection_is_retried_once(client, fake_ai, monkeypatch):
    import psycopg
    import db
    real_connect, failures = psycopg.connect, []

    def flaky(*args, **kwargs):
        if not failures:
            failures.append(1)
            raise psycopg.OperationalError("server closed the connection unexpectedly")
        return real_connect(*args, **kwargs)

    monkeypatch.setattr(db.psycopg, "connect", flaky)
    monkeypatch.setattr(db.time, "sleep", lambda s: None)
    client.post("/api/generate-intel", json={"destination": "Rome", "month": "May"})
    failures.clear()
    r = client.post("/api/save-itinerary", json={"destination": "Rome", "month": "May"})
    assert r.status_code == 200 and failures == [1]
    assert sql("SELECT count(*) FROM saved_itineraries")[0][0] == 1


def test_pdf_title_links_and_nesting():
    import pymupdf
    pdf = maps.create_pdf("Rome [September]", "## Logistics\n* **Safety:**\n  * **Pickpockets:** Front pockets.\n\n## Sources\n"
                                               "* [worldnomads.com](https://www.worldnomads.com/travel-safety/europe/italy/common-scams-in-italy)")
    page = pymupdf.open(stream=pdf, filetype="pdf")[0]
    text = page.get_text()
    assert text.startswith("Rome in September")
    assert "worldnomads.com\n" in text and "travel-safety" not in text, "sources print the site name, not the URL"
    assert [link["uri"] for link in page.get_links()] == ["https://www.worldnomads.com/travel-safety/europe/italy/common-scams-in-italy"]
    safety, pick = (next(b for b in page.get_text("blocks") if word in b[4]) for word in ("Safety", "Pickpockets"))
    assert pick[0] > safety[0] + 10, "nested point is indented"


def test_display_title():
    assert maps.display_title("Rome [September]") == "Rome in September"
    assert maps.display_title("Rome [Smarch]") == "Rome [Smarch]"
    assert maps.display_title("Paris") == "Paris"
