import time
import re
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from app.models.inference import InferenceRequest, InferenceResponse
from app.models.fact import Fact
from app.services.retrieval_service import retrieval_service
from app.models.retrieval import RetrievalQuery
from app.db.graph_store import graph_store

class InferenceService:
    def infer_answer(self, req: InferenceRequest) -> InferenceResponse:
        start_t = time.perf_counter()

        # Extract temporal anchor if present in query text (e.g. "in 2021", "in 2023")
        as_of = req.as_of
        year_match = re.search(r"\b(?:in|during|around)\s+(\d{4})\b", req.query, re.IGNORECASE)
        if year_match and not as_of:
            year_int = int(year_match.group(1))
            as_of = datetime(year_int, 6, 1, tzinfo=timezone.utc)

        eval_as_of = as_of if as_of else datetime.now(timezone.utc)
        as_of_str = eval_as_of.isoformat()

        # Step 1: Retrieve relevant facts as of the target point in time
        retrieval_res = retrieval_service.retrieve(RetrievalQuery(
            query=req.query,
            as_of=eval_as_of,
            session_id=req.session_id,
            top_k=5,
            include_neighborhood=True
        ))

        # Step 2: Retrieve full history (unfiltered by as_of) for the primary entities to detect transitions
        entities_found = set()
        for f in retrieval_res.matched_facts:
            entities_found.add(f.subject)

        all_historical_facts: List[Fact] = []
        for ent in entities_found:
            all_historical_facts.extend(graph_store.get_facts(as_of=None, subject=ent, limit=50))

        # Step 3: Construct Reasoning Chain
        reasoning_chain = []
        reasoning_chain.append(f"1. Parsed query intent and temporal anchor (evaluated at: {as_of_str[:10]}).")

        if not retrieval_res.matched_facts:
            latency = (time.perf_counter() - start_t) * 1000
            return InferenceResponse(
                query=req.query,
                as_of=as_of_str,
                answer="No verified temporal facts found in memory matching this query.",
                reasoning_chain=reasoning_chain + ["2. No graph triplets matched query constraints."],
                supporting_facts=[],
                superseded_facts=[],
                temporal_span_analyzed={"as_of": as_of_str, "status": "no_match"},
                confidence=0.0,
                latency_ms=round(latency, 2)
            )

        top_fact = retrieval_res.matched_facts[0]
        reasoning_chain.append(
            f"2. Retrieved temporally valid triplet: ({top_fact.subject} -> {top_fact.predicate} -> {top_fact.object}) "
            f"effective from {top_fact.valid_from.isoformat()[:10]}"
            f"{' to ' + top_fact.valid_to.isoformat()[:10] if top_fact.valid_to else ' (ongoing)'}."
        )

        # Check for supersession
        superseded = [f for f in all_historical_facts if f.superseded_by == top_fact.id or (f.subject == top_fact.subject and f.predicate == top_fact.predicate and f.valid_to and f.id != top_fact.id)]
        
        if superseded:
            oldest = superseded[0]
            reasoning_chain.append(
                f"3. Historical transition detected: Previously ({oldest.subject} -> {oldest.predicate} -> {oldest.object}), "
                f"which was invalidated on {oldest.valid_to.isoformat()[:10] if oldest.valid_to else 'transition'}."
            )

        # Formulate concise, grounded answer
        is_user = top_fact.subject.lower() == "user"
        subj_name = "You" if is_user else top_fact.subject
        possessive = "Your" if is_user else f"{top_fact.subject}'s"

        if top_fact.predicate in ["backend_framework"]:
            if as_of:
                answer = f"As of {as_of_str[:4]}, {possessive} backend framework was {top_fact.object}."
            else:
                answer = f"{possessive} backend framework is {top_fact.object}."
                if superseded:
                    answer += f" (Previously was {superseded[0].object})."
        elif top_fact.predicate in ["database_used", "uses_database"]:
            if as_of:
                answer = f"As of {as_of_str[:4]}, {subj_name} used {top_fact.object}."
            else:
                answer = f"{subj_name} currently use{'s' if not is_user else ''} {top_fact.object}."
                if superseded:
                    answer += f" (Previously used {superseded[0].object})."
        elif top_fact.predicate in ["lives_in", "resides_in"]:
            if as_of:
                answer = f"As of {as_of_str[:4]}, {subj_name} lived in {top_fact.object}."
            else:
                answer = f"{subj_name} currently live{'s' if not is_user else ''} in {top_fact.object}."
                if superseded:
                    answer += f" (Previously lived in {superseded[0].object})."
        elif top_fact.predicate in ["works_at", "employed_by"]:
            if as_of:
                answer = f"As of {as_of_str[:4]}, {subj_name} worked at {top_fact.object}."
            else:
                answer = f"{subj_name} currently work{'s' if not is_user else ''} at {top_fact.object}."
                if superseded:
                    answer += f" (Previously worked at {superseded[0].object})."
        elif top_fact.predicate in ["role_title"]:
            answer = f"{subj_name} hold{'s' if not is_user else ''} the role of {top_fact.object}."
        else:
            answer = f"Based on memory records, {top_fact.subject} {top_fact.predicate.replace('_', ' ')} {top_fact.object}."

        reasoning_chain.append("4. Generated grounded answer with temporal interval bounds.")

        latency = (time.perf_counter() - start_t) * 1000

        return InferenceResponse(
            query=req.query,
            as_of=as_of_str,
            answer=answer,
            reasoning_chain=reasoning_chain,
            supporting_facts=retrieval_res.matched_facts,
            superseded_facts=superseded,
            temporal_span_analyzed={"as_of": as_of_str, "status": "verified"},
            confidence=top_fact.confidence,
            latency_ms=round(latency, 2)
        )

inference_service = InferenceService()
