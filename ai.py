import os
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from langchain_groq import ChatGroq
from langchain_community.tools import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from maps import guide_is_complete


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
    """Three focused searches work better than one query covering six topics."""
    return [
        f"{destination} local dishes to try and best neighbourhoods for food",
        f"{destination} tipping etiquette, getting around by public transport and common tourist scams",
        f"{destination} weather, what to pack and crowds in {month}",
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


GUIDE_PROMPT = ChatPromptTemplate.from_template("""
You are an experienced local guide writing a short, practical briefing for a visitor.
Be specific and direct. Prefer facts from the research notes; where they are silent,
use well-established general knowledge and keep claims modest. Do not invent prices,
opening hours or names of businesses. Only say where places are relative to each
other (north of, next to, a short walk from) when the research notes say so.
Write in English using the Latin alphabet: romanise local names (for example
"Ramen", not the Japanese script).

RESEARCH NOTES:
{context}

DESTINATION: {destination}
MONTH OF TRAVEL: {month}

Write Markdown in exactly this format:

## Gastronomy (What to order)
* **[Dish]:** [What it is and where it's typical].

## Neighborhoods
* **[Area]:** [What it's like and who it suits].

## Logistics
* **Tips:** [Tipping and etiquette].
* **Transport:** [Best way to get around].
* **Safety:** [Common scams and how to avoid them].

## Seasonal ({month})
* **Weather:** [Typical temperatures and rain].
* **Crowds:** [High, medium or low, and why].

(---PAGE BREAK---)

### COORDINATES
List 3-4 of the neighbourhoods or places named above, one per line, exactly as: Name | Latitude | Longitude
""")


def generate_guide(destination, month):
    """Research and write a guide. Returns (markdown, sources) where sources
    are the URLs the research actually used."""
    groq_api = os.getenv("GROQ_API_KEY")
    if not groq_api or not os.getenv("TAVILY_API_KEY"):
        raise RuntimeError("Missing API keys for generation")

    docs = research(destination, month)
    context = "\n".join(f"- {d['content']} (Source: {d['url']})" for d in docs) or "(no research results)"

    model = get_intel_model()
    # If the model runs out of budget while reasoning it returns an empty or
    # cut-off answer (finish_reason "length"). Try once more with low effort,
    # which leaves nearly all of the budget for the guide itself.
    efforts = [guide_effort(), "low"] if is_reasoning_model(model) else [None]
    for effort in dict.fromkeys(efforts):
        llm = ChatGroq(
            groq_api_key=groq_api,
            model_name=model,
            temperature=float(os.getenv('GROQ_TEMP_INTEL', '0.3')),
            model_kwargs=reasoning_options(model, effort),
        )
        message = (GUIDE_PROMPT | llm).invoke({"context": context, "destination": destination, "month": month})
        text = message.content or ""
        if message.response_metadata.get("finish_reason") != "length" and guide_is_complete(text):
            return text, [d["url"] for d in docs]
    raise RuntimeError("The model returned an empty or incomplete guide")


def run_chat_response(guide_context, user_query, model_name=None, temperature=None):
    groq_api = os.getenv("GROQ_API_KEY")
    model = get_intel_model(model_name)
    llm = ChatGroq(
        groq_api_key=groq_api,
        model_name=model,
        temperature=float(temperature or os.getenv('GROQ_TEMP_CHAT', '0.5')),
        # Hidden reasoning counts towards this cap, so it's generous and reasoning
        # is kept low: short answers need little of it.
        max_tokens=2000,
        model_kwargs=reasoning_options(model, "low"),
    )

    prompt = ChatPromptTemplate.from_template("""
    You are a helpful assistant answering questions about a specific travel guide.
    
    THE GUIDE:
    {guide_context}
    
    USER QUESTION:
    {user_query}
    
    Answer based ONLY on the information in the guide provided above. If the answer is not in the guide, say "That information is not in this specific briefing." Keep answers concise.
    """)

    chain = prompt | llm | StrOutputParser()
    response = chain.invoke({"guide_context": guide_context, "user_query": user_query})
    return response.strip() or "Sorry, I couldn't come up with an answer to that. Please try asking another way."


def run_gen_response(guide_context, user_query, model_name=None, temperature=None):
    groq_api = os.getenv("GROQ_API_KEY")
    if not groq_api:
        return ""

    llm = ChatGroq(
        groq_api_key=groq_api,
        model_name=get_intel_model(model_name),
        temperature=float(temperature or os.getenv('GROQ_TEMP_INTEL', '0.3')),
    )

    prompt = ChatPromptTemplate.from_template("""
    You are a concise assistant that extracts or summarizes information from the provided guide.

    THE GUIDE:
    {guide_context}

    USER REQUEST:
    {user_query}

    Answer concisely and only using information in the guide. If the guide does not mention the requested item, reply exactly: No short description available.
    """)

    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"guide_context": guide_context, "user_query": user_query})


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
