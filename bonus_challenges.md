# Bonus Challenges — Implementation Report

## 1. Conversation Memory

### What We Implemented
A conversation memory system that allows the chatbot to maintain context across multiple turns within the same session.

### How It Works

**Frontend (localStorage):**
- On page load, generate or restore a `conversation_id` from `localStorage`
- Chat history (messages) is stored in `localStorage` and restored on page refresh
- The `conversation_id` is sent with every `/query` request

**Backend (in-memory store):**
- A Python dictionary stores the last N turns per `conversation_id`
- Previous turns are injected into the LLM prompt as conversation history
- Older conversations are automatically evicted to prevent memory leaks

**Token Cost Tradeoff:**
- Each turn adds ~200-400 tokens to the prompt (user question + assistant answer summary)
- With 5-turn memory window, worst case adds ~2,000 extra input tokens per request
- This is a ~3× increase in input tokens, but acceptable for conversational coherence
- We cap at 5 turns to bound cost — older messages are dropped (sliding window)

### Design Decisions
1. **Why in-memory, not database?** — For a demo/assignment, a Python dict is sufficient. Production would use Redis for persistence across restarts.
2. **Why sliding window (5 turns)?** — Balances context quality vs. token cost. Beyond 5 turns, older context rarely improves answer quality.
3. **Why localStorage?** — Persists across page refreshes without requiring authentication. Simple and effective for single-user sessions.

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

*[To be implemented]*

---

## 4. Live Deploy

*[To be implemented]*
