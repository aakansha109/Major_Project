import json

with open("backend/benchmarks/results/preliminary_results.json", "r", encoding="utf-8") as f:
    data = json.load(f)

hybrid_scenarios = data["strategies_evaluated"]["chronos_hybrid"]["scenarios"]
llm_scenarios = data["strategies_evaluated"]["always_llm"]["scenarios"]

print(f"{'ID':<10} | {'Category':<18} | {'Act F1':<7} | {'Hist F1':<8} | {'Hyb Q':<8} | {'LLM Q':<8} | {'Stale':<5} | Title")
print("-" * 95)

for h, l in zip(hybrid_scenarios, llm_scenarios):
    h_tot = h["queries_evaluated"]
    h_pass = h["queries_passed"]
    l_tot = l["queries_evaluated"]
    l_pass = l["queries_passed"]
    act = h["active_f1"]
    hist = h["historical_f1"]
    stale = h["stale_errors"]
    
    if act < 1.0 or hist < 1.0 or h_pass < h_tot:
        print(f"{h['scenario_id']:<10} | {h['category']:<18} | {act:<7.2f} | {hist:<8.2f} | {h_pass}/{h_tot:<6} | {l_pass}/{l_tot:<6} | {stale:<5} | {h['title']}")
        for qd in h.get("query_details", []):
            if not qd["passed"] or qd.get("stale_fact_error"):
                print(f"   -> Query: '{qd['query']}'")
                print(f"      Ans: {qd.get('model_answer', '')[:90]}...")
                print(f"      Passed: {qd['passed']} | Stale: {qd.get('stale_fact_error')} | Reasons: {qd.get('reasons')}")
