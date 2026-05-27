"""Virtual society simulation core."""

from .agent_dossiers import (
    AGENT_DOSSIER_VERSION,
    build_agent_dossier,
    build_agent_dossiers,
    build_agent_record,
    build_relationship_links,
)
from .codex_cli_provider import CodexCliCognition, CodexCliDialogue, CodexCliReflection
from .choice_tension_evaluation import ChoiceTensionFinding, assess_choice_tensions
from .cognition import RuleBasedCognition
from .cognition_impact_evaluation import assess_cognition_impacts
from .cognition_outcome_evaluation import assess_cognition_outcomes
from .counterfactual_cognition import (
    PlanCounterfactualComparison,
    PlanProbeResult,
    compare_plan_counterfactuals,
)
from .counterfactual_evaluation import (
    CounterfactualAssessment,
    CounterfactualBucket,
    CounterfactualProbeRecord,
    assess_counterfactual_trace,
)
from .dialogue import (
    HybridDialogue,
    HybridDialogueConfig,
    HybridDialogueStats,
    HybridDialogueTrace,
    RuleBasedDialogue,
)
from .dialogue_contract import (
    DialogueProposal,
    build_dialogue_context,
    parse_dialogue_response,
    render_dialogue_prompt,
)
from .dialogue_evaluation import assess_dialogue_follow_through
from .generative_chain_evaluation import assess_generated_chains
from .historical_scars import HistoricalScarFinding, build_historical_scar_validation
from .hybrid_cognition import (
    HybridCognition,
    HybridCognitionConfig,
    HybridCognitionStats,
    HybridCognitionTrace,
)
from .interventions import Intervention
from .llm_cache import LLMCacheRecord, LLMCacheStats, LLMCallCache
from .llm_contract import PLAN_PROMPT_VERSION, build_cognition_context, parse_plan_response, render_plan_prompt
from .model import AgentProfile, LifeEpisode, MemoryItem, Plan
from .observer_intent_evaluation import ObserverIntentFinding, assess_observer_intents
from .observer_recommendations import (
    ObserverRecommendation,
    build_observer_recommendations,
    intervention_payloads,
)
from .openai_provider import OpenAICognition, OpenAIDialogue, OpenAIReflection
from .reason_richness_evaluation import ReasonRichnessFinding, assess_reason_richness
from .scar_diagnosis import ScarBottleneck, assess_scar_bottlenecks
from .api import SimulationService
from .reflection import (
    HybridReflection,
    HybridReflectionConfig,
    HybridReflectionStats,
    HybridReflectionTrace,
    RuleBasedReflection,
)
from .reflection_contract import (
    ReflectionProposal,
    build_reflection_context,
    parse_reflection_response,
    render_reflection_prompt,
)
from .reflection_evaluation import assess_reflection_follow_through
from .simulation import Simulation
from .social_evaluation import SocialFinding, assess_social_dynamics
from .social_chronicle import ChronicleEntry, build_social_chronicle

__all__ = [
    "Intervention",
    "Plan",
    "PlanCounterfactualComparison",
    "PlanProbeResult",
    "PLAN_PROMPT_VERSION",
    "AGENT_DOSSIER_VERSION",
    "AgentProfile",
    "CounterfactualAssessment",
    "CounterfactualBucket",
    "CounterfactualProbeRecord",
    "ChronicleEntry",
    "ChoiceTensionFinding",
    "DialogueProposal",
    "HistoricalScarFinding",
    "LifeEpisode",
    "MemoryItem",
    "LLMCacheRecord",
    "LLMCacheStats",
    "LLMCallCache",
    "ObserverIntentFinding",
    "ObserverRecommendation",
    "OpenAICognition",
    "OpenAIDialogue",
    "OpenAIReflection",
    "SocialFinding",
    "CodexCliCognition",
    "CodexCliDialogue",
    "CodexCliReflection",
    "HybridCognition",
    "HybridCognitionConfig",
    "HybridCognitionStats",
    "HybridCognitionTrace",
    "HybridDialogue",
    "HybridDialogueConfig",
    "HybridDialogueStats",
    "HybridDialogueTrace",
    "HybridReflection",
    "HybridReflectionConfig",
    "HybridReflectionStats",
    "HybridReflectionTrace",
    "ReflectionProposal",
    "ReasonRichnessFinding",
    "ScarBottleneck",
    "RuleBasedCognition",
    "RuleBasedDialogue",
    "RuleBasedReflection",
    "SimulationService",
    "Simulation",
    "build_cognition_context",
    "build_agent_dossier",
    "build_agent_dossiers",
    "build_agent_record",
    "build_relationship_links",
    "build_dialogue_context",
    "build_reflection_context",
    "assess_cognition_impacts",
    "assess_cognition_outcomes",
    "assess_choice_tensions",
    "assess_counterfactual_trace",
    "assess_observer_intents",
    "build_observer_recommendations",
    "assess_reason_richness",
    "assess_scar_bottlenecks",
    "build_historical_scar_validation",
    "build_social_chronicle",
    "compare_plan_counterfactuals",
    "intervention_payloads",
    "assess_dialogue_follow_through",
    "assess_generated_chains",
    "assess_reflection_follow_through",
    "parse_plan_response",
    "parse_dialogue_response",
    "parse_reflection_response",
    "render_plan_prompt",
    "render_dialogue_prompt",
    "render_reflection_prompt",
    "assess_social_dynamics",
]
