import os
from langchain_groq import ChatGroq
from langchain_community.tools import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


def generate_intel(destination, month, model_name=None, temperature=None):
    groq_api = os.getenv("GROQ_API_KEY")
    tavily_api = os.getenv("TAVILY_API_KEY")

    if not groq_api or not tavily_api:
        raise RuntimeError("Missing API keys for generation")

    search_query = f"""
    cultural etiquette and tipping rules {destination}
    must eat local dishes food guide {destination} not restaurants
    neighborhood guide {destination} vibe check
    weather and packing tips {destination} in {month}
    common tourist scams {destination}
    coordinates of major neighborhoods {destination}
    """
    tavily = TavilySearchResults(max_results=3)
    search_docs = tavily.invoke(search_query)
    search_context = "\n".join([f"- {d['content']} (Source: {d['url']})" for d in search_docs])

    llm = ChatGroq(
        groq_api_key=groq_api,
        model_name=model_name or os.getenv('GROQ_MODEL_INTEL', 'llama-3.3-70b-versatile'),
        temperature=float(temperature or os.getenv('GROQ_TEMP_INTEL', '0.3')),
    )

    prompt = ChatPromptTemplate.from_template("""
    You are a cynical, expert local guide. Provide "Ground Truth" intelligence.
    
    CONTEXT:
    {context}
    
    REQUEST:
    Destination: {destination}
    Month: {month}
    
    STRICT RULES:
    1. FOOD & NEIGHBORHOODS: Must come from Context or static knowledge.
    2. WEATHER: If Context missing, use INTERNAL KNOWLEDGE for averages.
    3. NO FLUFF.
    
    FORMAT (Markdown):
    
    ## 🍝 Gastronomy (What to order)
    * **[Dish]:** [Desc].
    
    ## 🏘️ Neighborhoods
    * **[Area]:** [Vibe].
    
    ## ⚠️ Logistics
    * **Tips:** [Rule].
    * **Transport:** [Best method].
    * **Safety:** [Scams].
    
    ## 🎒 Seasonal ({month})
    * **Weather:** [Avg Temp/Rain].
    * **Crowds:** [High/Low].

    (---PAGE BREAK---)
    
    ### COORDINATES
    List 3-4 major locations or districts mentioned above in this exact format: Name | Latitude | Longitude
    Example:
    Eiffel Tower Sector | 48.8584 | 2.2945
    Le Marais | 48.8566 | 2.3522
    """)

    chain = prompt | llm | StrOutputParser()
    return chain.stream({"context": search_context, "destination": destination, "month": month})


def run_chat_response(guide_context, user_query, model_name=None, temperature=None):
    groq_api = os.getenv("GROQ_API_KEY")
    llm = ChatGroq(
        groq_api_key=groq_api,
        model_name=model_name or os.getenv('GROQ_MODEL_CHAT', 'llama-3.1-8b-instant'),
        temperature=float(temperature or os.getenv('GROQ_TEMP_CHAT', '0.5')),
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
    return response


def run_gen_response(guide_context, user_query, model_name=None, temperature=None):
    groq_api = os.getenv("GROQ_API_KEY")
    if not groq_api:
        return ""

    llm = ChatGroq(
        groq_api_key=groq_api,
        model_name=model_name or os.getenv('GROQ_MODEL_INTEL', 'llama-3.3-70b-versatile'),
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
