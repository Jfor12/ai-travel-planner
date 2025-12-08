# 🌍 AI Travel Planner (Full Stack)

An intelligent travel agent that generates personalized itineraries using Generative AI and live web search. Unlike standard chatbots, this agent uses the **ReAct Pattern** to research real-time data (hotels, events) and persists trip history in a database.

![Python](https://img.shields.io/badge/Python-3.9-blue)
![Stack](https://img.shields.io/badge/Full%20Stack-Streamlit%20%2B%20Postgres-green)
![AI](https://img.shields.io/badge/AI-LangChain%20%2B%20Llama3-orange)

## 🚀 Features
* **AI Agentic Workflow:** Uses LangChain to orchestrate a "Reason + Act" loop.
* **Live Web Search:** Integrated **DuckDuckGo** tool to find real booking links and current events (no hallucinations).
* **Zero-Cost LLM:** Powered by **Llama 3 (via Groq)** for GPT-4 level performance at $0 cost.
* **Database Integration:** Saves generated itineraries to **PostgreSQL** for retrieval.
* **Full Stack UI:** Built with **Streamlit** for a responsive user experience.

## 🛠️ Tech Stack
* **Frontend:** Streamlit
* **Orchestration:** LangChain
* **LLM:** Llama 3 70B (Groq API)
* **Database:** PostgreSQL (Neon/Supabase)
* **Tools:** DuckDuckGo Search

## ⚙️ Setup & Installation

1.  **Clone the repo**
    ```bash
    git clone [https://github.com/your-username/ai-travel-planner.git](https://github.com/your-username/ai-travel-planner.git)
    cd ai-travel-planner
    ```

2.  **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set up secrets**
    Create a `.env` file in the root directory:
    ```ini
    GROQ_API_KEY=your_groq_key
    DATABASE_URL=postgres://user:pass@host/db
    ```

4.  **Run the App**
    ```bash
    streamlit run app.py
    ```