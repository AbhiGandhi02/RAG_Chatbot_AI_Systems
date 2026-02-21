"""
ClearPath RAG Chatbot — FastAPI Application

Main entry point. Serves the POST /query endpoint and the frontend chat UI.
Orchestrates: Router → Retriever → LLM → Evaluator → Response
"""

import uuid
import logging
import time
from collections import OrderedDict
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
import os
import json

from backend.models.schemas import QueryRequest, QueryResponse, Metadata, Source, TokenUsage
from backend.router.classifier import classify_query, create_routing_log
from backend.rag.retriever import Retriever
from backend.llm.groq_client import get_groq_client
from backend.evaluator.evaluator import evaluate_response, get_warning_message
from backend.config import PORT

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

# Global instances (lazy initialized)
retriever = None
groq_client = None

# Conversation memory store — sliding window of last N turns per conversation
MAX_HISTORY_TURNS = 5    # Keep last 5 exchanges per conversation
MAX_CONVERSATIONS = 1000  # Evict oldest after this limit
conversation_store = OrderedDict()  # {conversation_id: [{"role": ..., "content": ...}, ...]}


def get_conversation_history(conversation_id: str):
    """Get conversation history for a given ID."""
    return conversation_store.get(conversation_id, [])


def store_turn(conversation_id: str, user_question: str, assistant_answer: str):
    """Store a conversation turn (user + assistant) with sliding window."""
    if conversation_id not in conversation_store:
        # Evict oldest conversation if at capacity
        if len(conversation_store) >= MAX_CONVERSATIONS:
            conversation_store.popitem(last=False)
        conversation_store[conversation_id] = []
    
    history = conversation_store[conversation_id]
    # Add the new turn
    history.append({"role": "user", "content": user_question})
    # Truncate assistant answer to save tokens (max 200 chars)
    short_answer = assistant_answer[:200] + "..." if len(assistant_answer) > 200 else assistant_answer
    history.append({"role": "assistant", "content": short_answer})
    
    # Enforce sliding window — keep last N turns (each turn = 2 messages)
    max_messages = MAX_HISTORY_TURNS * 2
    if len(history) > max_messages:
        conversation_store[conversation_id] = history[-max_messages:]


@asynccontextmanager
async def lifespan(app):
    """Initialize retriever and LLM client on server startup."""
    global retriever, groq_client
    
    logger.info("Initializing ClearPath RAG Chatbot...")
    
    # Initialize retriever (loads FAISS index)
    try:
        retriever = Retriever()
        logger.info("Retriever initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize retriever: {e}")
        logger.error("Run 'python -m backend.rag.embeddings' first to build the index.")
        raise
    
    # Initialize Groq client
    try:
        groq_client = get_groq_client()
        logger.info("Groq client initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize Groq client: {e}")
        raise
    
    logger.info("ClearPath RAG Chatbot ready!")
    yield


# Initialize FastAPI with lifespan
app = FastAPI(
    title="ClearPath RAG Chatbot",
    description="Customer support chatbot for ClearPath project management tool",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Main chatbot endpoint.
    
    Orchestration:
    1. Router classifies query → picks model
    2. Retriever finds top-k relevant chunks
    3. LLM generates response with context
    4. Evaluator checks response → flags
    5. Return structured response
    """
    if not request.question or not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    
    question = request.question.strip()
    conversation_id = request.conversation_id or f"conv_{uuid.uuid4().hex[:12]}"
    
    # Step 1: Route the query
    routing = classify_query(question)
    classification = routing["classification"]
    model_used = routing["model_used"]
    
    logger.info(f"Query: \"{question[:80]}...\" → {classification} → {model_used}")
    logger.info(f"  Routing signals: {routing['signals']}")
    
    # Step 2: Handle pure greetings differently — no need to search docs
    # Only skip retrieval for short greetings like "Hi!" or "Hello"
    # NOT for "Hi, what is the pricing?" which contains an actual question
    is_greeting = ("greeting_detected" in routing.get("signals", []) 
                   and len(question.split()) <= 5)
    
    if is_greeting:
        # For greetings, skip retrieval and respond naturally
        retrieved_chunks = []
        chunks_retrieved = 0
        greeting_context = "The user is greeting you. Respond warmly and let them know you can help with ClearPath questions about features, pricing, setup, troubleshooting, and more."
        history = get_conversation_history(conversation_id)
        llm_result = groq_client.generate(question, greeting_context, model_used, conversation_history=history)
        evaluator_flags = []
    else:
        # Normal flow: retrieve docs and evaluate
        retrieved_chunks = retriever.retrieve(question)
        chunks_retrieved = len(retrieved_chunks)
        
        logger.info(f"  Retrieved {chunks_retrieved} chunks")
        
        # Step 3: Build context and generate response with conversation history
        context = retriever.build_context(retrieved_chunks)
        history = get_conversation_history(conversation_id)
        llm_result = groq_client.generate(question, context, model_used, conversation_history=history)
        
        # Step 4: Evaluate the response
        evaluator_flags = evaluate_response(llm_result["answer"], chunks_retrieved, retrieved_chunks)
    
    # Extract results from LLM
    answer = llm_result["answer"]
    tokens_input = llm_result["tokens_input"]
    tokens_output = llm_result["tokens_output"]
    latency_ms = llm_result["latency_ms"]
    
    # Add warning message if flagged
    warning = get_warning_message(evaluator_flags)
    if warning:
        answer = f"{warning}\n\n{answer}"
        logger.info(f"  Evaluator flags: {evaluator_flags}")
    
    # Log routing decision (required format)
    routing_log = create_routing_log(
        query=question,
        classification=classification,
        model_used=model_used,
        tokens_input=tokens_input,
        tokens_output=tokens_output,
        latency_ms=latency_ms
    )
    logger.info(f"  Routing log: {routing_log}")
    
    # Step 5: Build response
    sources = [
        Source(
            document=chunk["document"],
            page=chunk["page"],
            relevance_score=chunk.get("relevance_score")
        )
        for chunk in retrieved_chunks
    ]
    
    response = QueryResponse(
        answer=answer,
        metadata=Metadata(
            model_used=model_used,
            classification=classification,
            tokens=TokenUsage(input=tokens_input, output=tokens_output),
            latency_ms=latency_ms,
            chunks_retrieved=chunks_retrieved,
            evaluator_flags=evaluator_flags
        ),
        sources=sources,
        conversation_id=conversation_id
    )
    
    # Store this turn in conversation memory
    store_turn(conversation_id, question, answer)
    logger.info(f"  Memory: {len(get_conversation_history(conversation_id)) // 2} turns stored for {conversation_id}")
    
    return response


@app.post("/query/stream")
async def query_stream(request: QueryRequest):
    """
    Streaming endpoint — returns tokens via Server-Sent Events (SSE).
    Same pipeline as /query but streams the LLM response token-by-token.
    """
    if not request.question or not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    
    question = request.question.strip()
    conversation_id = request.conversation_id or f"conv_{uuid.uuid4().hex[:12]}"
    
    # Steps 1-2: Route and retrieve (non-streamed, fast)
    routing = classify_query(question)
    classification = routing["classification"]
    model_used = routing["model_used"]
    
    is_greeting = ("greeting_detected" in routing.get("signals", [])
                   and len(question.split()) <= 5)
    
    if is_greeting:
        retrieved_chunks = []
        context = "The user is greeting you. Respond warmly and let them know you can help with ClearPath questions."
    else:
        retrieved_chunks = retriever.retrieve(question)
        context = retriever.build_context(retrieved_chunks)
    
    history = get_conversation_history(conversation_id)
    
    # Build sources for the metadata event
    sources = [
        {"document": c["document"], "page": c["page"], "relevance_score": c.get("relevance_score")}
        for c in retrieved_chunks
    ]
    evaluator_flags = []  # Will be computed after full response
    
    def event_generator():
        full_answer = ""
        
        # Send metadata first
        meta_event = {
            "type": "metadata",
            "classification": classification,
            "model_used": model_used,
            "chunks_retrieved": len(retrieved_chunks),
            "sources": sources,
            "conversation_id": conversation_id
        }
        yield f"data: {json.dumps(meta_event)}\n\n"
        
        # Stream tokens
        for chunk in groq_client.generate_stream(question, context, model_used, conversation_history=history):
            if chunk["type"] == "token":
                full_answer += chunk["content"]
                yield f"data: {json.dumps(chunk)}\n\n"
            elif chunk["type"] == "done":
                # Evaluate the full response
                if not is_greeting:
                    flags = evaluate_response(full_answer, len(retrieved_chunks), retrieved_chunks)
                else:
                    flags = []
                
                # Store in conversation memory
                store_turn(conversation_id, question, full_answer)
                
                done_event = {
                    "type": "done",
                    "tokens_input": chunk["tokens_input"],
                    "tokens_output": chunk["tokens_output"],
                    "latency_ms": chunk["latency_ms"],
                    "evaluator_flags": flags
                }
                yield f"data: {json.dumps(done_event)}\n\n"
            elif chunk["type"] == "error":
                yield f"data: {json.dumps(chunk)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


# Serve the frontend
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


@app.get("/")
async def serve_frontend():
    """Serve the chat interface."""
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "ClearPath RAG Chatbot API is running. POST to /query to get started."}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "clearpath-chatbot"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=PORT, reload=True)
