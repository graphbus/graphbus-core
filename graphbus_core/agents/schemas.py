"""
JSON schemas for structured negotiation outputs

These schemas ensure that all LLM responses are properly structured
and validated before being used in the negotiation process.
"""

# Intent Relevance Check Schema
INTENT_RELEVANCE_SCHEMA = {
    "type": "object",
    "properties": {
        "relevant": {
            "type": "boolean",
            "description": "Whether the intent is relevant to this agent's scope"
        },
        "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Confidence score (0-1) for the relevance decision"
        },
        "reasoning": {
            "type": "string",
            "description": "Brief explanation of why this intent is or isn't relevant"
        }
    },
    "required": ["relevant", "confidence", "reasoning"]
}

# Code Analysis Schema
CODE_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "issues": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of issues or areas for improvement found in the code"
        },
        "potential_improvements": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of specific, actionable improvements that could be made"
        },
        "priority": {
            "type": "string",
            "enum": ["high", "medium", "low"],
            "description": "Priority level for improvements (high, medium, or low)"
        },
        "summary": {
            "type": "string",
            "description": "Brief summary of the code analysis"
        }
    },
    "required": ["issues", "potential_improvements", "priority", "summary"]
}

# Code Suggestions Schema
CODE_SUGGESTIONS_SCHEMA = {
    "type": "object",
    "properties": {
        "suggestions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of specific code improvements to make"
        },
        "implementation_notes": {
            "type": "string",
            "description": "Notes on how to implement the suggestions"
        }
    },
    "required": ["suggestions"]
}

# Proposal Schema
PROPOSAL_SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {
            "type": "string",
            "description": "Brief description of the proposed improvement"
        },
        "old_code": {
            "type": "string",
            "description": "Current code that will be replaced"
        },
        "new_code": {
            "type": "string",
            "description": "Improved code to replace the old code"
        },
        "rationale": {
            "type": "string",
            "description": "Explanation of why this improvement is beneficial"
        },
        "impact": {
            "type": "string",
            "enum": ["low", "medium", "high"],
            "description": "Expected impact level of this change"
        }
    },
    "required": ["intent", "old_code", "new_code", "rationale", "impact"]
}

# Evaluation Schema
EVALUATION_SCHEMA = {
    "type": "object",
    "properties": {
        "decision": {
            "type": "string",
            "enum": ["approve", "reject", "conditional"],
            "description": "Decision on whether to approve or reject the proposal"
        },
        "rationale": {
            "type": "string",
            "description": "Explanation for the decision"
        },
        "conflicts": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Any conflicts or concerns with the proposal"
        },
        "suggestions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Suggestions for improvement if applicable"
        }
    },
    "required": ["decision", "rationale"]
}

# Clarifying Questions Schema
CLARIFYING_QUESTIONS_SCHEMA = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The clarifying question"
                    },
                    "context": {
                        "type": "string",
                        "description": "Optional context for the question"
                    },
                    "options": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional suggested answer options"
                    }
                },
                "required": ["question"]
            },
            "description": "List of clarifying questions for the user"
        }
    },
    "required": ["questions"]
}

# Reconciliation Schema
RECONCILIATION_SCHEMA = {
    "type": "object",
    "properties": {
        "overall_assessment": {
            "type": "string",
            "description": "Overall assessment of all proposals together"
        },
        "conflicts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "issue": {
                        "type": "string",
                        "description": "Description of the conflict"
                    },
                    "proposals": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Proposal IDs involved in the conflict"
                    }
                },
                "required": ["issue", "proposals"]
            },
            "description": "List of conflicts identified between proposals"
        },
        "recommendations": {
            "type": "object",
            "additionalProperties": {
                "type": "string"
            },
            "description": "Recommendations for each proposal (proposal_id -> recommendation)"
        }
    },
    "required": ["overall_assessment", "conflicts", "recommendations"]
}

# Arbitration Schema
ARBITRATION_SCHEMA = {
    "type": "object",
    "properties": {
        "decision": {
            "type": "string",
            "description": "Arbiter's decision and reasoning"
        },
        "approved_proposals": {
            "type": "array",
            "items": {"type": "string"},
            "description": "IDs of proposals approved by arbiter"
        },
        "rejected_proposals": {
            "type": "array",
            "items": {"type": "string"},
            "description": "IDs of proposals rejected by arbiter"
        },
        "modifications": {
            "type": "object",
            "additionalProperties": {
                "type": "string"
            },
            "description": "Suggested modifications for proposals (proposal_id -> modification)"
        }
    },
    "required": ["decision", "approved_proposals", "rejected_proposals"]
}
