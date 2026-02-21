"""Test script for Phase 4: Output Evaluator"""

from backend.evaluator.evaluator import evaluate_response, get_warning_message

print("=" * 60)
print("PHASE 4: Testing Output Evaluator")
print("=" * 60)

# Test 1: no_context flag — LLM answered but no chunks retrieved
print("\n--- Test 1: no_context flag ---")
flags = evaluate_response(
    answer="ClearPath offers three pricing plans starting at $29/month.",
    chunks_retrieved=0
)
print(f"  Answer: LLM gave an answer but 0 chunks were retrieved")
print(f"  Flags: {flags}")
print(f"  Warning: {get_warning_message(flags)}")
assert "no_context" in flags, "Should flag no_context"
print("  ✅ Passed")

# Test 2: refusal flag — LLM says it doesn't know
print("\n--- Test 2: refusal flag ---")
flags = evaluate_response(
    answer="I don't have enough information in the provided documentation to answer that question.",
    chunks_retrieved=3
)
print(f"  Answer: LLM refused to answer")
print(f"  Flags: {flags}")
print(f"  Warning: {get_warning_message(flags)}")
assert "refusal" in flags, "Should flag refusal"
print("  ✅ Passed")

# Test 3: conflicting_info flag — Answer mentions conflicting docs
print("\n--- Test 3: conflicting_info flag ---")
flags = evaluate_response(
    answer="The pricing page says $49/month, however, another document states $45/month. This appears to conflict with the enterprise guide.",
    chunks_retrieved=4,
    retrieved_chunks=[
        {"document": "doc1.pdf", "text": "..."},
        {"document": "doc2.pdf", "text": "..."},
        {"document": "doc3.pdf", "text": "..."},
        {"document": "doc4.pdf", "text": "..."},
    ]
)
print(f"  Answer: LLM found conflicting info across docs")
print(f"  Flags: {flags}")
print(f"  Warning: {get_warning_message(flags)}")
assert "conflicting_info" in flags, "Should flag conflicting_info"
print("  ✅ Passed")

# Test 4: Clean response — no flags
print("\n--- Test 4: Clean response (no flags) ---")
flags = evaluate_response(
    answer="The Pro plan costs $49/month and includes advanced reports, API access, and priority support.",
    chunks_retrieved=3,
    retrieved_chunks=[
        {"document": "pricing.pdf", "text": "..."},
        {"document": "pricing.pdf", "text": "..."},
        {"document": "features.pdf", "text": "..."},
    ]
)
print(f"  Answer: Clean, confident answer")
print(f"  Flags: {flags}")
print(f"  Warning: {get_warning_message(flags)}")
assert len(flags) == 0, "Should have no flags"
print("  ✅ Passed")

# Test 5: Both no_context + refusal
print("\n--- Test 5: no_context + refusal combined ---")
flags = evaluate_response(
    answer="I cannot find any information about that topic in the documentation.",
    chunks_retrieved=0
)
print(f"  Answer: No chunks AND LLM refused")
print(f"  Flags: {flags}")
print(f"  Warning: {get_warning_message(flags)}")
assert "refusal" in flags, "Should flag refusal"
print("  ✅ Passed")

print(f"\n{'=' * 60}")
print("Results: 5/5 tests passed")
print(f"{'=' * 60}")
print("\n✅ Phase 4 Output Evaluator test complete!")
