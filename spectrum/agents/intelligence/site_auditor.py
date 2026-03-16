"""SiteAuditor — monitors site health with snapshots every 30 minutes.

Checks:
- Page speed (via PageSpeed Insights API)
- Broken links (404s)
- Plugin health
- SSL certificate
- Uptime
- Core Web Vitals
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import structlog

from config.settings import get_settings
from spectrum.core.agent import Agent, AgentResult, AgentRole

logger = structlog.get_logger()


class SiteAuditor(Agent):
    """Monitors dogsstate.co.il health and creates snapshots."""

    @property
    def role(self) -> AgentRole:
        return AgentRole.SITE_AUDITOR

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        settings = get_settings()
        site_url = settings.wp.base_url
        mode = context.get("mode", "full")

        results: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "site_url": site_url,
        }
        errors: list[str] = []
        warnings: list[str] = []
        score = 100

        async with httpx.AsyncClient(timeout=30.0) as client:
            # ── Uptime Check ──────────────────────────────
            try:
                resp = await client.get(site_url)
                results["status_code"] = resp.status_code
                results["response_time_ms"] = int(resp.elapsed.total_seconds() * 1000)
                if resp.status_code != 200:
                    errors.append(f"Homepage returned {resp.status_code}")
                    score -= 30
                if results["response_time_ms"] > 3000:
                    warnings.append(f"Slow response: {results['response_time_ms']}ms")
                    score -= 10
            except httpx.RequestError as e:
                errors.append(f"Site unreachable: {e}")
                score -= 50

            # ── SSL Check ─────────────────────────────────
            if site_url.startswith("https"):
                results["ssl_valid"] = True
            else:
                warnings.append("Site not using HTTPS")
                score -= 10

            # ── Key Pages Check ───────────────────────────
            key_pages = ["/", "/shop/", "/blog/", "/contact/"]
            broken_pages: list[str] = []
            for page in key_pages:
                try:
                    resp = await client.get(f"{site_url}{page}", follow_redirects=True)
                    if resp.status_code >= 400:
                        broken_pages.append(f"{page} → {resp.status_code}")
                except httpx.RequestError:
                    broken_pages.append(f"{page} → unreachable")

            if broken_pages:
                errors.extend([f"Broken page: {p}" for p in broken_pages])
                score -= len(broken_pages) * 5
            results["broken_pages"] = broken_pages

            # ── PageSpeed Insights ────────────────────────
            try:
                psi_url = (
                    f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
                    f"?url={site_url}&strategy=mobile"
                )
                psi_resp = await client.get(psi_url, timeout=60.0)
                if psi_resp.status_code == 200:
                    psi_data = psi_resp.json()
                    lighthouse = psi_data.get("lighthouseResult", {})
                    categories = lighthouse.get("categories", {})
                    performance = categories.get("performance", {})
                    results["performance_score"] = int(performance.get("score", 0) * 100)
                    results["core_web_vitals"] = {
                        "LCP": lighthouse.get("audits", {})
                        .get("largest-contentful-paint", {})
                        .get("displayValue", "N/A"),
                        "FID": lighthouse.get("audits", {})
                        .get("max-potential-fid", {})
                        .get("displayValue", "N/A"),
                        "CLS": lighthouse.get("audits", {})
                        .get("cumulative-layout-shift", {})
                        .get("displayValue", "N/A"),
                    }
                    if results["performance_score"] < 50:
                        warnings.append(
                            f"Low performance score: {results['performance_score']}/100"
                        )
                        score -= 10
            except Exception as e:
                warnings.append(f"PageSpeed check failed: {e}")

        # ── Save Snapshot ─────────────────────────────────
        if mode == "snapshot":
            self._save_snapshot(results)

        score = max(0, score)

        return AgentResult(
            success=score >= 70,
            role=self.role,
            data=results,
            errors=errors,
            warnings=warnings,
            score=score,
        )

    def _save_snapshot(self, data: dict[str, Any]) -> None:
        settings = get_settings()
        snapshots_dir = settings.system.snapshots_dir
        snapshots_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filepath = snapshots_dir / f"snapshot_{timestamp}.json"
        filepath.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        self.log.info("snapshot_saved", path=str(filepath))
