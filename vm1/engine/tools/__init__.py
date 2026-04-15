"""
MMON VM1 — Tool Registry.
Mappa nomi tool → classi wrapper.
"""
from .bbot_wrapper import BbotWrapper
from .dorks_wrapper import DorksWrapper
from .mosint_wrapper import MosintWrapper
from .shodan_wrapper import ShodanWrapper
from .theharvester_wrapper import TheHarvesterWrapper
from .trufflehog_wrapper import TrufflehogWrapper

TOOL_REGISTRY: dict[str, type] = {
    "bbot": BbotWrapper,
    "mosint": MosintWrapper,
    "trufflehog": TrufflehogWrapper,
    "shodan": ShodanWrapper,
    "theharvester": TheHarvesterWrapper,
    "dorks": DorksWrapper,
}

__all__ = ["TOOL_REGISTRY"]
