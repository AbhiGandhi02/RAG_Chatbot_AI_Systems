"""Test script for Phase 5: API Endpoint
Run this AFTER starting the server in another terminal.
"""

import requests
import json

BASE_URL = "http://localhost:8000"

print("=" * 60)
print("PHASE 5: Testing API Endpoint")
print("=" * 60)

# Test 1: Health check
print("\n--- Test 1: Health Check (GET /health) ---")
try:
    r = requests.get(f"{BASE_URL}/health")
    print(f"  Status: {r.status_code}")
    print(f"  Response: {r.json()}")
except Exception as e:
    print(f"  ❌ Server not running? Error: {e}")
    print("  Start the server first: .\\venv\\Scripts\\python -m backend.main")
    exit(1)

# Test 2: Simple query
print("\n--- Test 2: Simple Query ---")
r = requests.post(f"{BASE_URL}/query", json={"question": "What is ClearPath?"})
data = r.json()
print(f"  Status: {r.status_code}")
print(f"  Classification: {data['metadata']['classification']}")
print(f"  Model: {data['metadata']['model_used']}")
print(f"  Tokens: in={data['metadata']['tokens']['input']}, out={data['metadata']['tokens']['output']}")
print(f"  Latency: {data['metadata']['latency_ms']}ms")
print(f"  Chunks: {data['metadata']['chunks_retrieved']}")
print(f"  Flags: {data['metadata']['evaluator_flags']}")
print(f"  Sources: {len(data['sources'])} docs")
print(f"  Answer: {data['answer'][:150]}...")

# Test 3: Complex query (should use 70B model)
print("\n--- Test 3: Complex Query ---")
r = requests.post(f"{BASE_URL}/query", json={
    "question": "How do I configure webhook integrations and what are the rate limits?"
})
data = r.json()
print(f"  Status: {r.status_code}")
print(f"  Classification: {data['metadata']['classification']}")
print(f"  Model: {data['metadata']['model_used']}")
print(f"  Latency: {data['metadata']['latency_ms']}ms")
print(f"  Answer: {data['answer'][:150]}...")

# Test 4: Greeting (simple)
print("\n--- Test 4: Greeting ---")
r = requests.post(f"{BASE_URL}/query", json={"question": "Hi!"})
data = r.json()
print(f"  Classification: {data['metadata']['classification']}")
print(f"  Model: {data['metadata']['model_used']}")
print(f"  Answer: {data['answer'][:100]}...")

# Test 5: Empty question (should error)
print("\n--- Test 5: Empty Question (expect 400) ---")
r = requests.post(f"{BASE_URL}/query", json={"question": ""})
print(f"  Status: {r.status_code}")

print(f"\n{'=' * 60}")
print("✅ Phase 5 API Endpoint tests complete!")
print(f"{'=' * 60}")
