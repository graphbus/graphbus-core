"""
Message and negotiation primitives
"""

from dataclasses import dataclass, field
from typing import Any
import time
import uuid


@dataclass
class Message:
    """
    Direct message from one node to another (Runtime Mode).
    """
    msg_id: str
    src: str
    dst: str
    method: str
    payload: dict[str, Any]
    context: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class Event:
    """
    Pub/sub event (Runtime Mode).
    """
    event_id: str
    topic: str
    src: str
    payload: dict[str, Any]
    timestamp: float = field(default_factory=time.time)


# Build Mode Only - Negotiation Primitives


@dataclass
class CodeChange:
    """
    Details of a proposed code change.
    """
    file_path: str
    target: str  # method name or class name
    change_type: str  # "modify", "add", "delete"
    old_code: str
    new_code: str
    diff: str | None = None  # unified diff format

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "target": self.target,
            "change_type": self.change_type,
            "old_code": self.old_code,
            "new_code": self.new_code,
            "diff": self.diff
        }


@dataclass
class SchemaChange:
    """
    Schema modifications as part of a proposal.
    """
    method: str
    input_schema_before: dict
    input_schema_after: dict
    output_schema_before: dict
    output_schema_after: dict

    def to_dict(self) -> dict:
        return {
            "method": self.method,
            "input_schema_before": self.input_schema_before,
            "input_schema_after": self.input_schema_after,
            "output_schema_before": self.output_schema_before,
            "output_schema_after": self.output_schema_after
        }


@dataclass
class Proposal:
    """
    Proposal for code change (Build Mode only).
    Agents use this to negotiate code refactorings.
    """
    proposal_id: str
    round: int  # which negotiation round
    src: str  # proposing agent
    dst: str | None  # target agent (None = broadcast)
    intent: str  # "align_schema", "add_validation", "refactor_method", etc.

    # Code change details
    code_change: CodeChange
    schema_change: SchemaChange | None = None

    # Negotiation context
    reason: str = ""  # LLM-generated explanation
    dependencies: list[str] = field(default_factory=list)  # other proposals this depends on
    priority: int = 0  # urgency (higher = more important)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "proposal_id": self.proposal_id,
            "round": self.round,
            "src": self.src,
            "dst": self.dst,
            "intent": self.intent,
            "code_change": self.code_change.to_dict(),
            "schema_change": self.schema_change.to_dict() if self.schema_change else None,
            "reason": self.reason,
            "dependencies": self.dependencies,
            "priority": self.priority,
            "timestamp": self.timestamp
        }


@dataclass
class ProposalEvaluation:
    """
    Evaluation of a proposal by another agent (Build Mode only).
    """
    proposal_id: str
    evaluator: str  # evaluating agent
    round: int

    # Decision
    decision: str  # "accept", "reject", "counter", "defer"
    confidence: float = 1.0  # 0.0-1.0, how confident the LLM is

    # LLM reasoning
    reasoning: str = ""  # detailed explanation from LLM
    concerns: list[str] = field(default_factory=list)  # specific issues identified
    suggestions: list[str] = field(default_factory=list)  # improvements even if accepting

    # Counter-proposal (if applicable)
    counter_proposal: "Proposal | None" = None

    # Impact assessment
    impact_assessment: dict = field(default_factory=dict)  # {
                                                            #   "breaks_contracts": bool,
                                                            #   "affects_dependencies": list[str],
                                                            #   "estimated_risk": "low" | "medium" | "high"
                                                            # }
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "proposal_id": self.proposal_id,
            "evaluator": self.evaluator,
            "round": self.round,
            "decision": self.decision,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "concerns": self.concerns,
            "suggestions": self.suggestions,
            "counter_proposal": self.counter_proposal.to_dict() if self.counter_proposal else None,
            "impact_assessment": self.impact_assessment,
            "timestamp": self.timestamp
        }


@dataclass
class CommitRecord:
    """
    Record of an accepted proposal that resulted in code changes (Build Mode only).
    """
    commit_id: str
    proposal_id: str
    round: int

    # Participants
    proposer: str
    evaluators: list[str]
    consensus_type: str = "unanimous"  # "unanimous", "majority", "override"

    # Resolution
    resolution: dict = field(default_factory=dict)  # final agreed code change
    files_modified: list[str] = field(default_factory=list)
    schema_changes: list[SchemaChange] = field(default_factory=list)

    # Metadata
    timestamp: float = field(default_factory=time.time)
    negotiation_log: list[dict] = field(default_factory=list)  # full conversation history

    def to_dict(self) -> dict:
        return {
            "commit_id": self.commit_id,
            "proposal_id": self.proposal_id,
            "round": self.round,
            "proposer": self.proposer,
            "evaluators": self.evaluators,
            "consensus_type": self.consensus_type,
            "resolution": self.resolution,
            "files_modified": self.files_modified,
            "schema_changes": [sc.to_dict() for sc in self.schema_changes],
            "timestamp": self.timestamp,
            "negotiation_log": self.negotiation_log
        }


def generate_id(prefix: str = "") -> str:
    """
    Generate a unique ID for messages, proposals, etc.
    """
    return f"{prefix}{uuid.uuid4().hex[:8]}"
