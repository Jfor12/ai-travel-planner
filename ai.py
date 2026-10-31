import os
import json
import logging
import re
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from groq import Groq
from tavily import TavilyClient

from maps import guide_is_complete

log = logging.getLogger("travel-planner")


# 29 Oct 2026: the Groq and Tavily clients are used directly. LangChain (langchain, langchain-community,
# langchain-core, langchain-groq) only wrapped these two calls and its 0.2 versions carried a long list of
# published security advisories; the three prompts below are plain format strings.


class TavilySearchResults:
    """The web search: `invoke(query)` returns a list of {"url", "content"} or, on failure, the error as a
    string (the shape the LangChain tool had, which `research` relies on)."""

    def __init__(self, max_results=3):
        self.max_results = max_results
        self._client = None

    def invoke(self, query):
        try:
            if self._client is None:
                self._client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
            response = self._client.search(query=query, max_results=self.max_results)
            return [{"url": r.get("url", ""), "content": r.get("content", "")} for r in response.get("results", [])]
        except Exception as error:  # the caller skips a failed search
            return repr(error)


def groq_client(api_key):
    """GROQ_API_BASE points the client at another server (the tests run a local stand-in)."""
    base_url = os.getenv("GROQ_API_BASE")
    return Groq(api_key=api_key, base_url=base_url or None, max_retries=2)


def complete(api_key, model, prompt, temperature, max_tokens=None, **options):
    """One chat completion with the prompt as the only (user) message: (text, finish_reason)."""
    request = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": temperature}
    if max_tokens is not None:
        request["max_tokens"] = max_tokens
    request.update(options)
    response = groq_client(api_key).chat.completions.create(**request)
    choice = response.choices[0]
    return (choice.message.content or ""), choice.finish_reason


PREFERRED_MODELS = (
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
)
_available_models = None
DEFAULT_MODEL_ID = "openai/gpt-oss-120b"


def get_available_models():
    global _available_models
    if _available_models is not None:
        return _available_models

    groq_api = os.getenv("GROQ_API_KEY")
    if not groq_api:
        raise RuntimeError("GROQ_API_KEY is not configured")

    request = Request(
        "https://api.groq.com/openai/v1/models",
        headers={"Authorization": f"Bearer {groq_api}"},
    )
    try:
        with urlopen(request, timeout=10) as response:
            payload = json.load(response)
        _available_models = {item["id"] for item in payload.get("data", [])}
        return _available_models
    except HTTPError as error:
        if error.code == 403:
            return None
        raise RuntimeError(f"Could not read models available to the Groq key: {error}") from error
    except Exception as error:
        raise RuntimeError(f"Could not read models available to the Groq key: {error}") from error


def get_intel_model(model_name=None):
    configured_model = model_name or os.getenv("GROQ_MODEL_ID") or DEFAULT_MODEL_ID
    configured_model = configured_model.strip()

    available_models = get_available_models()
    if available_models is None:
        return configured_model or DEFAULT_MODEL_ID

    if configured_model in available_models:
        return configured_model

    for candidate in PREFERRED_MODELS:
        if candidate in available_models:
            return candidate

    raise RuntimeError(
        "No usable Groq model is available to this API key. "
        f"Available models: {', '.join(sorted(available_models))}"
    )


def is_reasoning_model(model):
    return model.startswith("openai/gpt-oss")


def guide_effort():
    """Reasoning effort for guides: GROQ_REASONING_EFFORT, default "medium" (Groq's default).
    gpt-oss spends its output budget on hidden reasoning first; on "high" it can
    run out before writing anything, so "medium" is the safe default."""
    effort = os.getenv("GROQ_REASONING_EFFORT", "medium").strip().lower()
    return effort if effort in ("low", "medium", "high") else "medium"


def reasoning_options(model, effort=None):
    if is_reasoning_model(model):
        return {"reasoning_effort": effort or guide_effort()}
    return {}


def research_queries(destination, month):
    """One focused search per section works better than one query covering everything."""
    return [
        f"{destination} traditional local dishes to try and where to eat them",
        f"{destination} best neighbourhoods to explore and what each is like",
        f"{destination} common tourist scams to avoid",
        f"{destination} tipping etiquette and getting around by public transport",
        f"{destination} weather and crowds in {month}",
    ]


def research(destination, month, max_results=3):
    """Returns ([{'url', 'content'}], ...) deduplicated by URL. A failed search
    is skipped rather than failing the whole guide."""
    tavily = TavilySearchResults(max_results=max_results)
    seen, docs = set(), []
    for query in research_queries(destination, month):
        try:
            results = tavily.invoke(query)
        except Exception:
            continue
        if not isinstance(results, list):  # the tool returns an error string on failure
            continue
        for doc in results:
            url = doc.get("url") if isinstance(doc, dict) else None
            if url and url not in seen and doc.get("content"):
                seen.add(url)
                docs.append({"url": url, "content": doc["content"]})
    return docs


# 31 Oct 2026: the model returns JSON in a fixed shape, which is checked and repaired (validate_guide) and only
# then turned into the guide's Markdown (render_guide). Before, it wrote the Markdown itself, and sections drifted:
# markets and restaurants listed as neighbourhoods, international food under local dishes, scams folded into
# "Safety", and crowd levels that contradicted their own reasons.
GUIDE_PROMPT = """
You are an experienced local guide writing a short, practical briefing for a visitor.
Be specific and direct. Prefer facts from the research notes; where they are silent,
use well-established general knowledge and keep claims modest. Do not invent prices,
opening hours or names of businesses. Only say where places are relative to each
other (north of, next to, a short walk from) when the research notes say so.
Write in English using the Latin alphabet: romanise local names (for example
"Ramen", not the Japanese script). Use British spelling (neighbourhood, centre, colour).

RESEARCH NOTES:
{context}

DESTINATION: {destination}
MONTH OF TRAVEL: {month}

Reply with one JSON object and nothing else, in exactly this shape:

{{
  "food": [
    {{"dish": "a dish typical of {destination} or its country", "description": "what it is, one sentence",
      "where_to_try": "where to try it: a neighbourhood, a market or a kind of place",
      "places": ["names of specific restaurants or markets for this dish, only if the research notes name them"]}}
  ],
  "neighbourhoods": [
    {{"name": "a district or quarter of {destination}", "description": "what it's like, one or two sentences", "suits": "who it suits"}}
  ],
  "tipping": "tipping and etiquette, one or two sentences",
  "transport": "the best way to get around, one or two sentences",
  "scams": [
    {{"name": "the scam's usual name, e.g. Friendship bracelet", "how_it_works": "one sentence", "how_to_avoid": "one sentence"}}
  ],
  "weather": {{"high_c": 0, "low_c": 0, "rain": "how much rain to expect", "summary": "what to pack, one sentence"}},
  "crowds": {{"level": "low, medium or high", "reason": "why, one sentence"}}
}}

Rules for each section:
- food: 3 to 5 dishes from local or national cuisine. No international food (no "Sichuan-style" or "Middle Eastern-inspired" dishes) and no cuisines in general.
- neighbourhoods: 3 or 4 real neighbourhoods, districts or quarters. Never a market, restaurant, museum, landmark or single street.
- scams: 2 to 4 specific scams that target visitors here, each with its usual name. Not general advice such as "watch your bag".
- weather: high_c and low_c are the typical daily high and low in degrees Celsius for {month}, as numbers. Nothing in "rain" or "summary" may contradict them.
- crowds: the level must match the reason (for example, not "low" because it is peak season).
"""

SECTION_LIMITS = {"food": (3, 5), "neighbourhoods": (3, 4), "scams": (2, 4)}
# Names that are venues, not neighbourhoods (a market or a museum is a place to go, not a place to stay).
NOT_A_NEIGHBOURHOOD = re.compile(
    r"\b(market|march[ée]|mercat|mercato|mercado|markt|bazaar|souk|restaurant|trattoria|osteria|caf[ée]|bistro|museum|"
    r"mus[ée]e|museo|gallery|airport|hotel|mall|cathedral|basilica|stadium)\b", re.IGNORECASE)
NOT_LOCAL_FOOD = re.compile(r"inspired|fusion|international", re.IGNORECASE)
GENERIC_SCAM = re.compile(
    r"^(pickpocket(s|ing)?|petty (theft|crime)|theft|crime|general( safety)?|safety|be (aware|careful)|"
    r"(common |tourist )?scams?|overcharging|tourist traps?)$", re.IGNORECASE)
BRITISH = {"neighborhood": "neighbourhood", "Neighborhood": "Neighbourhood", "favorite": "favourite", "Favorite": "Favourite",
           "flavor": "flavour", "Flavor": "Flavour", "theater": "theatre", "Theater": "Theatre"}
CROWD_LEVELS = {"low": "Low", "quiet": "Low", "medium": "Medium", "moderate": "Medium", "high": "High", "busy": "High", "very high": "High"}


class GuideFormatError(ValueError):
    """The model's answer can't be used as a guide, even after repair."""


def parse_guide_json(text):
    """The JSON object in a reply, allowing for a code fence or a sentence around it."""
    text = (text or "").strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise GuideFormatError("no JSON object in the reply")
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError as error:
        raise GuideFormatError(f"invalid JSON: {error}") from error
    if not isinstance(data, dict):
        raise GuideFormatError("the reply is not a JSON object")
    return data


def _text(value, limit=400):
    """A clean one-paragraph string (Markdown markers removed), or ''."""
    if not isinstance(value, str):
        return ""
    value = re.sub(r"\s+", " ", value).strip().strip("*_#|").strip()
    for us, uk in BRITISH.items():
        value = re.sub(rf"\b{us}", uk, value)
    return value[:limit].rstrip()


def _number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if -40 <= number <= 55 else None


def validate_guide(data):
    """Repairs what can be repaired and returns (guide, problems). Items that break a section's rule are dropped;
    `problems` lists what is still wrong. An empty list means the guide meets every rule."""
    problems = []
    guide = {}

    food = []
    for item in data.get("food") or []:
        if not isinstance(item, dict):
            continue
        dish, description = _text(item.get("dish"), 80), _text(item.get("description"))
        if not dish or not description or NOT_LOCAL_FOOD.search(dish):
            continue
        places = [_text(p, 80) for p in item.get("places") or [] if isinstance(p, str)]
        food.append({"dish": dish, "description": description, "where_to_try": _text(item.get("where_to_try"), 200),
                     "places": [p for p in places if p][:2]})
    guide["food"] = food

    neighbourhoods, seen = [], set()
    for item in data.get("neighbourhoods") or data.get("neighborhoods") or []:
        if not isinstance(item, dict):
            continue
        name, description = _text(item.get("name"), 60), _text(item.get("description"))
        if not name or not description or NOT_A_NEIGHBOURHOOD.search(name) or name.lower() in seen:
            continue
        seen.add(name.lower())
        neighbourhoods.append({"name": name, "description": description, "suits": _text(item.get("suits"), 160)})
    guide["neighbourhoods"] = neighbourhoods

    scams = []
    for item in data.get("scams") or []:
        if not isinstance(item, dict):
            continue
        name, how = _text(item.get("name"), 60), _text(item.get("how_it_works"))
        if not name or not how or GENERIC_SCAM.match(name.rstrip(".:")):
            continue
        scams.append({"name": name, "how_it_works": how, "how_to_avoid": _text(item.get("how_to_avoid"))})
    guide["scams"] = scams

    for key in ("food", "neighbourhoods", "scams"):
        low, high = SECTION_LIMITS[key]
        guide[key] = guide[key][:high]
        if len(guide[key]) < low:
            problems.append(f"{key}: {len(guide[key])} usable, at least {low} needed")

    guide["tipping"], guide["transport"] = _text(data.get("tipping")), _text(data.get("transport"))
    if not guide["tipping"] or not guide["transport"]:
        problems.append("tipping or transport missing")

    weather = data.get("weather") if isinstance(data.get("weather"), dict) else {}
    high, low = _number(weather.get("high_c")), _number(weather.get("low_c"))
    if high is not None and low is not None and low > high:
        high, low = low, high
    rain, summary = _text(weather.get("rain"), 200), _text(weather.get("summary"), 200)
    if high is None or low is None:
        problems.append("weather: no typical high and low")
    else:
        # Drop any sentence that quotes a temperature well outside the typical range.
        def consistent(sentence):
            quoted = [float(n) for n in re.findall(r"(-?\d+(?:\.\d+)?)\s*°?\s*C\b", sentence)]
            return all(low - 5 <= t <= high + 5 for t in quoted)
        rain = rain if consistent(rain) else ""
        summary = summary if consistent(summary) else ""
    guide["weather"] = {"high_c": high, "low_c": low, "rain": rain, "summary": summary}

    crowds = data.get("crowds") if isinstance(data.get("crowds"), dict) else {}
    level = CROWD_LEVELS.get(str(crowds.get("level", "")).strip().lower())
    reason = _text(crowds.get("reason"), 240)
    if not level:
        problems.append("crowds: level is not low, medium or high")
    guide["crowds"] = {"level": level, "reason": reason}
    return guide, problems


def _f(celsius):
    return round(celsius * 9 / 5 + 32)


def _sentence(text):
    return text if not text or text[-1] in ".!?" else f"{text}."


def render_guide(guide, month):
    """The guide's Markdown: one section per heading, each holding only what the heading promises."""
    lines = ["## Food"]
    for item in guide["food"]:
        named = " and ".join(item["places"])
        where_text = item["where_to_try"].rstrip(".") if item["where_to_try"] else ""
        if named and named.lower() not in where_text.lower():
            where_text = f"{where_text}, for example {named}" if where_text else named
        where = f" *Where to try it:* {_sentence(where_text)}" if where_text else ""
        lines.append(f"* **{item['dish']}:** {_sentence(item['description'])}{where}")
    lines += ["", "## Neighbourhoods"]
    for item in guide["neighbourhoods"]:
        suits = f" *Suits:* {_sentence(item['suits'])}" if item["suits"] else ""
        lines.append(f"* **{item['name']}:** {_sentence(item['description'])}{suits}")
    lines += ["", "## Logistics",
              f"* **Tipping:** {_sentence(guide['tipping'])}",
              f"* **Getting around:** {_sentence(guide['transport'])}",
              "", "## Scams"]
    if guide["scams"]:
        for item in guide["scams"]:
            avoid = f" *Avoid it:* {_sentence(item['how_to_avoid'])}" if item["how_to_avoid"] else ""
            lines.append(f"* **{item['name']}:** {_sentence(item['how_it_works'])}{avoid}")
    else:
        lines.append("* **No specific scams found:** The research didn't name any scams aimed at visitors here. Usual big-city care applies.")
    weather, crowds = guide["weather"], guide["crowds"]
    reason = f" {_sentence(crowds['reason'])}" if crowds["reason"] else ""
    temps = f"Highs around {weather['high_c']:.0f}°C ({_f(weather['high_c'])}°F), lows around {weather['low_c']:.0f}°C ({_f(weather['low_c'])}°F)."
    extra = " ".join(_sentence(t) for t in (weather["rain"], weather["summary"]) if t)
    lines += ["", f"## Weather and crowds ({month})",
              f"* **Weather:** {temps}{f' {extra}' if extra else ''}",
              f"* **Crowds:** {crowds['level']}.{reason}"]
    return "\n".join(lines)


def places_to_map(guide, limit=8):
    """Neighbourhoods first, then restaurants and markets named for the dishes."""
    names = [n["name"] for n in guide["neighbourhoods"]] + [p for item in guide["food"] for p in item["places"]]
    out, seen = [], set()
    for name in names:
        if name.lower() not in seen:
            seen.add(name.lower())
            out.append({"name": name})
    return out[:limit]


def generate_guide(destination, month):
    """Research and write a guide. Returns (markdown, sources, places): sources are the URLs the research used,
    places the names to look up for the map."""
    groq_api = os.getenv("GROQ_API_KEY")
    if not groq_api or not os.getenv("TAVILY_API_KEY"):
        raise RuntimeError("Missing API keys for generation")

    docs = research(destination, month)
    context = "\n".join(f"- {d['content']} (Source: {d['url']})" for d in docs) or "(no research results)"

    model = get_intel_model()
    # If the model runs out of budget while reasoning it returns an empty or cut-off answer (finish_reason
    # "length"); and an answer can break a section's rules. Try once more with low effort, which leaves nearly
    # all of the budget for the guide itself. The last attempt is accepted if it is usable, even if a section
    # came up short (for example, fewer scams than asked for).
    efforts = list(dict.fromkeys([guide_effort(), "low"] if is_reasoning_model(model) else [None, None]))
    best = None
    for attempt, effort in enumerate(efforts):
        request = dict(temperature=float(os.getenv('GROQ_TEMP_INTEL', '0.3')), **reasoning_options(model, effort))
        prompt = GUIDE_PROMPT.format(context=context, destination=destination, month=month)
        try:
            text, finish_reason = complete(groq_api, model, prompt, response_format={"type": "json_object"}, **request)
        except Exception:
            # A model without JSON mode refuses the setting; the prompt asks for JSON anyway and the reply is checked.
            log.warning("JSON mode failed for %s; asking without it", model, exc_info=True)
            text, finish_reason = complete(groq_api, model, prompt, **request)
        if finish_reason == "length":
            continue
        try:
            guide, problems = validate_guide(parse_guide_json(text))
        except GuideFormatError:
            continue
        if not problems:
            best = guide
            break
        usable = len(guide["food"]) >= 2 and len(guide["neighbourhoods"]) >= 2 and guide["weather"]["high_c"] is not None \
            and guide["crowds"]["level"] and guide["tipping"] and guide["transport"]
        if usable and (best is None or attempt == len(efforts) - 1):
            best = guide
    if best is None:
        raise RuntimeError("The model returned an empty or incomplete guide")
    markdown = render_guide(best, month)
    if not guide_is_complete(markdown):
        raise RuntimeError("The model returned an empty or incomplete guide")
    return markdown, [d["url"] for d in docs], places_to_map(best)


def run_chat_response(guide_context, user_query, model_name=None, temperature=None):
    groq_api = os.getenv("GROQ_API_KEY")
    model = get_intel_model(model_name)
    prompt = """
    You are a helpful assistant answering questions about a specific travel guide.
    
    THE GUIDE:
    {guide_context}
    
    USER QUESTION:
    {user_query}
    
    Answer based ONLY on the information in the guide provided above. If the answer is not in the guide, say "That information is not in this specific briefing." Keep answers concise.
    """

    response, _ = complete(
        groq_api, model, prompt.format(guide_context=guide_context, user_query=user_query),
        temperature=float(temperature or os.getenv('GROQ_TEMP_CHAT', '0.5')),
        # Hidden reasoning counts towards this cap, so it's generous and reasoning
        # is kept low: short answers need little of it.
        max_tokens=2000,
        **reasoning_options(model, "low"),
    )
    return response.strip() or "Sorry, I couldn't come up with an answer to that. Please try asking another way."


def run_gen_response(guide_context, user_query, model_name=None, temperature=None):
    groq_api = os.getenv("GROQ_API_KEY")
    if not groq_api:
        return ""

    prompt = """
    You are a concise assistant that extracts or summarizes information from the provided guide.

    THE GUIDE:
    {guide_context}

    USER REQUEST:
    {user_query}

    Answer concisely and only using information in the guide. If the guide does not mention the requested item, reply exactly: No short description available.
    """

    response, _ = complete(
        groq_api, get_intel_model(model_name), prompt.format(guide_context=guide_context, user_query=user_query),
        temperature=float(temperature or os.getenv('GROQ_TEMP_INTEL', '0.3')),
    )
    return response


def generate_place_summary(guide_text, place_name):
    try:
        user_question = f"Provide a concise one-line (max 15 words) description of '{place_name}' based ONLY on the guide provided. If the guide does not mention the place, reply exactly: No short description available. Keep answer brief and factual."
        response = run_gen_response(guide_text, user_question)
        clean = response.strip()
        if not clean or 'not in this specific briefing' in clean.lower() or 'no short description' in clean.lower():
            return "No short description available."
        first_line = clean.splitlines()[0]
        words = first_line.split()
        if len(words) > 15:
            return ' '.join(words[:15]) + '...'
        return first_line
    except Exception:
        return "No short description available."
