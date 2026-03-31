"""
MMON VM1 — Tool Wrappers Registry

Importa tutti i wrapper e fornisce un registry per lo scheduler.
"""

from .base import FindingCategory, FindingPayload, FindingSeverity, ToolResult, ToolWrapper
from .bbot_wrapper import BbotWrapper
from .dorks_wrapper import DorksWrapper
from .h8mail_wrapper import H8mailWrapper
from .maigret_wrapper import MaigretWrapper
from .mosint_wrapper import MosintWrapper
from .shodan_wrapper import ShodanWrapper
from .spiderfoot_wrapper import SpiderfootWrapper
from .trape_wrapper import TrapeWrapper
from .trufflehog_wrapper import TrufflehogWrapper

# Registry: nome tool → classe wrapper
TOOL_REGISTRY: dict[str, type[ToolWrapper]] = {
    "bbot": BbotWrapper,
    "mosint": MosintWrapper,
    "h8mail": H8mailWrapper,
    "maigret": MaigretWrapper,
    "trufflehog": TrufflehogWrapper,
    "shodan": ShodanWrapper,
    "spiderfoot": SpiderfootWrapper,
    "trape": TrapeWrapper,
    "dorks": DorksWrapper,
}

__all__ = [
    "TOOL_REGISTRY",
    "ToolWrapper",
    "ToolResult",
    "FindingPayload",
    "FindingCategory",
    "FindingSeverity",
    "BbotWrapper",
    "MosintWrapper",
    "H8mailWrapper",
    "MaigretWrapper",
    "TrufflehogWrapper",
    "ShodanWrapper",
    "SpiderfootWrapper",
    "TrapeWrapper",
    "DorksWrapper",
]
