"""BrandManager — auto-detect, assign, clean up, and normalize product brands.

DogsState uses TWO brand systems:
1. `product_brand` taxonomy (Hebrew names) — shown in shop filters, 84 terms
2. `pa_מותג` attribute (English names) — WooCommerce product attributes, 103 terms

"שונות" (slug=dogs-state-stuff, ID=1006) = 286 products with no real brand.
This agent resolves both systems and syncs them.
"""

from __future__ import annotations

from typing import Any

from spectrum.core.agent import Agent, AgentResult, AgentRole

# ── Hebrew brand taxonomy (product_brand) to English mapping ──
# This maps the wp taxonomy term to the canonical English brand name.
HEBREW_TO_ENGLISH: dict[str, str] = {
    "רויאל קנין": "Royal Canin",
    "קיט קט": "Kit Cat",
    "פרמיו": "Premio",
    "שזיר": "Schesir",
    "וונפי": "Wanpy",
    "קונג": "Kong",
    "מונג'": "Monge",
    "סופר פטס": "Super Pets",
    "לקרס": "לקרס",
    "לה קט": "La Cat",
    "פטס פרוג'קט": "Petsproject",
    "פריסקיז": "Friskies",
    "ארמ אנד האמר": "Arm & Hammer",
    "טייסט אוף דה ויילד": "Taste of the Wild",
    "פרו פלאן": "Pro Plan",
    "וט לייף": "VetLife",
    "ווגז אנד וויגלז": "Wags & Wiggles",
    "פלקסי": "Flexi",
    "טריקסי": "Trixie",
    "אקאנה": "Acana",
    "פורינה": "Purina",
    "פנסי פיסט": "Fancy Feast",
    "כנען": "כנען",
    "נאטורל אנד דלישס": "Farmina",
    "נייטיב וואי": "Native Way",
    "אלפא ספיריט": "Alpha Spirit",
    "גו": "GO",
    "פרימורדיאל": "Primordial",
    "או דוג": "O'Dog",
    "סופרים": "Superme",
    "אורבן צ'ויס": "Urban Choice",
    "ג'וסרה": "Josera",
    "קיווי": "Kiwi Walker",
    "אדוונס": "Advance",
    "אי דוג": "Idog",
    "פארמינה": "Farmina",
    "בונאסיבו": "BonaCibo",
    "אינאבה": "Inaba",
    "האונד": "Hound",
    "בריט": "Brit",
    "קארנילאב": "Carnilove",
    "אליזקט": "Elizacat",
    "טרולי": "Truly",
    "ווימזיס": "Whimzees",
    "וורדס בסט": "World's Best",
    "מקס אנד מולי": "Max & Molly",
    "צ׳ורו": "Churu",
    "אבר קלין": "Ever Clean",
    "נקסגארד": "NexGard",
    "פרו גרוום": "Pro Groom",
    "פרפלאסט": "Ferplast",
    "ארתי פאוז": "Earthy Pawz",
    "ויטה קראפט": "Vitakraft",
    "ויסקס": "Whiskas",
    "יורו קיטי": "Euro Kitty",
    "נאו": "NOW",
    "סימבה": "Simba",
    "ריבוס": "Ribos",
    "ביהפר": "Beaphar",
    "בריליאנט": "Brilliant",
    "האלטי": "Halti",
    "הורייזן": "Horizon",
    "לנדה": "Lenda",
    "פראמי": "Prama",
    "וולנס קור": "Wellness Core",
    "וט סולושן": "Monge VetSolution",
    "וטס בסט": "Vet's Best",
    "מיגליאור גאטו": "Miglior Gatto",
    "מיגליום": "Meglium",
    "סרסטו": "Seresto",
    "פליקס": "Felix",
    "בונזו": "Bonzo",
    "גימקאט": "GimCat",
    "ווילדה סביריקה": "Wilda Siberica",
    "טרו ווט": "Trovet",
    "סימפל סולושן": "Simple Solution",
    "דוגרס": "Doggers",
    "יאלוט": "Yalute",
    "יופ": "Yuup",
    "מיאו מיקס": "Meow Mix",
    "פנסי פיסט גולד": "Fancy Feast",
    "שיבא": "Sheba",
    "מורנדו": "Morando",
    "שונות": "__MISC__",  # Catch-all, needs resolution
}

# Reverse: English to Hebrew brand taxonomy term
ENGLISH_TO_HEBREW: dict[str, str] = {
    v: k for k, v in HEBREW_TO_ENGLISH.items() if v != "__MISC__"
}

# ── Known brand patterns in product names ────────────────────
# Maps name patterns (lowercase) to the canonical brand name.
# Longest patterns are matched first to avoid false positives.
BRAND_PATTERNS: dict[str, str] = {
    # English brands — exact or common prefixes in product names
    "royal canin": "Royal Canin",
    "pro plan": "Pro Plan",
    "taste of the wild": "Taste of the Wild",
    "arm and hammer": "Arm & Hammer",
    "arm & hammer": "Arm & Hammer",
    "alpha spirit": "Alpha Spirit",
    "ever clean": "Ever Clean",
    "native way": "Native Way",
    "super pets": "Super Pets",
    "wags & wiggles": "Wags & Wiggles",
    "wags and wiggles": "Wags & Wiggles",
    "max & molly": "Max & Molly",
    "max and molly": "Max & Molly",
    "marley & dan": "Marley & Dan",
    "marly & dan": "Marley & Dan",
    "kiwi walker": "Kiwi Walker",
    "natural code": "Natural Code",
    "nutri vet": "Nutri Vet",
    "dr pet": "Dr Pet",
    "pro groom": "Pro Groom",
    "kit cat": "Kit Cat",
    "la cat": "La Cat",
    "pets project": "Petsproject",
    "petsproject": "Petsproject",
    "urban choice": "Urban Choice",
    "wilda siberica": "Wilda Siberica",
    "tricky treats": "Tricky Treats",
    "acana": "Acana",
    "advance": "Advance",
    "beaphar": "Beaphar",
    "bonacibo": "BonaCibo",
    "brit": "Brit",
    "carnilove": "Carnilove",
    "cateat": "CatEat",
    "churu": "Churu",
    "fancy feast": "Fancy Feast",
    "farmina": "Farmina",
    "felix": "Felix",
    "ferplast": "Ferplast",
    "flexi": "Flexi",
    "friskies": "Friskies",
    "halti": "Halti",
    "hartz": "Hartz",
    "horizon": "Horizon",
    "josera": "Josera",
    "kong": "Kong",
    "lenda": "Lenda",
    "monge": "Monge",
    "nexguard": "NexGard",
    "nexgard": "NexGard",
    "o'dog": "O'Dog",
    "premio": "Premio",
    "primordial": "Primordial",
    "ribos": "Ribos",
    "schesir": "Schesir",
    "simba": "Simba",
    "solo": "Solo",
    "superme": "Superme",
    "supreme": "Superme",
    "trixie": "Trixie",
    "tropiclean": "TropiClean",
    "vitakraft": "Vitakraft",
    "wanpy": "Wanpy",
    "whimzees": "Whimzees",
    "whiskas": "Whiskas",
    "zeus": "Zeus",
    "advantage": "Advantage",
    "idog": "Idog",
    "miglior": "Miglior",
    "afp": "AFP",
    "go!": "GO",
    "elizacat": "Elizacat",
    "fun ta": "Fun Ta",
    "garden bites": "Garden Bites",
    "multi cat": "Multi Cat",
    "petstages": "Petstages",
    "prama": "Prama",
    "yuup": "Yuup",
    "bil-jac": "Bil-Jac",
    "bill jack": "Bil-Jac",
    "n&d": "Farmina",
    "nd ": "Farmina",
    "moustache": "Moustache",
    "sticky fluffy": "Sticky Fluffy",
    # Hebrew brands
    "לקרס": "לקרס",
    "כנען": "כנען",
    "פלקסי": "Flexi",
    "טרולי": "טרולי",
    "קארניבור": "קארניבור",
    "פרימיו": "פרימיו",
    "אלפא דוג": "אלפא דוג",
    "האנטר בייטס": "האנטר בייטס",
    "אמיתי": "אמיתי",
    "זוהר": "זוהר",
    "אליזקט": "Elizacat",
    "סופר פטס": "Super Pets",
    "מקס אנד מולי": "Max & Molly",
    "מקס": "Max & Molly",
    "שונרא": "שונרא",
    "איזי": "איזי",
    "טרו וט": "טרו וט",
    "קיט קט": "Kit Cat",
}

# Brands that should be merged into a canonical form
BRAND_MERGES: dict[str, str] = {
    "GO!": "GO",
    "Bill Jack": "Bil-Jac",
    "Marly & Dan": "Marley & Dan",
    "Max and Molly": "Max & Molly",
    "Max & Molly": "Max & Molly",
    "מקס אנד מולי": "Max & Molly",
    "מקס": "Max & Molly",
    "N&D": "Farmina",
    "Vet Life": "VetLife",
    "Fancy Gourmet": "Fancy Feast",
    "Gourmet Pearl": "Fancy Feast",
    "בריט": "Brit",
    "שונרא": "שונרא",
}


def detect_brand(product_name: str) -> str | None:
    """Detect brand from product name using pattern matching.

    Tries longest patterns first to avoid false positives
    (e.g., "Kit Cat" before "Kit").
    """
    name_lower = product_name.lower().strip()

    # Remove common prefixes/noise
    for prefix in ("- ", "– ", "— "):
        if prefix in name_lower:
            # Brand is usually before the dash
            pass

    # Sort patterns by length (longest first) for accurate matching
    for pattern, brand in sorted(
        BRAND_PATTERNS.items(), key=lambda x: len(x[0]), reverse=True
    ):
        if pattern in name_lower:
            return brand

    return None


class BrandManager(Agent):
    """Manages brand attributes across all products.

    Modes:
    - scan: Detect missing brands and report what would change
    - assign: Auto-assign detected brands (dry_run=True for preview)
    - cleanup: Merge duplicate brands and delete empty terms
    """

    @property
    def role(self) -> AgentRole:
        return AgentRole.BRAND_MANAGER

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        action = context.get("action", "scan")

        if action == "scan":
            return await self._scan(context)
        if action == "assign":
            return await self._assign_brands(context)
        if action == "cleanup":
            return await self._cleanup_brands(context)

        return AgentResult(
            success=False,
            role=self.role,
            errors=[f"Unknown action: {action}"],
        )

    async def _scan(self, context: dict[str, Any]) -> AgentResult:
        """Scan all products and report brand detection results."""
        products = context.get("products", [])

        detected: list[dict[str, Any]] = []
        unmatched: list[dict[str, Any]] = []

        for p in products:
            has_brand = any(
                a.get("name", "").lower() in ("מותג", "brand")
                for a in p.get("attributes", [])
            )
            if has_brand:
                continue

            brand = detect_brand(p.get("name", ""))
            entry = {
                "id": p.get("id"),
                "name": p.get("name", "")[:80],
                "status": p.get("status", ""),
            }

            if brand:
                entry["detected_brand"] = brand
                detected.append(entry)
            else:
                unmatched.append(entry)

        return AgentResult(
            success=True,
            role=self.role,
            data={
                "total_scanned": len(products),
                "already_has_brand": len(products) - len(detected) - len(unmatched),
                "detected": detected,
                "detected_count": len(detected),
                "unmatched": unmatched,
                "unmatched_count": len(unmatched),
            },
            score=100,
        )

    async def _assign_brands(self, context: dict[str, Any]) -> AgentResult:
        """Assign detected brands to products via WooCommerce API."""
        from config.settings import get_settings
        from spectrum.integrations.woocommerce import WooCommerceClient

        settings = get_settings()
        wc = WooCommerceClient(settings.wp, settings.wc)

        dry_run = context.get("dry_run", True)
        products = context.get("products", [])

        assigned: list[dict[str, Any]] = []
        failed: list[dict[str, Any]] = []
        skipped: list[dict[str, Any]] = []

        try:
            for p in products:
                # Skip if already has brand
                has_brand = any(
                    a.get("name", "").lower() in ("מותג", "brand")
                    for a in p.get("attributes", [])
                )
                if has_brand:
                    continue

                brand = detect_brand(p.get("name", ""))
                if not brand:
                    skipped.append({"id": p["id"], "name": p.get("name", "")[:60]})
                    continue

                entry = {
                    "id": p["id"],
                    "name": p.get("name", "")[:60],
                    "brand": brand,
                }

                if dry_run:
                    entry["action"] = "would_assign"
                    assigned.append(entry)
                    continue

                try:
                    await wc.assign_brand_to_product(p["id"], brand)
                    entry["action"] = "assigned"
                    assigned.append(entry)
                    self.log.info(
                        "brand_assigned",
                        product_id=p["id"],
                        brand=brand,
                    )
                except Exception as exc:
                    entry["action"] = "failed"
                    entry["error"] = str(exc)
                    failed.append(entry)
                    self.log.warning(
                        "brand_assign_failed",
                        product_id=p["id"],
                        brand=brand,
                        error=str(exc),
                    )
        finally:
            await wc.close()

        return AgentResult(
            success=len(failed) == 0,
            role=self.role,
            data={
                "dry_run": dry_run,
                "assigned": assigned,
                "assigned_count": len(assigned),
                "failed": failed,
                "failed_count": len(failed),
                "skipped_count": len(skipped),
            },
            errors=[f"Failed: {e['id']} - {e.get('error')}" for e in failed],
            score=100 if not failed else 80,
        )

    async def _cleanup_brands(self, context: dict[str, Any]) -> AgentResult:
        """Merge duplicate brand terms and delete empty ones."""
        from config.settings import get_settings
        from spectrum.integrations.woocommerce import WooCommerceClient

        settings = get_settings()
        wc = WooCommerceClient(settings.wp, settings.wc)
        dry_run = context.get("dry_run", True)

        try:
            # Get all brand terms
            all_terms: list[dict[str, Any]] = []
            for page in range(1, 10):
                terms = await wc.get_attribute_terms(24, per_page=100)
                if not terms:
                    break
                all_terms.extend(terms)
                if len(terms) < 100:
                    break

            merged: list[dict[str, str]] = []
            deleted: list[dict[str, Any]] = []
            errors: list[str] = []

            # Find terms to delete (0 products, not a merge target)
            canonical_names = set(BRAND_MERGES.values())
            for term in all_terms:
                name = term["name"].replace("&amp;", "&")

                # Check if this is a duplicate that should be merged
                if name in BRAND_MERGES:
                    target = BRAND_MERGES[name]
                    merged.append({
                        "from": name,
                        "to": target,
                        "term_id": str(term["id"]),
                    })

                # Delete empty terms that aren't canonical
                elif term.get("count", 0) == 0 and name not in canonical_names:
                    if dry_run:
                        deleted.append({
                            "id": term["id"],
                            "name": name,
                            "action": "would_delete",
                        })
                    else:
                        try:
                            resp = await wc._client.delete(
                                f"{wc._api}/products/attributes/24/terms/{term['id']}",
                                params={"force": True},
                            )
                            resp.raise_for_status()
                            deleted.append({
                                "id": term["id"],
                                "name": name,
                                "action": "deleted",
                            })
                        except Exception as exc:
                            errors.append(f"Delete {name}: {exc}")

        finally:
            await wc.close()

        return AgentResult(
            success=True,
            role=self.role,
            data={
                "dry_run": dry_run,
                "total_terms": len(all_terms),
                "merges_needed": merged,
                "merges_count": len(merged),
                "deleted": deleted,
                "deleted_count": len(deleted),
            },
            errors=errors,
            score=100 if not errors else 80,
        )
