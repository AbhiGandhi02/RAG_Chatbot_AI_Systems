# Bonus Challenges — Implementation Report

## 1. Conversation Memory

### What We Implemented
A conversation memory system that allows the chatbot to maintain context across multiple turns within the same session.

### How It Works

**Frontend (localStorage):**
- On page load, generate or restore a `conversation_id` from `localStorage`
- Chat history (messages) is stored in `localStorage` and restored on page refresh
- The `conversation_id` is sent with every `/query` request

**Backend (PostgreSQL Database):**
- A robust PostgreSQL database using SQLAlchemy ORM stores `User`, `Conversation`, and `Message` models.
- The `get_formatted_history` function queries the database for the N most recent turns.
- Previous turns are formatted into role/content dictionaries and injected into the Groq LLM prompt as conversation history.

**Token Cost Tradeoff:**
- Each turn adds ~200-400 tokens to the prompt (user question + bounded assistant answer).
- With 5-turn memory window, worst case adds ~2,000 extra input tokens per request.
- This is a ~3× increase in input tokens, but necessary for conversational coherence.
- We gracefully cap contexts by slicing the LLM assistant responses if they exceed 500 characters, preventing prompt explosion.

### Design Decisions
1. **Why PostgreSQL instead of in-memory?** — While a basic dictionary works for a single-user demo, production RAG systems require persistent memory across stateless API scaling. Storing sessions alongside users sets the project up for enterprise deployment.
2. **Why sliding window (5 turns)?** — Balances context quality vs. token cost. Beyond 5 turns, older context rarely improves answer quality and simply burns tokens.
3. **Why Firebase Auth bindings?** — Sessions are strictly siloed by the authenticated Firebase `user_id`, meaning users cannot leak or pollute each other's conversation history via API enumeration attacks.

---

## 2. Streaming

### What We Implemented
Token-by-token streaming via **Server-Sent Events (SSE)**. The LLM response appears in real-time in the chat bubble, word by word — just like ChatGPT.

### How It Works

**Backend (`/query/stream` endpoint):**
1. Routing, retrieval, and context building happen upfront (non-streamed)
2. A `StreamingResponse` sends SSE events:
   - `metadata` event → classification, model, sources (sent first)
   - `token` events → individual tokens as they arrive from Groq
   - `done` event → final token counts, latency, evaluator flags

**Frontend (ReadableStream consumer):**
1. Uses `fetch()` with `response.body.getReader()` to read the SSE stream
2. Each `token` event appends to the message bubble and re-renders
3. On `done`, updates the debug panel with full metadata
4. Warning badges are added post-stream if evaluator flags are present

**Groq Client (`generate_stream` method):**
- Uses `stream=True` in the Groq SDK's `chat.completions.create()`
- Yields each `delta.content` token as it arrives
- Captures `x_groq.usage` from the final chunk for token counts

### Where Structured Output Parsing Breaks with Streaming
When streaming, the LLM response arrives as individual tokens/fragments. This breaks **any structured output parsing** that depends on the complete response:

1. **JSON mode parsing** — If the model is instructed to return JSON, you can't parse partial JSON. `{"answer": "The Pro plan co` is invalid JSON until the stream completes.
2. **Evaluator flags** — Our `refusal` detector looks for phrases like "I don't have enough information". During streaming, the phrase builds incrementally: `"I don"` → `"I don't"` → `"I don't have"` — you can't pattern-match mid-stream.
3. **Warning prefix injection** — We prepend "⚠️ Low confidence..." to flagged answers. With streaming, the answer is already being displayed, so we can't prepend — we add the badge *after* the stream completes instead.

**Our solution**: Evaluator runs post-stream on the full accumulated answer, and warning badges are inserted retroactively into the DOM.

---

## 3. Eval Harness

### What We Implemented
An automated evaluation harness (`eval_harness.py`) that runs a predefined suite of identical test queries against the RAG system to measure correctness and latency.

### How It Works

**Test Suite Definition:**
The harness defines a list of tuples containing `(query, [expected_keywords])`. 
- **Simple factual**: Ensures exact prices or names are extracted.
- **Complex**: Ensures comparison context is maintained.
- **Troubleshooting**: Tests the system's ability to provide step-by-step guides from the docs.
- **Out-of-Scope**: Tests that the system refuses to answer non-ClearPath questions using our evaluator "refusals".

**Execution (`TestClient` Mocking):**
- Rather than forcing a real frontend browser login, the harness uses `fastapi.testclient.TestClient` to hit the FastAPI backend directly.
- We override the `get_current_user` dependency in FastAPI to permanently return a mock `eval_harness_user` during testing. 
- The user is automatically created in the local PostgreSQL database to prevent `ForeignKeyViolationError`s when the conversation history is being saved.

**Validation & Results:**
- Hits the real `/query` endpoint (including PostgreSQL pgvector retrieval, Groq LLM generations, and the Output Evaluator flags).
- Verifies that all expected keywords exist in the LLM's answer.
- Outputs individual pass/fails along with latency metrics, ending with an aggregated summary (e.g., `7/7 tests passed`).

---

## 4. Live Deploy

### Architecture Recommendation

Since AWS is not an option for now and we want a free, low-maintenance deployment for an assignment, the optimal architecture is a split deployment:

1. **Database:** [**Supabase**](https://supabase.com/)
   - **Why:** Supabase is a managed PostgreSQL service with a generous free tier that never expires (unlike Render's 90-day free DB). Most importantly, **it supports the `pgvector` extension natively out of the box.** 
   - **Usage:** We simply provision a free database, retrieve the Postgres connection string, and set it as our `DATABASE_URL` environment variable in production.

2. **Backend + Frontend (Monolith):** [**Render.com**](https://render.com/)
   - **Why Render:** Render offers a free "Web Service" tier that can link directly to your GitHub repository. Every time you push to the `main` branch, Render will automatically pull the code, install `requirements.txt`, and start the FastAPI server using Uvicorn.
   - **Why Monolith:** Since FastAPI is mounting our static `/frontend` folder, we do not need a separate frontend host like Vercel. Render will host a single unified URL that serves both our API and our UI interface.

### Deployment Steps
1. Create a free Supabase project, go to Database settings, and copy the Connection String.
2. Link the GitHub repository to a new Render "Web Service".
3. Set the Build Command: `pip install -r requirements.txt`
4. Set the Start Command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
5. Inject the Environment Variables into Render (`GROQ_API_KEY`, `FIREBASE_*`, and `DATABASE_URL` from Supabase).

This guarantees a production-ready URL to submit with the assignment that examiners can immediately test without setting up anything locally.
