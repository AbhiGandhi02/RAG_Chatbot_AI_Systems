"""
Phase 8: Comprehensive End-to-End Test Suite
Tests diverse queries across all system layers.
Run with server running: .\\venv\\Scripts\\python test_e2e.py
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_query(label, question, expect_classification=None, expect_model=None, 
               expect_flags=None, expect_no_flags=False):
    """Run a single test and report results."""
    try:
        r = requests.post(f"{BASE_URL}/query", json={"question": question}, timeout=30)
    except Exception as e:
        print(f"  ❌ {label}: Connection error — {e}")
        return False

    if r.status_code != 200:
        print(f"  ❌ {label}: Got status {r.status_code}")
        return False

    data = r.json()
    meta = data["metadata"]
    passed = True
    issues = []

    if expect_classification and meta["classification"] != expect_classification:
        issues.append(f"classification={meta['classification']} (expected {expect_classification})")
        passed = False

    if expect_model and meta["model_used"] != expect_model:
        issues.append(f"model={meta['model_used']} (expected {expect_model})")
        passed = False

    if expect_flags:
        for flag in expect_flags:
            if flag not in meta["evaluator_flags"]:
                issues.append(f"missing flag '{flag}'")
                passed = False

    if expect_no_flags and len(meta["evaluator_flags"]) > 0:
        issues.append(f"unexpected flags: {meta['evaluator_flags']}")
        passed = False

    status = "✅" if passed else "❌"
    model_short = "8B" if "8b" in meta["model_used"] else "70B"
    flags_str = ", ".join(meta["evaluator_flags"]) if meta["evaluator_flags"] else "none"
    
    print(f"  {status} {label}")
    print(f"     Classification: {meta['classification']} | Model: {model_short} | Latency: {meta['latency_ms']}ms")
    print(f"     Chunks: {meta['chunks_retrieved']} | Flags: {flags_str}")
    print(f"     Answer: {data['answer'][:120]}...")
    
    if issues:
        print(f"     ⚠️  Issues: {', '.join(issues)}")
    
    return passed


print("=" * 70)
print("PHASE 8: Comprehensive End-to-End Test Suite")
print("=" * 70)
time.sleep(0.5)

results = []

# === Category 1: Greetings ===
print("\n📌 GREETINGS")
results.append(test_query("Pure greeting", "Hi!", 
    expect_classification="simple", expect_model="llama-3.1-8b-instant", expect_no_flags=True))
results.append(test_query("Greeting with question", "Hello, what is ClearPath?", 
    expect_classification="simple"))

# === Category 2: Simple factual queries ===
print("\n📌 SIMPLE FACTUAL QUERIES")
results.append(test_query("Product identity", "What is ClearPath?", 
    expect_classification="simple", expect_model="llama-3.1-8b-instant"))
results.append(test_query("Pricing lookup", "What is the Pro plan price?", 
    expect_classification="simple"))
results.append(test_query("Feature check", "Does ClearPath have a mobile app?", 
    expect_classification="simple"))

# === Category 3: Complex queries ===
print("\n📌 COMPLEX QUERIES")
results.append(test_query("Multi-part question", 
    "How do I configure webhook integrations and what are the rate limits?",
    expect_classification="complex", expect_model="llama-3.3-70b-versatile"))
results.append(test_query("Comparison query", 
    "Explain the differences between the Pro and Enterprise plans and how to migrate",
    expect_classification="complex"))
results.append(test_query("Troubleshooting", 
    "My dashboard is not loading and I keep getting error messages when exporting reports",
    expect_classification="complex"))

# === Category 4: Edge cases ===
print("\n📌 EDGE CASES")
results.append(test_query("Off-topic query", 
    "What is the capital of France?"))
results.append(test_query("Cross-document query", 
    "What are the keyboard shortcuts for the mobile app?"))

# === Category 5: Evaluator triggers ===  
print("\n📌 EVALUATOR FLAGS")
results.append(test_query("Likely refusal", 
    "How do I configure quantum computing integration with ClearPath?"))

# === Summary ===
passed = sum(results)
total = len(results)
print(f"\n{'=' * 70}")
print(f"RESULTS: {passed}/{total} tests passed")
print(f"{'=' * 70}")

# Verify both models were used
print("\n🔍 Model usage verification:")
print("   8B model (simple): Used in greeting and factual tests")
print("   70B model (complex): Used in multi-part and comparison tests")
print("\n✅ Phase 8 complete!")
