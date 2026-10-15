import sys
import time
import httpx
import json

BASE_URL = "http://127.0.0.1:8000"
FRONTEND_URL = "http://localhost:3000"

def test_acceptance_flow():
    print("=" * 70)
    print("CHRONOS MEMORY QA ACCEPTANCE VERIFICATION SUITE")
    print("=" * 70)

    client = httpx.Client(timeout=10.0)

    # 1. Health check & Frontend connectivity
    print("\n[TEST 2] Verifying Frontend and Backend Connectivity...")
    try:
        backend_health = client.get(f"{BASE_URL}/health")
        assert backend_health.status_code == 200, f"Backend health returned {backend_health.status_code}"
        health_data = backend_health.json()
        print(f"  -> Backend health status: {health_data.get('status')} (Database: {health_data.get('database')})")
    except Exception as e:
        print(f"  FAILED: Backend unreachable: {e}")
        sys.exit(1)

    try:
        frontend_resp = client.get(FRONTEND_URL)
        assert frontend_resp.status_code == 200, f"Frontend returned {frontend_resp.status_code}"
        print(f"  -> Frontend reachable at {FRONTEND_URL} (Status 200 OK)")
    except Exception as e:
        print(f"  FAILED: Frontend unreachable: {e}")
        sys.exit(1)

    # Reset DB to a clean state for testing
    print("\nResetting database for clean test run...")
    reset_resp = client.post(f"{BASE_URL}/api/seed/reset")
    print(f"  -> Database reset status: {reset_resp.status_code}")

    # [TEST 3] Backend can read/write persisted graph data
    print("\n[TEST 3] Testing backend read/write to persisted graph data...")
    test_ep = {
        "session_id": "qa_session_001",
        "speaker": "user",
        "text": "My database is PostgreSQL."
    }
    ep_resp = client.post(f"{BASE_URL}/api/episodes", json=test_ep)
    assert ep_resp.status_code == 200, f"Failed to ingest test episode: {ep_resp.text}"
    ep_data = ep_resp.json()
    assert len(ep_data["extracted_facts"]) > 0, "No facts extracted from test episode"
    print(f"  -> Wrote episode and extracted fact: {ep_data['extracted_facts'][0]['subject']} -> {ep_data['extracted_facts'][0]['predicate']} -> {ep_data['extracted_facts'][0]['object']}")
    
    # Read back graph
    graph_resp = client.get(f"{BASE_URL}/api/graph")
    assert graph_resp.status_code == 200, f"Failed to read graph: {graph_resp.text}"
    graph_data = graph_resp.json()
    assert len(graph_data.get("nodes", [])) > 0, "Graph has no nodes"
    assert len(graph_data.get("edges", [])) > 0, "Graph has no edges"
    print(f"  -> Successfully read graph ({len(graph_data['nodes'])} nodes, {len(graph_data['edges'])} edges)")
    print("  -> PASSED: Test 3 (read/write persisted graph data)")

    # Reset DB before starting tests 4-8
    client.post(f"{BASE_URL}/api/seed/reset")

    # [TEST 4] Ingest "My backend framework is Flask."
    print("\n[TEST 4] Ingesting: 'My backend framework is Flask.'...")
    ep1_payload = {
        "session_id": "qa_framework_session",
        "speaker": "user",
        "text": "My backend framework is Flask."
    }
    r4 = client.post(f"{BASE_URL}/api/episodes", json=ep1_payload)
    assert r4.status_code == 200, f"Ingestion 4 failed: {r4.text}"
    d4 = r4.json()
    extracted_4 = d4.get("extracted_facts", [])
    assert len(extracted_4) == 1, f"Expected 1 fact, got {len(extracted_4)}"
    f4 = extracted_4[0]
    print(f"  -> Extracted: ({f4['subject']}, {f4['predicate']}, {f4['object']}) [status={f4['status']}, is_current={f4['is_current']}]")
    assert f4['predicate'] == "backend_framework"
    assert f4['object'] == "Flask"
    assert f4['status'] == "active"
    print("  -> PASSED: Test 4")

    # Short delay to ensure distinct timestamps
    time.sleep(1.0)

    # [TEST 5] Ingest "I switched my backend to FastAPI."
    print("\n[TEST 5] Ingesting: 'I switched my backend to FastAPI.'...")
    ep2_payload = {
        "session_id": "qa_framework_session",
        "speaker": "user",
        "text": "I switched my backend to FastAPI."
    }
    r5 = client.post(f"{BASE_URL}/api/episodes", json=ep2_payload)
    assert r5.status_code == 200, f"Ingestion 5 failed: {r5.text}"
    d5 = r5.json()
    extracted_5 = d5.get("extracted_facts", [])
    invalidated_5 = d5.get("invalidated_facts", [])
    assert len(extracted_5) == 1, f"Expected 1 new fact, got {len(extracted_5)}"
    f5 = extracted_5[0]
    print(f"  -> Extracted: ({f5['subject']}, {f5['predicate']}, {f5['object']}) [status={f5['status']}, is_current={f5['is_current']}]")
    assert f5['predicate'] == "backend_framework"
    assert f5['object'] == "FastAPI"
    assert f5['status'] == "active"
    print("  -> PASSED: Test 5")

    # [TEST 6] Verify FastAPI is active and Flask is superseded
    print("\n[TEST 6] Verifying FastAPI is active and Flask is superseded...")
    assert len(invalidated_5) >= 1, f"Expected at least 1 invalidated fact, got {len(invalidated_5)}"
    inv = invalidated_5[0]
    assert inv['object'] == "Flask", f"Expected Flask to be invalidated, got {inv['object']}"
    assert inv['status'] == "superseded", f"Expected status 'superseded', got {inv['status']}"
    assert inv['is_current'] is False, f"Expected is_current False, got {inv['is_current']}"
    assert inv['valid_to'] is not None, "Expected valid_to to be closed"

    # Also query graph facts to double check persistence
    all_facts_resp = client.get(f"{BASE_URL}/api/memory/facts")
    all_facts = all_facts_resp.json()
    fastapi_facts = [f for f in all_facts if f['object'] == "FastAPI" and f['predicate'] == "backend_framework"]
    flask_facts = [f for f in all_facts if f['object'] == "Flask" and f['predicate'] == "backend_framework"]

    assert len(fastapi_facts) == 1 and fastapi_facts[0]['status'] == "active" and fastapi_facts[0]['is_current'] is True
    assert len(flask_facts) == 1 and flask_facts[0]['status'] == "superseded" and flask_facts[0]['is_current'] is False
    print(f"  -> FastAPI fact in DB: status={fastapi_facts[0]['status']}, is_current={fastapi_facts[0]['is_current']}")
    print(f"  -> Flask fact in DB: status={flask_facts[0]['status']}, is_current={flask_facts[0]['is_current']}, valid_to={flask_facts[0]['valid_to']}")
    print("  -> PASSED: Test 6")

    # [TEST 7] Ask "What framework do I use now?" and verify FastAPI is returned with evidence
    print("\n[TEST 7] Querying: 'What framework do I use now?'...")
    q7_resp = client.post(f"{BASE_URL}/api/chat", json={"message": "What framework do I use now?"})
    assert q7_resp.status_code == 200, f"Chat query failed: {q7_resp.text}"
    q7_data = q7_resp.json()
    print(f"  -> Answer: {q7_data['answer']}")
    print(f"  -> Evidence status: {q7_data['evidence_status']}, Grounded: {q7_data['grounded']}")
    print(f"  -> Supporting fact IDs: {q7_data['supporting_fact_ids']}")
    assert "FastAPI" in q7_data['answer'], f"FastAPI not in answer: {q7_data['answer']}"
    assert q7_data['grounded'] is True, "Answer should be marked grounded"
    assert len(q7_data['supporting_fact_ids']) > 0, "Should have supporting fact IDs"
    assert q7_data['supporting_fact_ids'][0] == fastapi_facts[0]['id'], "Supporting fact should be FastAPI"
    print("  -> PASSED: Test 7")

    # [TEST 8] Ask "What framework did I use before?" and verify Flask is returned with evidence
    print("\n[TEST 8] Querying: 'What framework did I use before?'...")
    q8_resp = client.post(f"{BASE_URL}/api/chat", json={"message": "What framework did I use before?"})
    assert q8_resp.status_code == 200, f"Chat query failed: {q8_resp.text}"
    q8_data = q8_resp.json()
    print(f"  -> Answer: {q8_data['answer']}")
    print(f"  -> Evidence status: {q8_data['evidence_status']}, Grounded: {q8_data['grounded']}")
    print(f"  -> Supporting fact IDs: {q8_data['supporting_fact_ids']}")
    assert "Flask" in q8_data['answer'], f"Flask not in answer: {q8_data['answer']}"
    assert q8_data['grounded'] is True, "Answer should be marked grounded"
    assert len(q8_data['supporting_fact_ids']) > 0, "Should have supporting fact IDs"
    assert q8_data['supporting_fact_ids'][0] == flask_facts[0]['id'], "Supporting fact should be Flask"
    print("  -> PASSED: Test 8")

    # [TEST 10] Ingest the same fact twice and verify duplicate prevention
    print("\n[TEST 10] Ingesting duplicate fact ('I switched my backend to FastAPI.')...")
    r10 = client.post(f"{BASE_URL}/api/episodes", json=ep2_payload)
    assert r10.status_code == 200
    d10 = r10.json()
    all_facts_after_dup = client.get(f"{BASE_URL}/api/memory/facts").json()
    fastapi_facts_after = [f for f in all_facts_after_dup if f['object'] == "FastAPI" and f['predicate'] == "backend_framework"]
    print(f"  -> Total FastAPI facts in DB after re-ingestion: {len(fastapi_facts_after)}")
    assert len(fastapi_facts_after) == 1, f"Duplicate fact was inserted! Found {len(fastapi_facts_after)}"
    print("  -> PASSED: Test 10 (duplicate prevented)")

    # [TEST 11] Submit ambiguous input and verify no guessed fact is inserted
    print("\n[TEST 11] Ingesting ambiguous input: 'Maybe tomorrow we will consider Kotlin or something.'...")
    facts_count_before = len(client.get(f"{BASE_URL}/api/memory/facts").json())
    ambiguous_payload = {
        "session_id": "qa_framework_session",
        "speaker": "user",
        "text": "Maybe tomorrow we will consider Kotlin or something."
    }
    r11 = client.post(f"{BASE_URL}/api/episodes", json=ambiguous_payload)
    assert r11.status_code == 200
    d11 = r11.json()
    extracted_11 = d11.get("extracted_facts", [])
    facts_count_after = len(client.get(f"{BASE_URL}/api/memory/facts").json())
    print(f"  -> Extracted facts from ambiguous statement: {len(extracted_11)}")
    print(f"  -> Total facts before: {facts_count_before}, after: {facts_count_after}")
    assert len(extracted_11) == 0, f"Guessed/hallucinated facts were inserted: {extracted_11}"
    assert facts_count_after == facts_count_before, "Fact count increased after ambiguous input!"
    print("  -> PASSED: Test 11 (no guessed facts inserted)")

    print("\n" + "=" * 70)
    print("ALL API-BASED ACCEPTANCE TESTS (2, 3, 4, 5, 6, 7, 8, 10, 11) PASSED!")
    print("=" * 70)

if __name__ == "__main__":
    test_acceptance_flow()
