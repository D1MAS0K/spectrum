"""Spectrum CLI — command-line interface for running agents and pipelines."""

from __future__ import annotations

import asyncio
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from config.settings import get_settings
from spectrum.core.agent import AgentRole
from spectrum.core.engine import Engine
from spectrum.core.pipeline import Pipeline, PipelineStep
from spectrum.utils.logger import setup_logging

app = typer.Typer(
    name="spectrum",
    help="Spectrum — AI-powered e-commerce automation for DogsState",
)
console = Console()


def _build_engine() -> Engine:
    """Build engine with all agents registered."""
    from spectrum.agents.content.content_factory import ContentFactory
    from spectrum.agents.content.keyword_sniper import KeywordSniper
    from spectrum.agents.content.wp_publisher import WPPublisher
    from spectrum.agents.growth.analytics_brain import AnalyticsBrain
    from spectrum.agents.growth.link_builder import LinkBuilder
    from spectrum.agents.growth.social_ops import SocialOps
    from spectrum.agents.intelligence.competitor_eye import CompetitorEye
    from spectrum.agents.intelligence.rank_tracker import RankTracker
    from spectrum.agents.intelligence.site_auditor import SiteAuditor
    from spectrum.agents.product.qa import ProductQA
    from spectrum.agents.product.rewriter import ProductRewriter
    from spectrum.agents.product.schema_guard import SchemaGuard
    from spectrum.media.gallery_manager import GalleryManager
    from spectrum.media.image_processor import ImageProcessor

    engine = Engine()

    agents = [
        ProductRewriter(),
        ProductQA(),
        SchemaGuard(),
        KeywordSniper(),
        ContentFactory(),
        WPPublisher(),
        SiteAuditor(),
        CompetitorEye(),
        RankTracker(),
        LinkBuilder(),
        SocialOps(),
        AnalyticsBrain(),
        ImageProcessor(),
        GalleryManager(),
    ]

    for agent in agents:
        engine.register(agent)

    return engine


@app.command()
def status() -> None:
    """Show system status and configured integrations."""
    settings = get_settings()
    table = Table(title="Spectrum System Status")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")

    checks = [
        ("WordPress", bool(settings.wp.app_password)),
        ("WooCommerce", bool(settings.wc.consumer_key)),
        ("Anthropic AI", bool(settings.ai.anthropic_api_key)),
        ("Google Search Console", bool(settings.google.service_account_json)),
        ("Google Analytics 4", bool(settings.ga4.property_id)),
        ("Google Merchant Center", bool(settings.google.merchant_id)),
        ("Serper (SERP API)", bool(settings.seo.serper_api_key)),
        ("SEMrush", bool(settings.seo.semrush_api_key)),
        ("Facebook", bool(settings.social.facebook_page_id)),
        ("Instagram", bool(settings.social.instagram_business_id)),
        ("Telegram", bool(settings.notifications.telegram_bot_token)),
    ]

    for name, configured in checks:
        status_text = "Configured" if configured else "Not configured"
        style = "green" if configured else "red"
        table.add_row(name, f"[{style}]{status_text}[/{style}]")

    console.print(table)


@app.command()
def audit() -> None:
    """Run a site health audit."""
    setup_logging()
    engine = _build_engine()

    async def _run() -> None:
        result = await engine.run_agent(AgentRole.SITE_AUDITOR, {"mode": "full"})
        if result.success:
            console.print("[green]Site audit passed[/green]", result.data)
        else:
            console.print("[red]Site audit issues found:[/red]")
            for err in result.errors:
                console.print(f"  - {err}")

    asyncio.run(_run())


@app.command()
def rewrite_product(product_id: int) -> None:
    """Rewrite a single product through the full pipeline (rewrite -> QA -> schema -> publish)."""
    setup_logging()
    engine = _build_engine()

    async def _run() -> None:
        from spectrum.integrations.woocommerce import WooCommerceClient

        settings = get_settings()
        wc = WooCommerceClient(settings.wp, settings.wc)

        try:
            product = await wc.get_product(product_id)
        finally:
            await wc.close()

        pipeline = Pipeline(
            name=f"product_rewrite_{product_id}",
            steps=[
                PipelineStep(agent=engine.get_agent(AgentRole.PRODUCT_REWRITER)),
                PipelineStep(agent=engine.get_agent(AgentRole.PRODUCT_QA)),
                PipelineStep(agent=engine.get_agent(AgentRole.SCHEMA_GUARD)),
            ],
        )

        result = await pipeline.run({"product": product})

        if result.success:
            console.print(f"[green]Product {product_id} rewritten successfully![/green]")
            console.print(f"Score: {result.final_score}/100")
        else:
            console.print(f"[red]Pipeline failed at step {result.steps_completed + 1}[/red]")
            for r in result.results:
                if r.errors:
                    for err in r.errors:
                        console.print(f"  - {err}")

    asyncio.run(_run())


@app.command()
def write_article(
    topic: str,
    keyword: str = "",
    publish: bool = False,
) -> None:
    """Generate and optionally publish a blog article."""
    setup_logging()
    engine = _build_engine()

    async def _run() -> None:
        steps = [
            PipelineStep(agent=engine.get_agent(AgentRole.CONTENT_FACTORY)),
        ]
        if publish:
            steps.append(
                PipelineStep(
                    agent=engine.get_agent(AgentRole.WP_PUBLISHER),
                    context_overrides={"publish_mode": "publish"},
                )
            )

        pipeline = Pipeline(name="article_creation", steps=steps)
        result = await pipeline.run({
            "topic": topic,
            "target_keyword": keyword or topic,
        })

        if result.success:
            console.print(f"[green]Article created! Words: {result.results[0].data.get('word_count')}[/green]")
        else:
            console.print("[red]Article creation failed[/red]")

    asyncio.run(_run())


@app.command()
def track_ranks(keywords: list[str]) -> None:
    """Track ranking positions for given keywords."""
    setup_logging()
    engine = _build_engine()

    async def _run() -> None:
        result = await engine.run_agent(AgentRole.RANK_TRACKER, {"keywords": keywords})
        if result.success:
            table = Table(title="Ranking Report")
            table.add_column("Keyword")
            table.add_column("Position")
            table.add_column("Status")

            for r in result.data.get("rankings", []):
                pos = str(r["position"]) if r["position"] else "Not found"
                table.add_row(r["keyword"], pos, r["status"])

            console.print(table)
            summary = result.data.get("summary", {})
            console.print(f"\nTop 3: {summary.get('top_3', 0)} | Page 1: {summary.get('page_1', 0)} | Not ranking: {summary.get('not_ranking', 0)}")

    asyncio.run(_run())


@app.command()
def competitors() -> None:
    """Run competitor analysis."""
    setup_logging()
    engine = _build_engine()

    async def _run() -> None:
        result = await engine.run_agent(AgentRole.COMPETITOR_EYE, {})
        if result.success:
            summary = result.data.get("summary", {})
            console.print(f"Keywords tracked: {summary.get('total_keywords', 0)}")
            console.print(f"Page 1 rankings: {summary.get('page_one', 0)}")
            console.print(f"Not ranking: {summary.get('not_ranking', 0)}")

    asyncio.run(_run())


@app.command()
def upload_images(folder: str) -> None:
    """Process and upload product images from a folder."""
    setup_logging()
    engine = _build_engine()

    async def _run() -> None:
        result = await engine.run_agent(
            AgentRole.GALLERY_MANAGER,
            {"action": "upload_folder", "folder_path": folder},
        )
        if result.success:
            console.print(f"[green]Uploaded {result.data.get('total_uploaded', 0)} images[/green]")
        else:
            console.print("[red]Upload failed:[/red]")
            for err in result.errors:
                console.print(f"  - {err}")

    asyncio.run(_run())


@app.command()
def find_missing_images() -> None:
    """Find all products missing images."""
    setup_logging()
    engine = _build_engine()

    async def _run() -> None:
        result = await engine.run_agent(
            AgentRole.GALLERY_MANAGER,
            {"action": "audit_missing"},
        )
        if result.success:
            missing = result.data.get("missing_images", [])
            console.print(f"[yellow]Products missing images: {len(missing)}[/yellow]")
            table = Table()
            table.add_column("ID")
            table.add_column("Name")
            table.add_column("Status")

            for p in missing[:50]:
                table.add_row(str(p["id"]), p["name"], p["status"])

            console.print(table)

    asyncio.run(_run())


@app.command()
def report(report_type: str = "weekly") -> None:
    """Generate analytics report (daily/weekly/monthly)."""
    setup_logging()
    engine = _build_engine()

    async def _run() -> None:
        result = await engine.run_agent(
            AgentRole.ANALYTICS_BRAIN,
            {"report_type": report_type},
        )
        if result.success:
            console.print(result.data.get("recommendations", ""))

    asyncio.run(_run())


@app.command()
def post_social(
    topic: str,
    platforms: list[str] = ["facebook"],
    image_url: str = "",
) -> None:
    """Create and post to social media."""
    setup_logging()
    engine = _build_engine()

    async def _run() -> None:
        result = await engine.run_agent(
            AgentRole.SOCIAL_OPS,
            {
                "action": "create_post",
                "topic": topic,
                "platforms": platforms,
                "image_url": image_url,
            },
        )
        if result.success:
            console.print(f"[green]Posted successfully![/green]")
            console.print(f"Text: {result.data.get('post_text', '')}")

    asyncio.run(_run())


@app.command()
def daemon() -> None:
    """Start Spectrum in daemon mode with all scheduled tasks."""
    setup_logging()
    engine = _build_engine()
    engine.start()
    console.print("[green]Spectrum daemon started. Press Ctrl+C to stop.[/green]")

    try:
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        engine.stop()
        console.print("[yellow]Spectrum stopped.[/yellow]")


if __name__ == "__main__":
    app()
