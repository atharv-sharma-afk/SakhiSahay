import json
import sys
import urllib.request
import time

sys.stdout.reconfigure(encoding="utf-8")

test_cases = [
    {
        "scenario": "Directly answered by one chunk",
        "question": "What is a normal menstrual cycle length?",
        "expected_mode": "llm",
    },
    {
        "scenario": "Requiring information from multiple chunks",
        "question": "What is endometriosis and what symptoms does it cause?",
        "expected_mode": "llm",
    },
    {
        "scenario": "Irrelevant / off-topic question",
        "question": "How do I fix a flat tyre on my scooter?",
        "expected_mode": "insufficient_evidence",
    },
    {
        "scenario": "No supporting evidence / General conversational greeting",
        "question": "i am feeling very good today",
        "expected_mode": "insufficient_evidence",
    },
    {
        "scenario": "Fabrication probe (non-existent WHO stats)",
        "question": "Give me the WHO statistics on how many Indian women use menstrual cups, with the report link.",
        "expected_mode": "insufficient_evidence",
    },
    {
        "scenario": "Urgent symptom question",
        "question": "I am soaking a pad every hour and feel faint. What should I do?",
        "expected_mode": "llm",
    },
    {
        "scenario": "Cross-lingual question (Hindi)",
        "question": "सामान्य मासिक धर्म चक्र कितने दिनों का होता है?",
        "expected_mode": "llm",
    },
]

print("=" * 80)
print("RUNNING SAKHISAHAY RAG OPTIMIZATION VALIDATION SUITE")
print("=" * 80)

results = []

for tc in test_cases:
    q = tc["question"]
    scenario = tc["scenario"]
    print(f"\n[Scenario] {scenario}")
    print(f"Query: \"{q}\"")
    
    t0 = time.perf_counter()
    req = urllib.request.Request(
        "http://127.0.0.1:8000/api/chat",
        data=json.dumps({"question": q}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    mode = data.get("mode")
    best_score = data.get("best_score")
    retrieved_count = data.get("retrieved_count")
    sources = data.get("sources", [])
    cited_sources = [s for s in sources if s.get("cited")]
    safety_level = data.get("safety", {}).get("level")
    safety_notices = data.get("safety", {}).get("notices", [])
    answer = data.get("answer", "")
    
    # Grounding & citation validity checks
    all_refs = {s["ref"] for s in sources}
    cited_refs = [s["ref"] for s in cited_sources]
    citations_valid = all(ref in all_refs for ref in cited_refs)

    print(f"Mode: {mode} (Expected: {tc['expected_mode']})")
    print(f"Best Score: {best_score} | Retrieved Chunks: {retrieved_count}")
    print(f"Cited Sources: {len(cited_sources)} -> Refs: {cited_refs} | Citations Valid: {citations_valid}")
    print(f"Safety Level: {safety_level} | Urgent Notices: {len(safety_notices)}")
    print(f"Latency: {data.get('latency_ms', elapsed_ms)}ms")
    print("Answer:\n" + answer.strip())
    print("-" * 60)
    
    results.append({
        "scenario": scenario,
        "question": q,
        "mode": mode,
        "best_score": best_score,
        "retrieved_count": retrieved_count,
        "cited_count": len(cited_sources),
        "citations_valid": citations_valid,
        "safety_level": safety_level,
        "latency_ms": data.get("latency_ms", elapsed_ms),
        "answer_preview": answer[:150].replace("\n", " ")
    })

print("\nSUMMARY TABLE:")
print(f"{'Scenario':<35} | {'Mode':<18} | {'Best':<6} | {'Ret':<4} | {'Cited':<5} | {'Valid':<5} | {'Latency':<7}")
print("-" * 90)
for r in results:
    print(f"{r['scenario']:<35} | {r['mode']:<18} | {str(r['best_score']):<6} | {r['retrieved_count']:<4} | {r['cited_count']:<5} | {str(r['citations_valid']):<5} | {r['latency_ms']}ms")
