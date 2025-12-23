"""
External service integrations for Rise Local Pipeline

This package contains all service clients and integrations for the Rise Local
lead generation pipeline. For backward compatibility, all classes are re-exported
at the package level.

Usage:
    from rise_pipeline.services import SupabaseClient, IntelligenceServices

    # Or use specific imports for new code:
    from rise_pipeline.services.database import SupabaseClient
    from rise_pipeline.services.enrichment import IntelligenceServices
    from rise_pipeline.services.intelligence import RAGService, LLMCouncil
"""

from .database import SupabaseClient
from .enrichment import ClayClient, IntelligenceServices, FullEnrichClient
from .delivery import InstantlyClient, GHLClient, HeyReachClient
from .intelligence import RAGService, HallucinationDetector, LLMCouncil
from .visualization import QuickChartClient

__all__ = [
    # Database
    'SupabaseClient',
    # Enrichment
    'ClayClient',
    'IntelligenceServices',
    'FullEnrichClient',
    # Delivery
    'InstantlyClient',
    'GHLClient',
    'HeyReachClient',
    # Intelligence
    'RAGService',
    'HallucinationDetector',
    'LLMCouncil',
    # Visualization
    'QuickChartClient',
]
