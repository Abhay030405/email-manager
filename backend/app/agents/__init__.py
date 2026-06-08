"""CampaignX AI agents package.

Exports all five core agents so they can be imported directly from
``app.agents`` without needing to know the internal module layout::

    from app.agents import (
        BaseAgent,
        CampaignBriefParserAgent,
        CustomerSegmentationAgent,
        CampaignStrategyAgent,
        ContentGenerationAgent,
    )
"""

from app.agents.base_agent import BaseAgent
from app.agents.brief_parser import CampaignBriefParserAgent, BriefInput, ParsedBrief
from app.agents.segmentation import CustomerSegmentationAgent, SegmentOut
from app.agents.strategy import (
    CampaignStrategyAgent,
    StrategyInput,
    ABTestPlan,
    CampaignStrategy,
)
from app.agents.content_gen import (
    ContentGenerationAgent,
    ContentGenerationInput,
    EmailContent,
)

__all__ = [
    # Base
    "BaseAgent",
    # Brief parser
    "CampaignBriefParserAgent",
    "BriefInput",
    "ParsedBrief",
    # Segmentation
    "CustomerSegmentationAgent",
    "SegmentOut",
    # Strategy
    "CampaignStrategyAgent",
    "StrategyInput",
    "ABTestPlan",
    "CampaignStrategy",
    # Content generation
    "ContentGenerationAgent",
    "ContentGenerationInput",
    "EmailContent",
]
