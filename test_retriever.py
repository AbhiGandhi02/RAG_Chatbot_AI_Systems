"""Test script for Phase 2: RAG Pipeline"""

# Step 1: Test Retriever
print("=" * 60)
print("STEP 1: Testing Retriever")
print("=" * 60)

from backend.rag.retriever import Retriever
r = Retriever()

chunks = r.retrieve("What is the pricing for Pro plan?")
print(f"Retrieved {len(chunks)} chunks\n")
for c in chunks:
    print(f"  Score: {c['relevance_score']} | {c['document']}")
    print(f"  Text: {c['text'][:100]}...")
    print()

# Step 2: Test Context Building
print("=" * 60)
print("STEP 2: Testing Context Building")
print("=" * 60)
context = r.build_context(chunks)
print(f"Context length: {len(context)} characters")
print(f"Preview: {context[:200]}...")
print()

# Step 3: Test Groq LLM Client
print("=" * 60)
print("STEP 3: Testing Groq LLM Client")
print("=" * 60)

from backend.llm.groq_client import get_groq_client
client = get_groq_client()

result = client.generate(
    query="What is the Pro plan price?",
    context=context,
    model="llama-3.1-8b-instant"
)

print(f"Model: llama-3.1-8b-instant")
print(f"Tokens - Input: {result['tokens_input']}, Output: {result['tokens_output']}")
print(f"Latency: {result['latency_ms']}ms")
print(f"\nAnswer:\n{result['answer']}")
print()

# Step 4: Return source documents
print("=" * 60)
print("STEP 4: Source Documents")
print("=" * 60)
for c in chunks:
    score = c.get('relevance_score', 'N/A')
    print(f"  📄 {c['document']} (page {c['page']}) — score: {score}")

print("\n✅ Phase 2 RAG Pipeline test complete!")
