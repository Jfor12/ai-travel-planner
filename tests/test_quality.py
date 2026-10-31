import json
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
    assert len(queries) == 5 and any("June" in q for q in queries) and any("scams" in q for q in queries)
    assert [d["url"] for d in docs] == ["https://a.example/x", "https://b.example/1", "https://b.example/2", "https://b.example/3", "https://b.example/5"]


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
    fresh = "## Food\n* **Supplì:** Fried rice balls.\n\n## Scams\n* **Gladiator photos:** Pay after posing.\n\n## Weather\n* **May:** Warm, 20–26°C."
    sql("INSERT INTO guide_cache (destination_key, month, guide_text, created_at) VALUES ('rome', 'May', %s, %s)",
        (fresh, datetime.now() - timedelta(days=10)))
    assert client.post("/api/generate-intel", json={"destination": "Rome", "month": "May"}).json()["intel"] == fresh
    assert fake_ai["generate"] == []


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


# --- Model settings -------------------------------------------------------------------------------------

GOOD_GUIDE = "## Gastronomy\n* **Pintxos:** Small bites.\n\n## Logistics\n* **Transport:** Metro."
GOOD_JSON = json.dumps({
    "food": [
        {"dish": "Cacio e pepe", "description": "Pasta with Pecorino and pepper", "where_to_try": "Trattorias in Testaccio", "places": ["Felice a Testaccio"]},
        {"dish": "Supplì", "description": "Fried rice balls with mozzarella", "where_to_try": "Pizzerias and bakeries", "places": []},
        {"dish": "Carciofi alla romana", "description": "Braised artichokes", "where_to_try": "In spring, most trattorias", "places": []},
    ],
    "neighbourhoods": [
        {"name": "Testaccio", "description": "Working-class quarter with a food market", "suits": "Food lovers"},
        {"name": "Monti", "description": "Village-like streets next to the Forum", "suits": "Couples"},
        {"name": "Trastevere", "description": "Cobbled lanes across the river", "suits": "Evenings out"},
    ],
    "tipping": "Rounding up is enough", "transport": "Walk, or use the metro and buses",
    "scams": [
        {"name": "Gladiator photos", "how_it_works": "Costumed men demand money after a photo", "how_to_avoid": "Agree a price first or decline"},
        {"name": "Friendship bracelet", "how_it_works": "A bracelet is tied on, then paid for", "how_to_avoid": "Keep your hands to yourself"},
    ],
    "weather": {"high_c": 27, "low_c": 17, "rain": "A few short storms", "summary": "Pack layers"},
    "crowds": {"level": "medium", "reason": "Fewer visitors than in August"},
})


@pytest.fixture
def fake_groq(monkeypatch):
    """A local stand-in for Groq's API. It records what the app sends, and
    `replies` maps a reasoning effort to (content, finish_reason)."""
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer
    seen, replies = [], {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            seen.append(request)
            content, finish = replies.get(request.get("reasoning_effort"), (GOOD_JSON, "stop"))
            body = json.dumps({
                "id": "x", "object": "chat.completion", "created": 0, "model": request["model"],
                "choices": [{"index": 0, "finish_reason": finish, "message": {"role": "assistant", "content": content}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            }).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setenv("GROQ_API_BASE", f"http://127.0.0.1:{server.server_port}")
    monkeypatch.delenv("GROQ_REASONING_EFFORT", raising=False)
    monkeypatch.setattr(ai, "research", lambda d, m: [{"url": "https://example.com", "content": "Monti is next to the Forum. Try cacio e pepe at Felice a Testaccio, suppli from any pizzeria and carciofi alla romana in spring."}])
    monkeypatch.setattr(ai, "get_available_models", lambda: {"openai/gpt-oss-120b", "openai/gpt-oss-20b"})
    yield type("FakeGroq", (), {"seen": seen, "replies": replies})
    server.shutdown()
    server.server_close()


def test_guides_use_medium_reasoning_on_the_strongest_model(fake_groq, monkeypatch):
    monkeypatch.delenv("GROQ_MODEL_ID", raising=False)
    text, sources, places = ai.generate_guide("Rome", "September")
    request = fake_groq.seen[-1]
    assert request["model"] == "openai/gpt-oss-120b"
    assert request["reasoning_effort"] == "medium"
    assert request["response_format"] == {"type": "json_object"}
    assert "Only say where places are relative to each" in request["messages"][0]["content"]
    assert text.startswith("## Food\n* **Cacio e pepe:**") and sources == ["https://example.com"]
    assert places == [{"name": "Testaccio"}, {"name": "Monti"}, {"name": "Trastevere"}, {"name": "Felice a Testaccio"}]
    assert len(fake_groq.seen) == 1


def test_an_empty_answer_is_retried_with_low_reasoning(fake_groq):
    # What happened live: reasoning used the whole budget, content came back empty.
    fake_groq.replies["medium"] = ("", "length")
    text, _, _ = ai.generate_guide("Barcelona", "September")
    assert [r["reasoning_effort"] for r in fake_groq.seen] == ["medium", "low"]
    assert "## Scams" in text


def test_a_cut_off_or_hollow_answer_is_retried(fake_groq):
    fake_groq.replies["medium"] = ("## Gastronomy\n* **Pintxos:** Small", "length")
    ai.generate_guide("Barcelona", "September")
    fake_groq.replies["medium"] = ("Sorry, I can't help with that.", "stop")
    ai.generate_guide("Barcelona", "October")
    assert [r["reasoning_effort"] for r in fake_groq.seen] == ["medium", "low", "medium", "low"]


def test_if_every_attempt_is_empty_generation_fails_instead_of_returning_nothing(fake_groq):
    fake_groq.replies["medium"] = ("", "length")
    fake_groq.replies["low"] = ("", "length")
    with pytest.raises(RuntimeError, match="empty or incomplete"):
        ai.generate_guide("Barcelona", "September")


def test_reasoning_effort_can_be_changed_and_is_only_sent_to_gpt_oss(fake_groq, monkeypatch):
    monkeypatch.setenv("GROQ_REASONING_EFFORT", "high")
    ai.generate_guide("Rome", "May")
    assert fake_groq.seen[-1]["reasoning_effort"] == "high"
    assert ai.reasoning_options("qwen/qwen3.6-27b") == {}
    monkeypatch.setenv("GROQ_REASONING_EFFORT", "extreme")
    assert ai.reasoning_options("openai/gpt-oss-120b") == {"reasoning_effort": "medium"}


def test_chat_leaves_room_for_the_answer_and_never_returns_blank(fake_groq):
    assert ai.run_chat_response(GOOD_GUIDE, "Where to eat?") == GOOD_JSON
    request = fake_groq.seen[-1]
    assert request["reasoning_effort"] == "low" and request["max_tokens"] == 2000
    fake_groq.replies["low"] = ("", "length")
    assert ai.run_chat_response(GOOD_GUIDE, "Where to eat?").startswith("Sorry, I couldn't")


# --- Empty guides are never cached or served -----------------------------------------------------------

BARCELONA_AS_SEEN_LIVE = "\n\n## Sources\n* [devourtours.com](https://devourtours.com/blog/where-to-eat-in-barcelona)"


def test_guide_is_complete():
    assert maps.guide_is_complete(GOOD_GUIDE)
    assert not maps.guide_is_complete(BARCELONA_AS_SEEN_LIVE)
    assert not maps.guide_is_complete("")
    assert not maps.guide_is_complete(None)
    assert not maps.guide_is_complete("## Gastronomy\n* **Pintxos:** Small bites.")  # one section only


def test_an_empty_cached_guide_is_rewritten(client, fake_ai):
    sql("INSERT INTO guide_cache (destination_key, month, guide_text) VALUES ('barcelona', 'September', %s)", (BARCELONA_AS_SEEN_LIVE,))
    data = client.post("/api/generate-intel", json={"destination": "Barcelona", "month": "September"}).json()
    assert data["cached"] is False and "Generated guide for Barcelona" in data["intel"]
    assert "Generated guide" in sql("SELECT guide_text FROM guide_cache")[0][0]


def test_an_empty_guide_is_not_cached_or_saved(client, fake_ai, monkeypatch):
    monkeypatch.setattr(api, "generate_guide", lambda d, m: ("", ["https://example.com"], []))
    client.post("/api/generate-intel", json={"destination": "Barcelona", "month": "May"})
    assert sql("SELECT count(*) FROM guide_cache")[0][0] == 0
    assert client.post("/api/save-itinerary", json={"destination": "Barcelona", "month": "May"}).status_code == 404


def test_generation_failure_is_a_clear_error_not_a_blank_guide(client, monkeypatch):
    def empty(d, m):
        raise RuntimeError("The model returned an empty or incomplete guide")
    monkeypatch.setattr(api, "generate_guide", empty)
    r = client.post("/api/generate-intel", json={"destination": "Barcelona", "month": "June"})
    assert r.status_code == 500 and "generate the guide" in r.json()["detail"]


def test_a_retired_model_setting_falls_back_to_the_strongest(monkeypatch):
    monkeypatch.setattr(ai, "get_available_models", lambda: {"openai/gpt-oss-120b", "openai/gpt-oss-20b"})
    monkeypatch.setenv("GROQ_MODEL_ID", "moonshotai/kimi-k2-instruct-0905")
    assert ai.get_intel_model() == "openai/gpt-oss-120b"


def test_admin_can_see_which_model_is_used(client, monkeypatch):
    monkeypatch.setattr(api, "get_intel_model", lambda: "openai/gpt-oss-120b")
    info = client.get("/api/admin/request-info", headers={"X-Admin-Token": ADMIN_TOKEN}).json()
    assert info["model"] == "openai/gpt-oss-120b"


# --- Guide sections hold only what their headings promise (31 Oct 2026) ----------------------------------

def test_the_guide_is_rendered_with_one_section_per_promise():
    guide, problems = ai.validate_guide(json.loads(GOOD_JSON))
    assert problems == []
    text = ai.render_guide(guide, "September")
    assert [line for line in text.splitlines() if line.startswith("## ")] == [
        "## Food", "## Neighbourhoods", "## Logistics", "## Scams", "## Weather and crowds (September)"]
    assert "* **Cacio e pepe:** Pasta with Pecorino and pepper. *Where to try it:* Trattorias in Testaccio, for example Felice a Testaccio." in text
    assert "* **Weather:** Highs around 27°C (81°F), lows around 17°C (63°F). A few short storms. Pack layers." in text
    assert "* **Crowds:** Medium. Fewer visitors than in August." in text
    assert maps.guide_is_complete(text) and maps.is_current_format(text)


def test_validation_repairs_what_breaks_the_rules():
    data = json.loads(GOOD_JSON)
    data["neighbourhoods"].append({"name": "Mercato di Testaccio", "description": "A covered market", "suits": "Lunch"})
    data["neighbourhoods"].append({"name": "Campo de' Fiori Market", "description": "Stalls", "suits": "Mornings"})
    data["food"].append({"dish": "Middle Eastern-inspired street food", "description": "Falafel", "where_to_try": "", "places": []})
    data["scams"].append({"name": "Pickpockets", "how_it_works": "Busy buses", "how_to_avoid": "Front pockets"})
    data["weather"] = {"high_c": "17", "low_c": 27, "rain": "Expect 35°C heatwaves", "summary": "Light layers"}
    data["crowds"] = {"level": "Moderate", "reason": "September is busy but calmer than August"}
    data["tipping"] = "Not needed in this neighborhood's cafes"
    guide, problems = ai.validate_guide(data)
    assert problems == []
    assert [n["name"] for n in guide["neighbourhoods"]] == ["Testaccio", "Monti", "Trastevere"]
    assert all("inspired" not in f["dish"] for f in guide["food"])
    assert [s["name"] for s in guide["scams"]] == ["Gladiator photos", "Friendship bracelet"]
    assert guide["weather"] == {"high_c": 27.0, "low_c": 17.0, "rain": "", "summary": "Light layers"}  # swapped; 35°C dropped
    assert guide["crowds"]["level"] == "Medium"
    assert "neighbourhood" in guide["tipping"]


def test_validation_reports_what_cant_be_repaired():
    data = json.loads(GOOD_JSON)
    data["scams"] = [{"name": "Scams", "how_it_works": "Be careful", "how_to_avoid": ""}]
    data["crowds"] = {"level": "it depends", "reason": ""}
    _, problems = ai.validate_guide(data)
    assert any(p.startswith("scams") for p in problems) and any(p.startswith("crowds") for p in problems)


def test_json_is_found_inside_a_fence_and_broken_json_is_rejected():
    assert ai.parse_guide_json('Here you go:\n```json\n{"food": []}\n```')["food"] == []
    with pytest.raises(ai.GuideFormatError):
        ai.parse_guide_json('{"food": [')


def test_an_answer_that_breaks_the_rules_is_retried_then_accepted_if_usable(fake_groq):
    short = json.loads(GOOD_JSON)
    short["scams"] = []
    fake_groq.replies["medium"] = ("not json at all", "stop")
    fake_groq.replies["low"] = (json.dumps(short), "stop")
    text, _, _ = ai.generate_guide("Rome", "May")
    assert [r["reasoning_effort"] for r in fake_groq.seen] == ["medium", "low"]
    assert "**No specific scams found:**" in text


def test_hyphens_in_place_names_are_kept_and_stray_rules_are_dropped():
    old = "## Neighborhoods\n* **Le Marais:** Old streets.\n\n---\n### COORDINATES\nCanal Saint-Martin | 48.8703 | 2.3695"
    assert maps.extract_map_data(old) == [{"name": "Canal Saint-Martin", "lat": 48.8703, "lon": 2.3695}]
    assert maps.guide_body(old).endswith("Old streets.")


def test_old_format_cached_guides_are_rewritten_and_fresh_skips_the_cache(client, fake_ai):
    sql("INSERT INTO guide_cache (destination_key, month, guide_text) VALUES ('rome', 'May', %s)",
        ("## Gastronomy\n* **A:** b\n\n## Logistics\n* **Safety:** Pickpockets.",))
    assert client.post("/api/generate-intel", json={"destination": "Rome", "month": "May"}).json()["cached"] is False
    assert client.post("/api/generate-intel", json={"destination": "Rome", "month": "May"}).json()["cached"] is True
    assert client.post("/api/generate-intel", json={"destination": "Rome", "month": "May", "fresh": True}).json()["cached"] is False
    assert len(fake_ai["generate"]) == 2


def test_places_without_coordinates_are_dropped_when_the_geocoder_is_down(monkeypatch):
    def down(query):
        raise geo.GeocoderUnavailable("timeout")
    geo._cache.clear()
    monkeypatch.setattr(geo, "_fetch", down)
    assert geo.verify_locations("Rome", [{"name": "Monti"}, {"name": "Colosseum", "lat": 41.89, "lon": 12.49}]) == [
        {"name": "Colosseum", "lat": 41.89, "lon": 12.49}]


def test_dishes_and_venues_must_be_in_the_research():
    data = json.loads(GOOD_JSON)
    data["food"].append({"dish": "Burnt Pie", "description": "A pie", "where_to_try": "Pubs", "places": []})
    data["food"][0]["places"] = ["Felice a Testaccio", "Invented Trattoria"]
    data["food"][1]["where_to_try"] = "Breakfast at The Wolseley"
    data["food"][1]["places"] = ["The Wolseley"]
    research = "Rome's classics: Cacio e pepe (Felice a Testaccio is famous for it), supplì and carciofi alla romana."
    guide, problems = ai.validate_guide(data, research=research)
    assert [f["dish"] for f in guide["food"]] == ["Cacio e pepe", "Supplì", "Carciofi alla romana"]
    assert guide["food"][0]["places"] == ["Felice a Testaccio"]
    assert guide["food"][1]["places"] == [] and guide["food"][1]["where_to_try"] == ""  # it named a dropped venue
    assert problems == []
    # Without research to check against, nothing is dropped for it.
    assert len(ai.validate_guide(data, research=ai.NO_RESEARCH)[0]["food"]) == 4
