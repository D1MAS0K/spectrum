"""Pre-built pipelines — complete workflows that chain agents together.

These are the "battle plans" — each pipeline defines a full workflow
that mirrors what Claw + TheMainDog did manually.
"""

from __future__ import annotations

from spectrum.core.agent import AgentRole
from spectrum.core.engine import Engine
from spectrum.core.pipeline import Pipeline, PipelineStep


def product_rewrite_pipeline(engine: Engine, publish: bool = False) -> Pipeline:
    """Full product rewrite: write -> QA -> schema -> (optional) publish.

    This is the equivalent of the Claw+TheMainDog review cycle:
    1. ProductRewriter writes content (Claw)
    2. ProductQA checks quality (TheMainDog's 100/100 gate)
    3. SchemaGuard validates structured data
    4. WPPublisher publishes (only if QA passes)
    """
    steps = [
        PipelineStep(agent=engine.get_agent(AgentRole.PRODUCT_REWRITER)),
        PipelineStep(agent=engine.get_agent(AgentRole.PRODUCT_QA), required_score=100),
        PipelineStep(agent=engine.get_agent(AgentRole.SCHEMA_GUARD)),
    ]
    if publish:
        steps.append(
            PipelineStep(
                agent=engine.get_agent(AgentRole.WP_PUBLISHER),
                context_overrides={"publish_mode": "publish", "post_type": "product"},
            )
        )
    return Pipeline(name="product_rewrite", steps=steps)


def article_pipeline(engine: Engine, publish: bool = False) -> Pipeline:
    """Full blog article: keyword research -> write -> (optional) publish."""
    steps = [
        PipelineStep(agent=engine.get_agent(AgentRole.KEYWORD_SNIPER)),
        PipelineStep(agent=engine.get_agent(AgentRole.CONTENT_FACTORY)),
    ]
    if publish:
        steps.append(
            PipelineStep(
                agent=engine.get_agent(AgentRole.WP_PUBLISHER),
                context_overrides={"publish_mode": "publish", "post_type": "post"},
            )
        )
    return Pipeline(name="article_creation", steps=steps)


def image_pipeline(engine: Engine) -> Pipeline:
    """Image processing: process -> upload -> assign to product."""
    return Pipeline(
        name="image_processing",
        steps=[
            PipelineStep(agent=engine.get_agent(AgentRole.IMAGE_PROCESSOR)),
            PipelineStep(agent=engine.get_agent(AgentRole.GALLERY_MANAGER)),
        ],
    )


def daily_intelligence_pipeline(engine: Engine) -> Pipeline:
    """Daily intelligence: audit site -> track ranks -> analyze."""
    return Pipeline(
        name="daily_intelligence",
        steps=[
            PipelineStep(
                agent=engine.get_agent(AgentRole.SITE_AUDITOR),
                context_overrides={"mode": "snapshot"},
                required_score=70,
            ),
            PipelineStep(agent=engine.get_agent(AgentRole.RANK_TRACKER)),
            PipelineStep(
                agent=engine.get_agent(AgentRole.ANALYTICS_BRAIN),
                context_overrides={"report_type": "daily"},
            ),
        ],
    )


def full_competitor_analysis_pipeline(engine: Engine) -> Pipeline:
    """Full competitor analysis: scan competitors -> find keywords -> report."""
    return Pipeline(
        name="competitor_analysis",
        steps=[
            PipelineStep(agent=engine.get_agent(AgentRole.COMPETITOR_EYE)),
            PipelineStep(agent=engine.get_agent(AgentRole.KEYWORD_SNIPER)),
            PipelineStep(agent=engine.get_agent(AgentRole.ANALYTICS_BRAIN)),
        ],
    )
