import re
import time
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple

from app.models.chat import ChatRequest, ChatResponse, MemoryHistoryResponse, MemoryHistoryItem
from app.models.fact import Fact
from app.models.episode import Episode
from app.models.retrieval import RetrievalQuery
from app.db.graph_store import graph_store
from app.services.retrieval_service import retrieval_service

logger = logging.getLogger("chronos.services.chat")

class ChatService:
    """
    Conversational Retrieval Service.
    Integrates bi-temporal knowledge graph queries with semantic conversation episode search.
    Strictly adheres to research constraints:
    - Never answers a historical question using only the latest fact.
    - Never claims an answer is grounded unless supporting records were retrieved.
    - Accurately distinguishes active vs superseded vs point-in-time facts.
    """

    def parse_temporal_anchor(self, text: str, explicit_as_of: Optional[datetime]) -> Tuple[Optional[datetime], str]:
        """Extracts date/year from query text or uses explicit_as_of"""
        if explicit_as_of is not None:
            return explicit_as_of, "explicit"

        # Regex for YYYY-MM-DD
        date_match = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text)
        if date_match:
            try:
                dt = datetime(int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3)), 12, 0, tzinfo=timezone.utc)
                return dt, "date_parsed"
            except Exception:
                pass

        # Regex for "in 2021", "in 2023", "during 2020", "as of 2022"
        year_match = re.search(r"\b(?:in|during|around|as of|on|back in)\s+(\d{4})\b", text, re.IGNORECASE)
        if year_match:
            y = int(year_match.group(1))
            dt = datetime(y, 6, 1, 12, 0, tzinfo=timezone.utc)
            return dt, "year_parsed"

        # Just year alone: "2021", "2023"
        bare_year = re.search(r"\b(19\d{2}|20\d{2})\b", text)
        if bare_year:
            y = int(bare_year.group(1))
            dt = datetime(y, 6, 1, 12, 0, tzinfo=timezone.utc)
            return dt, "year_parsed"

        return None, "none"

    def detect_query_mode(self, text: str, parsed_date: Optional[datetime]) -> str:
        """
        Determines temporal intent:
        - 'TIMELINE': 'history of', 'timeline of', 'show the history', 'evolution'
        - 'PREVIOUS': 'before', 'previously', 'prior', 'formerly', 'used to', 'past'
        - 'POINT_IN_TIME': has date anchor
        - 'CURRENT': 'now', 'currently', 'today', 'present', or default current state question
        """
        lower = text.lower()
        if any(p in lower for p in ["history of", "timeline of", "show the history", "evolution of", "track my"]):
            return "TIMELINE"
        if any(re.search(rf"\b{p}\b", lower) for p in ["before", "previously", "prior", "formerly", "past", "used to", "earlier", "old"]):
            return "PREVIOUS"
        if parsed_date is not None:
            return "POINT_IN_TIME"
        if any(re.search(rf"\b{p}\b", lower) for p in ["now", "currently", "current", "present", "today"]):
            return "CURRENT"
        return "DEFAULT"

    def extract_subject_and_predicate(self, text: str) -> Tuple[str, Optional[str]]:
        """Maps query keywords to graph subject and candidate predicate"""
        lower = text.lower()
        words = set(re.findall(r"\b\w+\b", lower))

        # 1. Subject extraction
        subject = "User" # default conversational perspective
        proper_names = ["alice", "bob", "charlie", "diana", "evan", "fiona", "george", "hannah", "ian", "sarah", "john smith", "john"]
        for name in proper_names:
            if name in lower:
                subject = name.title()
                break

        # If user explicitly uses 3rd person or 1st person
        if any(p in words for p in ["i", "my", "me", "myself", "we", "our"]):
            subject = "User"

        # 2. Predicate extraction
        predicate = None
        if "frontend" in words or "ui" in words or "frontend framework" in lower:
            predicate = "frontend_framework"
        elif "framework" in words or "backend" in words or "tech stack" in lower:
            predicate = "backend_framework"
        elif any(w in words for w in ["live", "living", "reside", "residing", "moved", "relocate", "location", "city", "house"]):
            predicate = "lives_in"
        elif any(w in words for w in ["work", "working", "job", "company", "employer", "employed", "joined"]):
            predicate = "works_at"
        elif any(w in words for w in ["database", "db", "storage"]):
            predicate = "database_used"
        elif any(w in words for w in ["role", "title", "position"]):
            predicate = "role_title"
        elif any(w in words for w in ["hardware", "laptop", "macbook", "computer", "device", "monitor"]):
            predicate = "uses_hardware"
        elif any(w in words for w in ["cloud", "hosting", "infrastructure"]):
            predicate = "cloud_provider"
        elif any(w in words for w in ["language", "languages", "programming"]):
            predicate = "uses_language"
        elif any(w in words for w in ["tool", "tools", "editor", "ide"]):
            predicate = "uses_tool"
        elif any(w in words for w in ["repo", "repository", "maintain", "maintains"]):
            predicate = "maintains_repo"
        elif any(w in words for w in ["married", "spouse", "wife", "husband"]):
            predicate = "married_to"
        elif any(w in words for w in ["office", "stationed"]):
            predicate = "office_location"
        elif any(w in words for w in ["project", "leading", "leads"]):
            predicate = "leads_project"
        elif any(w in words for w in ["prefer", "preference", "likes"]):
            predicate = "prefers"

        return subject, predicate

    def _get_candidate_predicates(self, predicate: Optional[str]) -> List[Optional[str]]:
        if not predicate:
            return [None]
        candidates = [predicate]
        if predicate in ("database", "database_used"):
            alt = "database" if predicate == "database_used" else "database_used"
            candidates.append(alt)
        elif predicate in ("uses_language", "primary_language"):
            alt = "primary_language" if predicate == "uses_language" else "uses_language"
            candidates.append(alt)
        elif predicate in ("backend_framework", "backend"):
            alt = "backend" if predicate == "backend_framework" else "backend_framework"
            candidates.append(alt)
        return candidates

    async def process_chat(self, req: ChatRequest) -> ChatResponse:
        start_t = time.perf_counter()
        query_text = req.message.strip()
        reasoning_chain = []

        parsed_date, date_source = self.parse_temporal_anchor(query_text, req.as_of)
        mode = self.detect_query_mode(query_text, parsed_date)
        subject, predicate = self.extract_subject_and_predicate(query_text)

        reasoning_chain.append(
            f"1. Analyzed query intent: mode='{mode}', subject='{subject}', predicate='{predicate or 'unspecified'}', date_anchor='{parsed_date.isoformat()[:10] if parsed_date else 'none'}'."
        )

        is_user = subject.lower() == "user"
        subj_display = "You" if is_user else subject
        possessive = "Your" if is_user else f"{subject}'s"

        # =========================================================================
        # CASE 1: TIMELINE / HISTORY QUERY ("Show the history of my backend framework")
        # =========================================================================
        if mode == "TIMELINE":
            reasoning_chain.append("2. Executing chronological history retrieval across temporal knowledge graph.")
            facts = graph_store.get_fact_history(subject=subject, predicate=predicate)
            if not facts and predicate:
                # Try without subject or predicate constraint
                facts = graph_store.get_fact_history(subject=subject)

            if facts:
                valid_span_start = facts[0].valid_from.strftime("%Y-%m-%d")
                transition_lines = []
                for idx, f in enumerate(facts, 1):
                    end_str = f.valid_to.strftime("%Y-%m-%d") if f.valid_to else "present (ongoing)"
                    status_lbl = "active" if f.is_current else "superseded"
                    transition_lines.append(f"{idx}. {f.object} (Valid: {f.valid_from.strftime('%Y-%m-%d')} to {end_str}) [{status_lbl}]")

                history_text = "\n".join(transition_lines)
                pred_label = (predicate or "attribute").replace("_", " ")
                answer = f"Chronological history of {possessive} {pred_label}:\n{history_text}"

                supporting_fact_ids = [f.id for f in facts]
                source_ep_ids = list({f.source_episode_id for f in facts if f.source_episode_id})

                reasoning_chain.append(f"3. Retrieved {len(facts)} historical transition events.")
                latency = (time.perf_counter() - start_t) * 1000

                return ChatResponse(
                    query=query_text,
                    answer=answer,
                    grounded=True,
                    evidence_status="verified_historical",
                    supporting_fact_ids=supporting_fact_ids,
                    source_episode_ids=source_ep_ids,
                    temporal_validity={
                        "history_span_start": valid_span_start,
                        "events_count": len(facts),
                        "transitions_count": max(0, len(facts) - 1)
                    },
                    retrieval_method="temporal_timeline",
                    confidence=0.98,
                    supporting_facts=facts,
                    supporting_episodes=[],
                    reasoning_chain=reasoning_chain,
                    latency_ms=round(latency, 2)
                )

        # =========================================================================
        # CASE 2: PREVIOUS STATE QUERY ("What framework did I use before?", "Where did I live previously?")
        # CRITICAL RULE: Never answer a historical question using only the latest fact!
        # =========================================================================
        elif mode == "PREVIOUS":
            reasoning_chain.append("2. Query explicitly requests prior/superseded state. Guarding against latest fact.")
            all_facts = []
            for cand_pred in self._get_candidate_predicates(predicate):
                all_facts = graph_store.get_facts(as_of=None, subject=subject, predicate=cand_pred, limit=50)
                if all_facts:
                    predicate = cand_pred
                    break

            # Separate active fact vs superseded historical facts
            superseded_facts = [f for f in all_facts if not f.is_current or f.status == "superseded" or f.valid_to is not None]
            active_facts = [f for f in all_facts if f.is_current and f.status == "active"]

            # Sort superseded facts by valid_to descending (most recently superseded first)
            superseded_facts.sort(key=lambda x: x.valid_to or x.valid_from, reverse=True)

            if superseded_facts:
                prior_fact = superseded_facts[0]
                valid_from_str = prior_fact.valid_from.strftime("%Y-%m-%d")
                valid_to_str = prior_fact.valid_to.strftime("%Y-%m-%d") if prior_fact.valid_to else "transition"

                current_context = ""
                if active_facts:
                    current_context = f" (This was superseded by your current {predicate.replace('_', ' ')}, {active_facts[0].object})."

                pred_label = (predicate or "attribute").replace("_", " ")
                if predicate in ("backend_framework", "backend"):
                    answer = f"Previously (from {valid_from_str} to {valid_to_str}), {subj_display.lower() if is_user else subj_display} used {prior_fact.object}{current_context}"
                elif predicate == "frontend_framework":
                    answer = f"Previously (from {valid_from_str} to {valid_to_str}), {subj_display.lower() if is_user else subj_display} used {prior_fact.object}{current_context}"
                elif predicate == "lives_in":
                    answer = f"Previously (from {valid_from_str} to {valid_to_str}), {subj_display.lower() if is_user else subj_display} lived in {prior_fact.object}{current_context}"
                elif predicate == "works_at":
                    answer = f"Previously (from {valid_from_str} to {valid_to_str}), {subj_display.lower() if is_user else subj_display} worked at {prior_fact.object}{current_context}"
                elif predicate in ("database_used", "database"):
                    answer = f"Previously (from {valid_from_str} to {valid_to_str}), {subj_display.lower() if is_user else subj_display} used {prior_fact.object}{current_context} as database"
                else:
                    answer = f"Previously (from {valid_from_str} to {valid_to_str}), {possessive} {pred_label} was {prior_fact.object}{current_context}"

                reasoning_chain.append(
                    f"3. Retrieved superseded historical fact ({prior_fact.subject} -> {prior_fact.predicate} -> {prior_fact.object}) "
                    f"valid {valid_from_str} to {valid_to_str}."
                )

                latency = (time.perf_counter() - start_t) * 1000
                return ChatResponse(
                    query=query_text,
                    answer=answer,
                    grounded=True,
                    evidence_status="verified_historical",
                    supporting_fact_ids=[prior_fact.id],
                    source_episode_ids=[prior_fact.source_episode_id] if prior_fact.source_episode_id else [],
                    temporal_validity={
                        "valid_from": prior_fact.valid_from.isoformat(),
                        "valid_to": prior_fact.valid_to.isoformat() if prior_fact.valid_to else None,
                        "is_current": False,
                        "status": "superseded"
                    },
                    retrieval_method="temporal_graph_historical",
                    confidence=prior_fact.confidence,
                    supporting_facts=[prior_fact],
                    supporting_episodes=[],
                    reasoning_chain=reasoning_chain,
                    latency_ms=round(latency, 2)
                )
            elif active_facts:
                # Active fact exists, but NO previous fact was ever recorded
                act = active_facts[0]
                pred_label = (predicate or "attribute").replace("_", " ")
                answer = (
                    f"Memory records only show {possessive.lower() if is_user else possessive} current {pred_label} "
                    f"({act.object}, active since {act.valid_from.strftime('%Y-%m-%d')}). "
                    f"No prior historical {pred_label} is recorded before this."
                )
                reasoning_chain.append("3. Only active fact present; correctly refused to answer historical query with current fact.")
                latency = (time.perf_counter() - start_t) * 1000

                return ChatResponse(
                    query=query_text,
                    answer=answer,
                    grounded=True,
                    evidence_status="verified_historical_none",
                    supporting_fact_ids=[act.id],
                    source_episode_ids=[act.source_episode_id] if act.source_episode_id else [],
                    temporal_validity={
                        "earliest_known_valid_from": act.valid_from.isoformat(),
                        "has_prior_superseded": False
                    },
                    retrieval_method="temporal_graph_historical_empty",
                    confidence=0.95,
                    supporting_facts=[act],
                    supporting_episodes=[],
                    reasoning_chain=reasoning_chain,
                    latency_ms=round(latency, 2)
                )

        # =========================================================================
        # CASE 3: POINT-IN-TIME QUERY ("Where did Alice live in 2021?", "What framework did I use in 2022?")
        # =========================================================================
        elif mode == "POINT_IN_TIME" and parsed_date is not None:
            reasoning_chain.append(f"2. Point-in-time evaluation target: {parsed_date.strftime('%Y-%m-%d')}.")
            facts = []
            for cand_pred in self._get_candidate_predicates(predicate):
                facts = graph_store.get_facts(as_of=parsed_date, subject=subject, predicate=cand_pred, limit=10)
                if facts:
                    predicate = cand_pred
                    break

            if facts:
                fact = facts[0]
                valid_from_str = fact.valid_from.strftime("%Y-%m-%d")
                valid_to_str = fact.valid_to.strftime("%Y-%m-%d") if fact.valid_to else "present"
                date_label = parsed_date.strftime("%Y-%m-%d") if date_source == "date_parsed" else str(parsed_date.year)

                if predicate == "lives_in":
                    answer = f"As of {date_label}, {subj_display.lower() if is_user else subj_display} lived in {fact.object} (valid from {valid_from_str} to {valid_to_str})."
                elif predicate in ("backend_framework", "backend"):
                    answer = f"As of {date_label}, {possessive} backend framework was {fact.object} (valid from {valid_from_str} to {valid_to_str})."
                elif predicate == "frontend_framework":
                    answer = f"As of {date_label}, {possessive} frontend framework was {fact.object} (valid from {valid_from_str} to {valid_to_str})."
                elif predicate == "works_at":
                    answer = f"As of {date_label}, {subj_display.lower() if is_user else subj_display} worked at {fact.object} (valid from {valid_from_str} to {valid_to_str})."
                elif predicate in ("database_used", "database"):
                    answer = f"As of {date_label}, {subj_display.lower() if is_user else subj_display} used {fact.object} as database (valid from {valid_from_str} to {valid_to_str})."
                else:
                    pred_clean = (fact.predicate).replace("_", " ")
                    answer = f"As of {date_label}, {fact.subject} {pred_clean} {fact.object} (valid from {valid_from_str} to {valid_to_str})."

                reasoning_chain.append(f"3. Found time-valid fact ({fact.subject} -> {fact.predicate} -> {fact.object}) bounding target date.")
                latency = (time.perf_counter() - start_t) * 1000

                return ChatResponse(
                    query=query_text,
                    answer=answer,
                    grounded=True,
                    evidence_status="verified_point_in_time",
                    supporting_fact_ids=[fact.id],
                    source_episode_ids=[fact.source_episode_id] if fact.source_episode_id else [],
                    temporal_validity={
                        "as_of": parsed_date.isoformat(),
                        "valid_from": fact.valid_from.isoformat(),
                        "valid_to": fact.valid_to.isoformat() if fact.valid_to else None,
                        "is_current": fact.is_current
                    },
                    retrieval_method="temporal_graph_point_in_time",
                    confidence=fact.confidence,
                    supporting_facts=[fact],
                    supporting_episodes=[],
                    reasoning_chain=reasoning_chain,
                    latency_ms=round(latency, 2)
                )
            else:
                date_label = str(parsed_date.year) if date_source == "year_parsed" else parsed_date.strftime("%Y-%m-%d")
                pred_label = (predicate or "requested attribute").replace("_", " ")
                answer = f"No verified memory records were active as of {date_label} for {possessive.lower() if is_user else possessive} {pred_label}."
                reasoning_chain.append("3. No temporal graph fact intersected target date.")
                latency = (time.perf_counter() - start_t) * 1000

                return ChatResponse(
                    query=query_text,
                    answer=answer,
                    grounded=False,
                    evidence_status="ungrounded",
                    supporting_fact_ids=[],
                    source_episode_ids=[],
                    temporal_validity={"as_of": parsed_date.isoformat(), "status": "no_active_interval"},
                    retrieval_method="temporal_graph_point_in_time",
                    confidence=0.0,
                    supporting_facts=[],
                    supporting_episodes=[],
                    reasoning_chain=reasoning_chain,
                    latency_ms=round(latency, 2)
                )

        # =========================================================================
        # CASE 4: CURRENT STATE QUERY ("What framework do I use now?", "Where do I live now?")
        # =========================================================================
        # Query active current facts
        active_facts = []
        for cand_pred in self._get_candidate_predicates(predicate):
            active_facts = graph_store.get_facts(
                as_of=None,
                subject=subject,
                predicate=cand_pred,
                only_current=True,
                status="active",
                limit=10
            )
            if active_facts:
                predicate = cand_pred
                break

        if active_facts:
            if len(active_facts) > 1:
                objects_str = ", ".join(f.object for f in active_facts[:-1]) + f" and {active_facts[-1].object}"
                pred_label = active_facts[0].predicate.replace('_', ' ')
                if active_facts[0].predicate in ("uses_language", "uses_hardware", "uses_tool"):
                    answer = f"{subj_display} currently use{'s' if not is_user else ''} {objects_str}."
                else:
                    answer = f"{subj_display} currently {pred_label} {objects_str}."

                reasoning_chain.append(f"2. Retrieved {len(active_facts)} current active facts: {objects_str}.")
                latency = (time.perf_counter() - start_t) * 1000

                return ChatResponse(
                    query=query_text,
                    answer=answer,
                    grounded=True,
                    evidence_status="verified_active",
                    supporting_fact_ids=[f.id for f in active_facts],
                    source_episode_ids=[f.source_episode_id for f in active_facts if f.source_episode_id],
                    temporal_validity={
                        "valid_from": active_facts[0].valid_from.isoformat(),
                        "valid_to": None,
                        "is_current": True,
                        "status": "active"
                    },
                    retrieval_method="temporal_graph_active",
                    confidence=active_facts[0].confidence,
                    supporting_facts=active_facts,
                    supporting_episodes=[],
                    reasoning_chain=reasoning_chain,
                    latency_ms=round(latency, 2)
                )

            act = active_facts[0]
            valid_from_str = act.valid_from.strftime("%Y-%m-%d")

            # Check if there is a superseded fact for historical contrast
            history = graph_store.get_fact_history(subject=act.subject, predicate=act.predicate)
            prior = [f for f in history if f.id != act.id and f.valid_to]
            contrast_str = f" (Previously: {prior[-1].object})" if prior else ""

            if act.predicate in ("backend_framework", "backend"):
                answer = f"{possessive} current backend framework is {act.object}{contrast_str} (active since {valid_from_str})."
            elif act.predicate == "frontend_framework":
                answer = f"{possessive} current frontend framework is {act.object}{contrast_str} (active since {valid_from_str})."
            elif act.predicate == "lives_in":
                answer = f"{subj_display} currently live{'s' if not is_user else ''} in {act.object}{contrast_str} (since {valid_from_str})."
            elif act.predicate == "works_at":
                answer = f"{subj_display} currently work{'s' if not is_user else ''} at {act.object}{contrast_str} (since {valid_from_str})."
            elif act.predicate in ("database_used", "database"):
                answer = f"{subj_display} currently use{'s' if not is_user else ''} {act.object}{contrast_str} as database."
            elif act.predicate == "cloud_provider":
                answer = f"{possessive} current cloud provider is {act.object}{contrast_str}."
            elif act.predicate == "role_title":
                answer = f"{subj_display} currently hold{'s' if not is_user else ''} the role of {act.object}."
            elif act.predicate in ("uses_hardware", "uses_tool", "uses_language"):
                answer = f"{subj_display} currently use{'s' if not is_user else ''} {act.object}."
            else:
                answer = f"{act.subject} currently {act.predicate.replace('_', ' ')} {act.object} (active since {valid_from_str})."

            reasoning_chain.append(f"2. Retrieved current active fact: ({act.subject} -> {act.predicate} -> {act.object}).")
            latency = (time.perf_counter() - start_t) * 1000

            return ChatResponse(
                query=query_text,
                answer=answer,
                grounded=True,
                evidence_status="verified_active",
                supporting_fact_ids=[act.id],
                source_episode_ids=[act.source_episode_id] if act.source_episode_id else [],
                temporal_validity={
                    "valid_from": act.valid_from.isoformat(),
                    "valid_to": None,
                    "is_current": True,
                    "status": "active"
                },
                retrieval_method="temporal_graph_active",
                confidence=act.confidence,
                supporting_facts=[act],
                supporting_episodes=[],
                reasoning_chain=reasoning_chain,
                latency_ms=round(latency, 2)
            )

        # =========================================================================
        # CASE 5: SEMANTIC EPISODE RETRIEVAL (Fallback when graph query alone is insufficient)
        # =========================================================================
        reasoning_chain.append("2. Direct temporal graph lookup found no active facts. Falling back to semantic episode retrieval.")
        ret_result = retrieval_service.retrieve(RetrievalQuery(
            query=query_text,
            session_id=req.session_id,
            top_k=3,
            include_episodes=True
        ))

        if ret_result.matched_facts:
            top_f = ret_result.matched_facts[0]
            answer = f"Based on memory records, {top_f.subject} {top_f.predicate.replace('_', ' ')} {top_f.object}."
            reasoning_chain.append(f"3. Semantic fact match found: ({top_f.subject} -> {top_f.predicate} -> {top_f.object}).")
            latency = (time.perf_counter() - start_t) * 1000

            return ChatResponse(
                query=query_text,
                answer=answer,
                grounded=True,
                evidence_status="verified_graph_semantic",
                supporting_fact_ids=[top_f.id],
                source_episode_ids=[top_f.source_episode_id] if top_f.source_episode_id else [],
                temporal_validity={
                    "valid_from": top_f.valid_from.isoformat(),
                    "valid_to": top_f.valid_to.isoformat() if top_f.valid_to else None,
                    "is_current": top_f.is_current
                },
                retrieval_method="semantic_graph_retrieval",
                confidence=top_f.confidence,
                supporting_facts=[top_f],
                supporting_episodes=ret_result.matched_episodes,
                reasoning_chain=reasoning_chain,
                latency_ms=round(latency, 2)
            )

        if ret_result.matched_episodes:
            top_ep = ret_result.matched_episodes[0]
            ep_date = top_ep.timestamp.strftime("%Y-%m-%d")
            answer = f"Based on conversation episode from {ep_date}: \"{top_ep.text}\""
            reasoning_chain.append(f"3. Retrieved grounded episode {top_ep.id} via semantic vector similarity.")
            latency = (time.perf_counter() - start_t) * 1000

            return ChatResponse(
                query=query_text,
                answer=answer,
                grounded=True,
                evidence_status="semantic_episode",
                supporting_fact_ids=[],
                source_episode_ids=[top_ep.id],
                temporal_validity={"episode_timestamp": top_ep.timestamp.isoformat()},
                retrieval_method="semantic_episode_retrieval",
                confidence=0.82,
                supporting_facts=[],
                supporting_episodes=[top_ep],
                reasoning_chain=reasoning_chain,
                latency_ms=round(latency, 2)
            )

        # =========================================================================
        # CASE 6: UNGROUNDED / UNMATCHED QUERY
        # MANDATORY RULE: Never claim an answer is grounded unless supporting records were retrieved!
        # =========================================================================
        reasoning_chain.append("3. No matching facts or relevant conversation episodes found in memory.")
        latency = (time.perf_counter() - start_t) * 1000

        return ChatResponse(
            query=query_text,
            answer="I do not have verified memory records in the temporal knowledge graph or conversation history to answer this question.",
            grounded=False,
            evidence_status="ungrounded",
            supporting_fact_ids=[],
            source_episode_ids=[],
            temporal_validity={},
            retrieval_method="unmatched",
            confidence=0.0,
            supporting_facts=[],
            supporting_episodes=[],
            reasoning_chain=reasoning_chain,
            latency_ms=round(latency, 2)
        )

    def get_memory_facts(
        self,
        as_of: Optional[datetime] = None,
        subject: Optional[str] = None,
        predicate: Optional[str] = None,
        only_current: Optional[bool] = None,
        limit: int = 100
    ) -> List[Fact]:
        """Provides filtered memory facts query"""
        return graph_store.get_facts(
            as_of=as_of,
            subject=subject,
            predicate=predicate,
            only_current=only_current,
            limit=limit
        )

    def get_memory_history(
        self,
        subject: Optional[str] = None,
        predicate: Optional[str] = None,
        limit: int = 100
    ) -> MemoryHistoryResponse:
        """Provides full temporal evolution/history of memory facts"""
        facts = graph_store.get_fact_history(subject=subject, predicate=predicate, limit=limit)
        items = [
            MemoryHistoryItem(
                fact_id=f.id,
                subject=f.subject,
                predicate=f.predicate,
                object=f.object,
                valid_from=f.valid_from,
                valid_to=f.valid_to,
                status=f.status,
                is_current=f.is_current,
                source_episode_id=f.source_episode_id,
                superseded_by=f.superseded_by,
                confidence=f.confidence,
                created_at=f.created_at,
                extraction_method=f.extraction_method
            )
            for f in facts
        ]
        return MemoryHistoryResponse(
            subject=subject,
            predicate=predicate,
            total_events=len(items),
            transitions_count=max(0, len(items) - 1),
            timeline=items
        )

chat_service = ChatService()
