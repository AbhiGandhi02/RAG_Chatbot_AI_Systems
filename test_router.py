"""Test script for Phase 3: Model Router (Query Classifier)"""

from backend.router.classifier import classify_query

print("=" * 60)
print("PHASE 3: Testing Model Router")
print("=" * 60)

test_queries = [
    # Should be SIMPLE
    ("Hi!", "simple"),
    ("Hello, how are you?", "simple"),
    ("Thanks!", "simple"),
    ("What is ClearPath?", "simple"),
    ("Is ClearPath free?", "simple"),

    # Should be COMPLEX
    ("How do I configure webhook integrations with Slack and what are the rate limits?", "complex"),
    ("Explain the differences between the Pro and Enterprise plans and how to migrate between them", "complex"),
    ("My dashboard is not working and I'm getting an error when I try to export reports. Can you help?", "complex"),
    ("Why is the API returning 403 errors? I've tried multiple times and it's still broken.", "complex"),
    ("Walk me through the steps to set up custom workflows with automation rules", "complex"),
]

correct = 0
total = len(test_queries)

for query, expected in test_queries:
    result = classify_query(query)
    status = "✅" if result["classification"] == expected else "❌"
    if result["classification"] == expected:
        correct += 1

    print(f"\n{status} Query: \"{query}\"")
    print(f"   Expected: {expected.upper()} | Got: {result['classification'].upper()}")
    print(f"   Model: {result['model_used']}")
    print(f"   Signals: {result['signals']}")

print(f"\n{'=' * 60}")
print(f"Results: {correct}/{total} correct")
print(f"{'=' * 60}")

# Show structured routing log format
print("\nSample Routing Log (required format):")
from backend.router.classifier import create_routing_log
log = create_routing_log(
    query="How do I configure webhooks?",
    classification="complex",
    model_used="llama-3.3-70b-versatile",
    tokens_input=1200,
    tokens_output=150,
    latency_ms=800
)
for k, v in log.items():
    print(f"  {k}: {v}")

print("\n✅ Phase 3 Model Router test complete!")
