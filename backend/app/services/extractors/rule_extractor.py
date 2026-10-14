import re
import time
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple

from app.models.fact import Fact
from app.services.extractors.base import BaseExtractor, ExtractionResult

logger = logging.getLogger("chronos.extractors.rule")

class ExtractionRule:
    def __init__(
        self,
        name: str,
        pattern: str,
        predicate: str,
        default_subject: str = "User",
        subject_group: Optional[str] = "sub",
        object_group: str = "obj",
        confidence: float = 0.98,
        is_negation: bool = False
    ):
        self.name = name
        self.pattern = re.compile(pattern, re.IGNORECASE)
        self.predicate = predicate
        self.default_subject = default_subject
        self.subject_group = subject_group
        self.object_group = object_group
        self.confidence = confidence
        self.is_negation = is_negation

    def match(self, text: str, episode_time: datetime, default_speaker: str = "User") -> Optional[Dict[str, Any]]:
        m = self.pattern.search(text)
        if not m:
            return None
        
        data = m.groupdict()
        sub = self.default_subject
        if self.subject_group and self.subject_group in data and data[self.subject_group]:
            raw_sub = data[self.subject_group].strip()
            if raw_sub.lower() in ["i", "my", "we", "our", "myself"]:
                sub = default_speaker
            else:
                sub = raw_sub

        obj = data.get(self.object_group, "").strip()
        if not obj:
            return None

        # Clean punctuation
        sub = sub.strip(".,;:?!'\" ")
        obj = obj.strip(".,;:?!'\" ")

        # Temporal anchor parsing
        valid_from = episode_time
        year_val = data.get("year")
        if year_val:
            try:
                valid_from = datetime(int(year_val), 1, 1, tzinfo=timezone.utc)
            except Exception:
                pass
        
        # Relative temporal markers
        lower_text = text.lower()
        if "yesterday" in lower_text:
            valid_from = datetime.fromtimestamp(episode_time.timestamp() - 86400, tz=timezone.utc)
        elif "last year" in lower_text:
            valid_from = datetime(episode_time.year - 1, 1, 1, tzinfo=timezone.utc)
        elif "since " in lower_text:
            since_m = re.search(r"since\s+(\d{4})", lower_text)
            if since_m:
                valid_from = datetime(int(since_m.group(1)), 1, 1, tzinfo=timezone.utc)

        return {
            "subject": sub,
            "predicate": self.predicate,
            "object": obj,
            "valid_from": valid_from,
            "confidence": self.confidence,
            "rule_name": self.name,
            "is_negation": self.is_negation
        }

class RuleBasedExtractor(BaseExtractor):
    """
    Deterministic rule-based extractor executing lexical/regex patterns.
    Operates at 0 LLM tokens, 0.00 USD, and sub-millisecond latency.
    """

    def __init__(self):
        self.rules: List[ExtractionRule] = [
            # 1. Backend Framework & Technology Stack
            ExtractionRule(
                "backend_switch",
                r"\b(?:i\s+)?switched\s+(?:(?:my\s+)?(?:backend|frontend)?(?:\s+framework)?\s+)?to\s+(?P<obj>FastAPI|Flask|Django|Express|Next\.js|React|Vue|Svelte|Kotlin|Java|Go|[A-Za-z0-9_\-\.\+]+)(?:[\.\,\;]|$)",
                "backend_framework",
                default_subject="User"
            ),
            ExtractionRule(
                "backend_is",
                r"\b(?:my\s+)?(?:backend|frontend)?(?:\s+framework)?\s+is\s+(?P<obj>[A-Za-z0-9_\-\.\+]+)(?:[\.\,\;]|$)",
                "backend_framework",
                default_subject="User"
            ),
            ExtractionRule(
                "backend_use",
                r"\bi\s+(?:now\s+)?use\s+(?P<obj>[A-Za-z0-9_\-\.\+]+)\s+(?:as|for)\s+(?:my\s+)?backend(?:[\.\,\;]|$)",
                "backend_framework",
                default_subject="User"
            ),
            ExtractionRule(
                "backend_correction",
                r"\b(?:actually|correction\s*:)\s*,?\s*(?:my\s+)?backend(?:\s+framework)?\s+is\s+(?P<obj>[A-Za-z0-9_\-\.\+]+)(?:[\.\,\;]|$)",
                "backend_framework",
                default_subject="User",
                confidence=1.0
            ),
            ExtractionRule(
                "backend_informal",
                r"\b(?:i\s+think\s+)?(?:we|i)\s+use\s+(?P<obj>Flask|FastAPI|Django|Express|Next\.js|React|Vue)\s+for\s+now\b",
                "backend_framework",
                default_subject="User",
                confidence=0.75
            ),

            # 2. Database Stack
            ExtractionRule(
                "db_now_use",
                r"\bi\s+now\s+use\s+(?P<obj>[A-Za-z0-9_\-\.\s]+?)(?:[\.\,\;]|$)",
                "database_used",
                default_subject="User"
            ),
            ExtractionRule(
                "db_switched",
                r"\b(?:i\s+)?switched\s+(?:my\s+)?database\s+to\s+(?P<obj>[A-Za-z0-9_\-\.\s]+?)(?:[\.\,\;]|$)",
                "database_used",
                default_subject="User"
            ),
            ExtractionRule(
                "db_is",
                r"\b(?:my\s+)?database\s+is\s+(?P<obj>[A-Za-z0-9_\-\.\s]+?)(?:[\.\,\;]|$)",
                "database_used",
                default_subject="User"
            ),

            # 3. Relocation / Living (Reported & Third Person FIRST, then First Person)
            ExtractionRule(
                "reported_residence",
                r"\b(?P<sub>[A-Z][a-zA-Z]+)\s+told\s+[A-Za-z]+\s+that\s+(?:he|she)\s+(?:now\s+)?lives\s+in\s+(?P<obj>[A-Z][a-zA-Z\s]+?)(?:[\.\,\;]|$)",
                "lives_in"
            ),
            ExtractionRule(
                "relocation_third_person_moved",
                r"\b(?P<sub>[A-Z][a-zA-Z]+)\s+moved\s+to\s+(?P<obj>[A-Z][a-zA-Z\s]+?)(?:\s+in\s+(?P<year>\d{4}))?(?:[\.\,\;]|$)",
                "lives_in"
            ),
            ExtractionRule(
                "relocation_third_person_lives",
                r"\b(?P<sub>[A-Z][a-zA-Z]+)\s+(?:now\s+)?lives\s+in\s+(?P<obj>[A-Z][a-zA-Z\s]+?)(?:\s+since\s+(?P<year>\d{4}))?(?:[\.\,\;]|$)",
                "lives_in"
            ),
            ExtractionRule(
                "relocation_third_person_resides",
                r"\b(?P<sub>[A-Z][a-zA-Z]+)\s+resides\s+in\s+(?P<obj>[A-Z][a-zA-Z\s]+?)(?:[\.\,\;]|$)",
                "lives_in"
            ),
            ExtractionRule(
                "relocation_first_person_moved",
                r"\b(?:i\s+)?moved\s+to\s+(?P<obj>[A-Z][a-zA-Z\s]+?)(?:\s+in\s+(?P<year>\d{4}))?(?:[\.\,\;]|$)",
                "lives_in",
                default_subject="User"
            ),
            ExtractionRule(
                "relocation_first_person_live",
                r"\b(?:i\s+)?(?:now\s+)?live\s+in\s+(?P<obj>[A-Z][a-zA-Z\s]+?)(?:\s+since\s+(?P<year>\d{4}))?(?:[\.\,\;]|$)",
                "lives_in",
                default_subject="User"
            ),
            ExtractionRule(
                "relocation_visiting",
                r"\b(?:temporarily\s+staying|visiting)\s+in\s+(?P<obj>[A-Z][a-zA-Z\s]+?)(?:[\.\,\;]|$)",
                "lives_in",
                default_subject="User",
                confidence=0.65
            ),

            # 4. Employment / Job (Third Person FIRST, then First Person)
            ExtractionRule(
                "job_third_person_joined",
                r"\b(?P<sub>[A-Z][a-zA-Z]+)\s+joined\s+(?P<obj>[A-Z][a-zA-Z0-9]+)(?:\s+as\s+(?:a\s+|an\s+)?[A-Za-z\s]+)?(?:\s+in\s+(?P<year>\d{4}))?(?:[\.\,\;]|$)",
                "works_at"
            ),
            ExtractionRule(
                "job_third_person_works",
                r"\b(?P<sub>[A-Z][a-zA-Z]+)\s+(?:now\s+)?works\s+at\s+(?P<obj>[A-Z][a-zA-Z0-9\s]+?)(?:\s+since\s+(?P<year>\d{4}))?(?:[\.\,\;]|$)",
                "works_at"
            ),
            ExtractionRule(
                "job_first_person_joined",
                r"\b(?:i\s+)?joined\s+(?P<obj>[A-Z][a-zA-Z0-9]+)(?:\s+as\s+(?:a\s+|an\s+)?[A-Za-z\s]+)?(?:\s+in\s+(?P<year>\d{4}))?(?:[\.\,\;]|$)",
                "works_at",
                default_subject="User"
            ),
            ExtractionRule(
                "job_first_person_work",
                r"\bi\s+(?:now\s+)?work\s+at\s+(?P<obj>[A-Za-z0-9\s]+?)(?:\s+since\s+(?P<year>\d{4}))?(?:[\.\,\;]|$)",
                "works_at",
                default_subject="User"
            ),
            ExtractionRule(
                "job_contracting",
                r"\b(?:contracting|consulting)\s+(?:at|for)\s+(?P<obj>[A-Z][a-zA-Z0-9]+)(?:[\.\,\;]|$)",
                "works_at",
                default_subject="User",
                confidence=0.85
            ),
            ExtractionRule(
                "job_left",
                r"\b(?P<sub>[A-Z][a-zA-Z]+|I)\s+left\s+(?P<obj>[A-Z][a-zA-Z0-9\s]+?)(?:\s+in\s+(?P<year>\d{4}))?(?:[\.\,\;]|$)",
                "works_at",
                is_negation=True
            ),
            ExtractionRule(
                "job_founded",
                r"\b(?P<sub>[A-Z][a-zA-Z]+|I)\s+(?:founded|co-founded)\s+(?P<obj>[A-Z][a-zA-Z0-9]+)",
                "works_at"
            ),

            # 5. Role / Title
            ExtractionRule(
                "role_as_title",
                r"\bas\s+(?:a\s+|an\s+)?(?P<obj>CEO|CTO|VP|Director|Head\s+of\s+[A-Za-z\s]+|Research\s+Scientist|Principal\s+Architect|Senior\s+Engineer|Engineering\s+Manager|researcher)(?:[\.\,\;]|$)",
                "role_title",
                default_subject="User"
            ),
            ExtractionRule(
                "role_became",
                r"\b(?P<sub>[A-Z][a-zA-Z]+|I)\s+became\s+(?:a|an)\s+(?P<obj>[A-Za-z\s]+?)(?:\s+at\s+[A-Za-z0-9]+)?(?:\s+in\s+(?P<year>\d{4}))?(?:[\.\,\;]|$)",
                "role_title"
            ),
            ExtractionRule(
                "role_promoted",
                r"\b(?P<sub>[A-Z][a-zA-Z]+|I)\s+was\s+promoted\s+to\s+(?P<obj>[A-Za-z\s]+?)(?:[\.\,\;]|$)",
                "role_title"
            ),

            # 6. Tools / Hardware / Tech
            ExtractionRule(
                "hardware_upgraded",
                r"\b(?P<sub>[A-Z][a-zA-Z]+|I)\s+upgraded\s+to\s+(?:a\s+|an\s+)?(?P<obj>[A-Za-z0-9\s]+?)(?:[\.\,\;]|$)",
                "uses_hardware"
            ),
            ExtractionRule(
                "tool_prefers",
                r"\b(?P<sub>[A-Z][a-zA-Z]+|I)\s+prefers?\s+(?P<obj>[A-Za-z0-9\s]+?)(?:[\.\,\;]|$)",
                "prefers"
            ),

            # 7. Projects & Relationships
            ExtractionRule(
                "project_leading",
                r"\b(?P<sub>[A-Z][a-zA-Z]+|I)\s+is\s+leading\s+(?:the\s+)?(?P<obj>[A-Za-z0-9\s]+?)(?:\s+project)?(?:[\.\,\;]|$)",
                "leads_project"
            ),
            ExtractionRule(
                "relation_married",
                r"\b(?P<sub>[A-Z][a-zA-Z]+)\s+married\s+(?P<obj>[A-Z][a-zA-Z]+)(?:\s+in\s+(?P<year>\d{4}))?(?:[\.\,\;]|$)",
                "married_to"
            ),
            ExtractionRule(
                "parent_relation",
                r"\b(?P<sub>[A-Z][a-zA-Z]+)(?:\s+and\s+[A-Za-z]+)?\s+had\s+a\s+(?:daughter|son|child)\s+named\s+(?P<obj>[A-Z][a-zA-Z]+)(?:\s+in\s+(?P<year>\d{4}))?",
                "parent_of"
            ),

            # 8. Negations
            ExtractionRule(
                "negation_not_use",
                r"\bi\s+(?:do\s+not|don't)\s+use\s+(?P<obj>[A-Za-z0-9_\-\.\+]+)(?:\s+anymore)?(?:[\.\,\;]|$)",
                "backend_framework",
                default_subject="User",
                is_negation=True
            ),
            ExtractionRule(
                "frontend_negation",
                r"\bi\s+(?:do\s+not|don't)\s+use\s+(?P<obj>React|Vue|Svelte|Angular|Next\.js)(?:\s+anymore)?(?:[\.\,\;]|$)",
                "frontend_framework",
                default_subject="User",
                is_negation=True
            ),
            ExtractionRule(
                "frontend_switch",
                r"\b(?:i\s+)?(?:switched\s+(?:my\s+)?frontend(?:\s+framework)?\s+to|use)\s+(?P<obj>[A-Za-z0-9_\-\.\+]+)\s+for\s+(?:all\s+my\s+)?frontend",
                "frontend_framework",
                default_subject="User"
            ),
            ExtractionRule(
                "frontend_is",
                r"\b(?:our\s+web\s+application\s+)?frontend\s+(?:stack\s+)?is\s+(?:built\s+with\s+)?(?P<obj>[A-Za-z0-9_\-\.\+]+)(?:[\.\,\;]|$)",
                "frontend_framework",
                default_subject="User"
            ),
            ExtractionRule(
                "frontend_transition",
                r"\btransitioned\s+our\s+frontend\s+stack\s+to\s+(?P<obj>[A-Za-z0-9_\-\.\+]+)",
                "frontend_framework",
                default_subject="User"
            ),
            ExtractionRule(
                "project_status_deprecated",
                r"\b(?P<sub>Project\s+[A-Z][a-zA-Z0-9]+)\s+has\s+been\s+(?:officially\s+)?(?:sunsetted\s+and\s+)?(?P<obj>deprecated|sunsetted)",
                "status"
            ),


            # 9. Cloud Provider & Infrastructure
            ExtractionRule(
                "cloud_provider_switch",
                r"\bmoved\s+all\s+infrastructure\s+from\s+[A-Za-z0-9\s]+\s+to\s+(?P<obj>Google Cloud|AWS|Azure|GCP|Cloudflare)(?:[\.\,\;]|$)",
                "cloud_provider",
                default_subject="User"
            ),
            ExtractionRule(
                "cloud_provider_run",
                r"\ball\s+our\s+microservices\s+run\s+on\s+(?P<obj>Google Cloud|AWS|Azure|GCP)(?:[\.\,\;]|$)",
                "cloud_provider",
                default_subject="User"
            ),

            # 10. Database Stack Explicit
            ExtractionRule(
                "db_store_core",
                r"\bstore\s+our\s+core\s+application\s+data\s+in\s+(?P<obj>[A-Za-z0-9_\-]+)(?:[\.\,\;]|$)",
                "database",
                default_subject="User"
            ),
            ExtractionRule(
                "db_migrated_to",
                r"\bmigrated\s+our\s+database\s+from\s+[A-Za-z0-9_\-]+\s+to\s+(?P<obj>[A-Za-z0-9_\-]+)",
                "database",
                default_subject="User"
            ),

            # 11. Programming Languages & Tools
            ExtractionRule(
                "lang_switch_primary",
                r"\bswitched\s+my\s+primary\s+(?:[A-Za-z]+\s+)?language\s+to\s+(?P<obj>[A-Za-z0-9\+\#]+)(?:[\.\,\;]|$)",
                "primary_language",
                default_subject="User"
            ),
            ExtractionRule(
                "lang_write_in",
                r"\bwrite\s+my\s+(?:[A-Za-z]+\s+)?applications\s+in\s+(?P<obj>[A-Za-z0-9\+\#]+)(?:[\.\,\;]|$)",
                "primary_language",
                default_subject="User"
            ),
            ExtractionRule(
                "lang_code_daily",
                r"\bcode\s+daily\s+in\s+(?P<obj>[A-Za-z0-9\+\#]+)(?:[\.\,\;]|$)",
                "uses_language",
                default_subject="User"
            ),
            ExtractionRule(
                "lang_writing_for",
                r"\bwriting\s+(?P<obj>[A-Za-z0-9\+\#]+)\s+for\s+systems\s+tools(?:[\.\,\;]|$)",
                "uses_language",
                default_subject="User"
            ),
            ExtractionRule(
                "tool_uses_for",
                r"\buse\s+(?P<obj>Docker|Terraform|Kubernetes|Ansible)\s+for\s+(?:containerization|managing)",
                "uses_tool",
                default_subject="User"
            ),
            ExtractionRule(
                "repo_maintainer",
                r"\b(?:contribute\s+to\s+the|maintainer\s+of\s+the)\s+(?P<obj>[A-Za-z0-9_\-]+)\s+repository(?:[\.\,\;]|$)",
                "maintains_repo",
                default_subject="User"
            ),

            # 12. Office Locations
            ExtractionRule(
                "office_works_at",
                r"\b(?P<sub>[A-Z][a-zA-Z]+)\s+works\s+at\s+the\s+(?P<obj>[A-Za-z\s]+?)\s+office(?:[\.\,\;]|$)",
                "office_location"
            ),
            ExtractionRule(
                "office_transferred",
                r"\b(?P<sub>[A-Z][a-zA-Z]+)\s+transferred\s+to\s+the\s+(?P<obj>[A-Za-z\s]+?)\s+office(?:[\.\,\;]|$)",
                "office_location"
            )
        ]

    def _split_into_clauses(self, text: str) -> List[Tuple[str, bool]]:
        """
        Splits conversational utterance into sequential clauses and detects
        whether a clause represents an intra-utterance correction or retraction.
        Returns: List of (clause_text, is_correction_or_retraction_marker)
        """
        s = text.strip()
        # 1. Delimiters that mark corrections or distinct clauses
        s = re.sub(r'\.\s+(?=[A-Z])', ' || ', s)
        s = re.sub(r'[\r\n;]+|[—–]|--|,?\s*(?:wait\s+actually|wait\s+no|wait\s+i\s+mean|scratch\s+that|never\s+mind|actually)\s*,?', ' ||_CORR_|| ', s, flags=re.IGNORECASE)
        s = re.sub(r',?\s*but\s+', ' ||_CORR_|| ', s, flags=re.IGNORECASE)
        s = re.sub(r',?\s+and\s+(?=(?:I\s+|we\s+|he\s+|she\s+|joined\s+|switched\s+|moved\s+|lives?\s+|works?\s+|code\s+))', ' || ', s, flags=re.IGNORECASE)
        s = re.sub(r',\s+(?=(?:I\s+use|I\s+code|I\s+live|I\s+work|I\s+moved|I\s+switched))', ' || ', s, flags=re.IGNORECASE)

        raw_parts = s.split('||')
        clauses: List[Tuple[str, bool]] = []
        is_next_corr = False

        for part in raw_parts:
            part = part.strip()
            if not part:
                continue
            if part == '_CORR_':
                is_next_corr = True
                continue
            if part.startswith('_CORR_ '):
                is_next_corr = True
                part = part[7:].strip()
            
            p_clean = part.strip(' ,.')
            if p_clean:
                clauses.append((p_clean, is_next_corr))
                is_next_corr = False

        if not clauses:
            clauses = [(text.strip(), False)]
        return clauses

    async def extract(
        self,
        text: str,
        episode_time: datetime,
        default_speaker: str = "User"
    ) -> ExtractionResult:
        start_t = time.perf_counter()

        # 1. Guard against ambiguous retractions / self-corrections (e.g. "wait actually maybe not", "wait who knows")
        ambiguous_correction_pattern = re.compile(
            r"\b(?:wait\s+actually\s+maybe\s+not|wait\s+maybe\s+not|wait\s+actually\s+who\s+knows|wait\s+maybe|maybe\s+not|who\s+knows|not\s+sure)\b",
            re.IGNORECASE
        )
        if ambiguous_correction_pattern.search(text):
            latency_ms = (time.perf_counter() - start_t) * 1000
            return ExtractionResult(
                facts=[],
                confidence=0.0,
                extraction_method="rule",
                latency_ms=round(latency_ms, 3),
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                tokens_is_measured=True,
                estimated_cost_usd=0.0,
                cost_pricing_basis="Zero-token deterministic rule engine ($0.00)",
                decision_reason="Ambiguous intra-utterance retraction/correction detected; safely refusing to commit guessed facts",
                fallback_triggered=False
            )

        from app.services.contradiction_service import FUNCTIONAL_PREDICATES

        # 2. Extract facts clause-by-clause
        clauses = self._split_into_clauses(text)
        candidate_facts: List[Fact] = []
        last_named_subject = None
        matched_rule_names = []
        highest_confidence = 0.0

        for clause_text, is_corr in clauses:
            for rule in self.rules:
                res = rule.match(clause_text, episode_time, default_speaker=default_speaker)
                if res:
                    sub = res["subject"]
                    # Anaphora / Pronoun Coreference Resolution
                    if sub.lower() in ["he", "she", "they"] and last_named_subject:
                        sub = last_named_subject
                    elif sub[0].isupper() and sub.lower() not in ["he", "she", "they", "it", "user"]:
                        last_named_subject = sub

                    is_neg = bool(res.get("is_negation"))
                    fact = Fact(
                        subject=sub,
                        predicate=res["predicate"],
                        object=res["object"],
                        valid_from=res["valid_from"],
                        valid_to=res["valid_from"] if is_neg else None,
                        status="superseded" if is_neg else "active",
                        is_current=False if is_neg else True,
                        confidence=res["confidence"],
                        extraction_method="negation" if is_neg else "rule",
                        source="rule",
                        rule_name=res["rule_name"],
                        tokens_used=0,
                        input_tokens=0,
                        output_tokens=0,
                        tokens_is_measured=True,
                        estimated_cost_usd=0.0,
                        cost_pricing_basis="Zero-token deterministic rule engine ($0.00)",
                        decision_reason=f"Matched deterministic rule '{res['rule_name']}' in clause '{clause_text}' with confidence {res['confidence']:.2f}",
                        raw_text=clause_text
                    )
                    candidate_facts.append(fact)
                    matched_rule_names.append(res["rule_name"])
                    if res["confidence"] > highest_confidence:
                        highest_confidence = res["confidence"]
                    break

        # 3. Intra-Utterance Contradiction & Retraction Resolution
        # Process sequential candidate facts to ensure corrections and retractions override earlier clauses
        final_facts: List[Fact] = []
        retracted_keys = set()

        # Pass A: Identify explicit negations/retractions (e.g. "left Meta", "don't use React")
        for f in candidate_facts:
            if f.extraction_method == "negation":
                retracted_keys.add((f.subject.lower(), f.predicate.lower(), f.object.lower()))

        # Pass B: Filter out retracted facts and resolve functional predicate supersession within utterance
        for f in candidate_facts:
            key = (f.subject.lower(), f.predicate.lower(), f.object.lower())
            
            # If this positive fact was retracted later in the same utterance, do not emit as active
            if f.extraction_method != "negation" and key in retracted_keys:
                logger.info("Intra-utterance retraction: (%s, %s, %s) was retracted in the same sentence.",
                            f.subject, f.predicate, f.object)
                continue

            # If it is a negation fact itself, keep as invalidation marker if needed
            if f.extraction_method == "negation":
                final_facts.append(f)
                continue

            # Check if an earlier candidate fact in the same utterance shares the same subject and functional predicate
            is_functional = f.predicate.lower() in FUNCTIONAL_PREDICATES
            if is_functional:
                # Mark previous active fact on same functional predicate as superseded
                for prev in final_facts:
                    if prev.is_current and prev.subject.lower() == f.subject.lower() and prev.predicate.lower() == f.predicate.lower():
                        prev.is_current = False
                        prev.status = "superseded"
                        prev.valid_to = f.valid_from
                        logger.info("Intra-utterance supersession: (%s, %s, %s) supersedes earlier clause (%s).",
                                    f.subject, f.predicate, f.object, prev.object)

            final_facts.append(f)

        latency_ms = (time.perf_counter() - start_t) * 1000

        if final_facts:
            decision = f"Deterministic rules matched: {', '.join(matched_rule_names)} (confidence: {highest_confidence:.2f})"
        else:
            decision = "No deterministic rule matched conversational text"

        return ExtractionResult(
            facts=final_facts,
            confidence=highest_confidence,
            extraction_method="rule",
            latency_ms=round(latency_ms, 3),
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
            tokens_is_measured=True,
            estimated_cost_usd=0.0,
            cost_pricing_basis="Zero-token deterministic rule engine ($0.00)",
            decision_reason=decision,
            fallback_triggered=False
        )

rule_extractor = RuleBasedExtractor()
