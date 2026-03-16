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
    from spectrum.agents.product.brand_manager import BrandManager
    from spectrum.agents.product.bulk_upgrader import BulkUpgrader
    from spectrum.agents.product.qa import ProductQA
    from spectrum.agents.product.rewriter import ProductRewriter
    from spectrum.agents.product.schema_guard import SchemaGuard
    from spectrum.agents.product.site_fixer import SiteFixer
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
        BrandManager(),
        SiteFixer(),
        BulkUpgrader(),
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
def fix_brands(
    dry_run: bool = True,
    action: str = "scan",
) -> None:
    """Manage product brands: scan, assign, or cleanup.

    Actions:
    - scan: Report missing brands and what would be auto-detected
    - assign: Auto-assign brands from product names (use --no-dry-run to execute)
    - cleanup: Merge duplicate brands, delete empties
    """
    setup_logging()
    engine = _build_engine()

    async def _run() -> None:
        from spectrum.integrations.woocommerce import WooCommerceClient

        settings = get_settings()
        wc = WooCommerceClient(settings.wp, settings.wc)

        try:
            # Load all products
            all_products: list[dict] = []
            page = 1
            while True:
                products = await wc.get_products(status="any", per_page=100, page=page)
                if not products:
                    break
                all_products.extend(products)
                page += 1
                if len(products) < 100:
                    break
        finally:
            await wc.close()

        console.print(f"[cyan]Loaded {len(all_products)} products[/cyan]")

        result = await engine.run_agent(
            AgentRole.BRAND_MANAGER,
            {"action": action, "products": all_products, "dry_run": dry_run},
        )

        if action == "scan":
            data = result.data
            console.print(f"\n[bold]Brand Scan Results:[/bold]")
            console.print(f"  Already has brand: {data.get('already_has_brand', 0)}")
            console.print(f"  Auto-detected: [green]{data.get('detected_count', 0)}[/green]")
            console.print(f"  Could not match: [yellow]{data.get('unmatched_count', 0)}[/yellow]")

            detected = data.get("detected", [])
            if detected:
                table = Table(title="Auto-Detected Brands (first 30)")
                table.add_column("ID")
                table.add_column("Product")
                table.add_column("Detected Brand")
                for d in detected[:30]:
                    table.add_row(str(d["id"]), d["name"][:50], d["detected_brand"])
                console.print(table)

        elif action in ("assign", "cleanup"):
            mode = "DRY RUN" if dry_run else "EXECUTED"
            console.print(f"\n[bold]{mode}:[/bold]")
            console.print(f"  Processed: {result.data.get('assigned_count', result.data.get('deleted_count', 0))}")
            if result.errors:
                for err in result.errors:
                    console.print(f"  [red]{err}[/red]")

    asyncio.run(_run())


@app.command()
def fix_site(
    action: str = "audit",
    dry_run: bool = True,
) -> None:
    """Audit and fix site-wide product issues.

    Actions:
    - audit: Full read-only scan of all issues
    - fix_yoast: Update Yoast SEO meta for all products
    - fix_alt_text: Replace generic alt text with product names
    """
    setup_logging()
    engine = _build_engine()

    async def _run() -> None:
        from spectrum.integrations.woocommerce import WooCommerceClient

        settings = get_settings()
        wc = WooCommerceClient(settings.wp, settings.wc)

        try:
            all_products: list[dict] = []
            page = 1
            while True:
                products = await wc.get_products(status="any", per_page=100, page=page)
                if not products:
                    break
                all_products.extend(products)
                page += 1
                if len(products) < 100:
                    break
        finally:
            await wc.close()

        console.print(f"[cyan]Loaded {len(all_products)} products[/cyan]")

        result = await engine.run_agent(
            AgentRole.SITE_FIXER,
            {"action": action, "products": all_products, "dry_run": dry_run},
        )

        if action == "audit":
            summary = result.data.get("summary", {})
            table = Table(title="Site Audit Results")
            table.add_column("Issue", style="cyan")
            table.add_column("Count", style="bold")
            table.add_column("Severity")

            severity_map = {
                "no_brand": ("🔴", "Critical"),
                "description_below_standard": ("🔴", "Critical"),
                "no_product_schema": ("🔴", "Critical"),
                "single_image": ("🟡", "High"),
                "generic_alt_text": ("🟡", "High"),
                "missing_yoast_title": ("🟡", "High"),
                "missing_yoast_desc": ("🟡", "High"),
                "no_images": ("🟠", "Medium"),
                "short_description_too_long": ("🟠", "Medium"),
                "no_price": ("🔴", "Critical"),
                "out_of_stock": ("⚪", "Info"),
            }

            for issue, count in sorted(summary.items(), key=lambda x: -x[1]):
                sev = severity_map.get(issue, ("⚪", "Info"))
                table.add_row(issue, str(count), f"{sev[0]} {sev[1]}")

            console.print(table)
            console.print(f"\n[bold]Total issues: {result.data.get('total_issues', 0)}[/bold]")
        else:
            mode = "DRY RUN" if dry_run else "EXECUTED"
            console.print(f"\n[bold]{mode}: {result.data.get('fixed_count', 0)} items processed[/bold]")

    asyncio.run(_run())


@app.command()
def upgrade_descriptions(
    limit: int = 10,
    dry_run: bool = True,
    publish: bool = False,
) -> None:
    """Bulk-upgrade product descriptions to 5000+ chars standard.

    Uses AI rewriting + QA pipeline. Start with --dry-run to preview.
    """
    setup_logging()
    engine = _build_engine()

    async def _run() -> None:
        from spectrum.integrations.woocommerce import WooCommerceClient

        settings = get_settings()
        wc = WooCommerceClient(settings.wp, settings.wc)

        try:
            all_products: list[dict] = []
            page = 1
            while True:
                products = await wc.get_products(status="publish", per_page=100, page=page)
                if not products:
                    break
                all_products.extend(products)
                page += 1
                if len(products) < 100:
                    break
        finally:
            await wc.close()

        console.print(f"[cyan]Loaded {len(all_products)} published products[/cyan]")

        action = "upgrade_and_publish" if publish else "upgrade"
        if dry_run:
            action = "scan"

        result = await engine.run_agent(
            AgentRole.BULK_UPGRADER,
            {
                "action": action,
                "products": all_products,
                "limit": limit,
                "dry_run": dry_run,
            },
        )

        if dry_run or action == "scan":
            data = result.data
            console.print(f"\n[bold]Description Upgrade Scan:[/bold]")
            console.print(f"  Need upgrade: [yellow]{data.get('needs_upgrade_count', 0)}[/yellow]")
            console.print(f"  Already good: [green]{data.get('already_good_count', 0)}[/green]")

            needs = data.get("needs_upgrade", data.get("would_upgrade", []))
            if needs:
                table = Table(title=f"Would upgrade (showing first {min(20, len(needs))})")
                table.add_column("ID")
                table.add_column("Product")
                table.add_column("Current Length")
                table.add_column("Gap")
                for n in needs[:20]:
                    table.add_row(
                        str(n["id"]),
                        n["name"][:40],
                        str(n.get("current_length", "?")),
                        str(n.get("gap", "?")),
                    )
                console.print(table)
        else:
            data = result.data
            console.print(f"\n[bold]Upgrade Results:[/bold]")
            console.print(f"  Upgraded: [green]{data.get('upgraded_count', 0)}[/green]")
            console.print(f"  Failed: [red]{data.get('failed_count', 0)}[/red]")

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
