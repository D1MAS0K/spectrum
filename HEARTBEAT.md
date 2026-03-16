# HEARTBEAT.md — Spectrum Automated Routine

> שגרה אוטומטית שרצה כל 30 דקות. גיבוי, ניטור, ומשימות בתור.

## Cycle: Every 30 Minutes

```
┌─────────────────────────────────────────────┐
│              HEARTBEAT CYCLE                │
│              (Every 30 min)                 │
├─────────────────────────────────────────────┤
│                                             │
│  1. BACKUP & SNAPSHOT                       │
│     └─ Save site state snapshot             │
│     └─ Compare with previous snapshot       │
│     └─ Flag unexpected changes              │
│                                             │
│  2. HEALTH CHECK                            │
│     └─ Site uptime verification             │
│     └─ API endpoint availability            │
│     └─ SSL certificate status               │
│     └─ PageSpeed score check                │
│                                             │
│  3. QUEUE CHECK                             │
│     └─ Check for pending tasks              │
│     └─ Process next task in queue           │
│     └─ Update task status                   │
│                                             │
│  4. METRICS COLLECTION                      │
│     └─ Products updated count               │
│     └─ Articles published count             │
│     └─ QA pass/fail ratio                   │
│     └─ API error rate                       │
│                                             │
│  5. REPORT (if changes detected)            │
│     └─ Summarize changes since last cycle   │
│     └─ Alert if anomalies detected          │
│                                             │
└─────────────────────────────────────────────┘
```

## Snapshot Comparison Logic

Each cycle creates a lightweight snapshot:

```python
snapshot = {
    "timestamp": "ISO-8601",
    "products": {
        "total": int,
        "draft": int,
        "published": int,
        "recently_modified": list[int]  # Product IDs modified since last snapshot
    },
    "posts": {
        "total": int,
        "draft": int,
        "published": int,
    },
    "site_health": {
        "uptime": bool,
        "response_time_ms": int,
        "pagespeed_score": int,
        "ssl_valid": bool,
    },
    "api_health": {
        "woocommerce": bool,
        "wordpress": bool,
        "google_search_console": bool,
        "google_analytics": bool,
    }
}
```

## Alert Conditions

| Condition | Severity | Action |
|-----------|----------|--------|
| Site down | CRITICAL | Telegram + WhatsApp alert immediately |
| API unreachable | HIGH | Retry 3x, then Telegram alert |
| PageSpeed drop > 10 points | MEDIUM | Log + include in next report |
| Unexpected product changes | MEDIUM | Flag for review, log diff |
| SSL expiring < 7 days | HIGH | Telegram alert |
| Queue backlog > 50 items | MEDIUM | Log warning, consider scaling |
| QA fail rate > 20% | HIGH | Pause pipeline, alert for review |

## Integration with APScheduler

The heartbeat is implemented via `core/scheduler.py` using APScheduler:

```python
# Scheduled job configuration
heartbeat_job = {
    "id": "heartbeat",
    "func": "spectrum.core.engine:Engine.heartbeat",
    "trigger": "interval",
    "minutes": 30,
    "max_instances": 1,  # Prevent overlap
    "coalesce": True,    # Skip missed beats
}
```

## Queue System

Tasks are queued for processing during heartbeat cycles:

| Priority | Type | Example |
|----------|------|---------|
| 1 (Highest) | Critical fix | Broken Schema, missing image on live product |
| 2 | Product rewrite | Scheduled product optimization |
| 3 | Content creation | Blog article from keyword research |
| 4 | Maintenance | Category cleanup, attribute audit |
| 5 (Lowest) | Analytics | Report generation, rank tracking |

## Daemon Mode

When running `spectrum daemon`, the heartbeat starts automatically:

```bash
spectrum daemon
# Starts APScheduler with:
# - Heartbeat: every 30 minutes
# - Rank tracking: daily at 06:00
# - Competitor monitoring: every 6 hours
# - Site audit: daily at 03:00
# - Analytics report: weekly on Sunday
```
