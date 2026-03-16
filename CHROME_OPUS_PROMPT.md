# DogsState Product Data Improvement — Chrome Opus Instructions

You are working on dogsstate.co.il — Israel's #1 pet store (dogs and cats). You need to fix product data via the WooCommerce REST API and WordPress REST API. The site uses Yoast SEO + Yoast WooCommerce SEO for structured data (Product Schema).

## Authentication

- **WooCommerce API**: Use Basic Auth with WordPress application password
  - Username: `dimatheking`
  - App Password: `4YgK mVeg usYa N2ej qXqJ rZJC`
  - Base URL: `https://dogsstate.co.il/wp-json/wc/v3/`
  - Always include header `User-Agent: Spectrum/1.0`

- **WordPress REST API**: Same credentials, base URL: `https://dogsstate.co.il/wp-json/wp/v2/`

## Important API Details

- **Reading products**: `GET /wc/v3/products?per_page=100&page=N&status=publish` (16 pages, 1523 products)
- **Updating a product**: `PUT /wc/v3/products/{id}` with JSON body
- **Batch update**: `POST /wc/v3/products/batch` with `{"update": [{...}, {...}]}` (max 100 per batch)
- **Brand taxonomy**: Attribute ID = **24**, slug = `pa_מותג`
- **Getting brand terms**: `GET /wc/v3/products/attributes/24/terms?per_page=100`
- **Creating new brand term**: `POST /wc/v3/products/attributes/24/terms` with `{"name": "BrandName"}`

---

## TASK 1: Fix 12 Products with Local Brand Attribute (id:0 → id:24)

These 12 products have the brand set as a **local attribute** (id:0) instead of the **taxonomy attribute** (id:24). Yoast only reads taxonomy attributes for Product Schema.

**Products to fix:**

| ID | Current Brand Value | Product Name |
|----|-------------------|--------------|
| 10141 | La Cat | La cat לה קט מיקס נטול חמץ 7.2 ק"ג |
| 10139 | La Cat | La cat - לה קט עוף נטול חמץ 7.2 ק"ג |
| 10127 | Tricky Treats | Tricky Treats טריקי טריטס עוף צלוי |
| 10119 | Tricky Treats | Tricky Treats ברווז חטיף להסתרת תרופות |
| 10114 | Tricky Treats | Tricky Treats ברווז מעושן אריזת 30 חטיפים |
| 10103 | Tricky Treats | טריקי טריטס חטיף להסתרת תרופות |
| 10100 | Pharma | פראמה חטיף לכלב תות 70 גרם |
| 10098 | Pharma | פראמה חטיף דלעת לכלב 70 גרם |
| 10096 | Pharma | פראמה חטיף לכלב מנגו 70 גרם |
| 10094 | Pharma | פארמה חטיף לכלב סלמי איטלקי 70 גרם |
| 10091 | Pharma | פראמה חטיף לכלב - פטה כבד עוף 70 גרם |
| 10088 | Pharma | פראמה חטיף לכלב - חלב הוקאידו 70 גרם |

**How to fix each product:**

1. GET the product to see all its current attributes
2. In the attributes array, find the brand entry with `id: 0` and `name: "מותג"`
3. Replace it with `id: 24` (keeping the same options value)
4. Make sure the brand term exists in taxonomy (La Cat, Tricky Treats, Prama/Pharma already exist as taxonomy terms — check with GET /wc/v3/products/attributes/24/terms)
5. PUT the product with the corrected attributes array

**Important**: Keep ALL other attributes unchanged. Only change the brand attribute id from 0 to 24.

**For Pharma/Prama**: The existing taxonomy term is called "Prama" (id check needed). Map the "Pharma" local attribute to the "Prama" taxonomy term, or if "Pharma" doesn't exist, check which name is correct and create the right one.

---

## TASK 2: Add Brand Attribute to 498 Products Missing It

498 published products have **no brand attribute at all**. For each product:

1. Read the product name and description
2. Identify the brand from the product name (most products have the brand name in the title)
3. Check if a taxonomy term already exists for this brand (GET /wc/v3/products/attributes/24/terms)
4. If not, create a new taxonomy term (POST /wc/v3/products/attributes/24/terms with {"name": "BrandName"})
5. Add the brand attribute to the product: include `{"id": 24, "options": ["BrandName"], "visible": true, "variation": false}` in the attributes array

**Existing taxonomy terms (103 brands):**
Acana, Advance, AFP, Arm & Hammer, Beaphar, BonaCibo, Brit, Carnilove, CatEat, Churu, Dr Pet, Fancy Feast, Farmina, Felix, Flexi, Friskies, Fun Ta, Garden Bites, GO, Gourmet, Halti, Hartz, Horizon, Italian Team, Josera, Kit Cat, Kiwi Walker, Kong, La Cat, Lenda, Miglior, Monge, Moustache, Multi Cat, N&D, Natural Code, NexGard, Nutri Vet, O'Dog, Petstages, Prama, Premio, Primordial, Pro Groom, Pro Plan, Ribos, Royal Canin, Schesir, Simba, Sticky Fluffy, Superme, Taste of the Wild, Trixie, TropiClean, Urban Choice, Vet Life, VetLife, Vets & Pets, Vitakraft, Wags & Wiggles, Wanpy, Whimzees, Whiskas, Wilda Siberica, Yuup, לקרס, פראמי, קיט קט

**Brand detection hints for common products without brand:**
- "אלפא דוג" / "Alpha Dog" → create term "Alpha Dog"
- "אלפא ספיריט" / "Alpha Spirit" → create term "Alpha Spirit"
- "איזי ווק" / "Easy Walk" → create term "Easy Walk" (by PetSafe)
- "סופרים" / "Supreme" → use existing "Superme" or create "Supreme"
- "סופר פטס" / "Super Pets" → create term "Super Pets"
- "בסקרוויל" / "Baskerville" → create term "Baskerville"
- "idog" / "אידוג" → create term "iDog"
- "האנטר בייטס" / "Hunter Bites" → create term "Hunter Bites"
- "קארניבור" / "Carnibest" → create term "Carnibest"
- "Earthy Pawz" → create term "Earthy Pawz"
- "בסט צוייס" / "Best Choice" → create term "Best Choice"
- "צארליז" / "Charlie's" → create term "Charlie's"
- "פט קווין" / "Pet Queen" → create term "Pet Queen"
- "קינג סטאר" / "King Star" → create term "King Star"
- "סטאר קט" / "Star Cat" → create term "Star Cat"
- "Almo Nature" → create term "Almo Nature"
- "NOW" (pet food brand) → create term "NOW Fresh"
- "אליזקט" / "ElizaCat" → create term "ElizaCat"
- "Sentry" → create term "Sentry"
- "TroVet" / "טרו וט" → create term "TroVet"
- "Feliway" → create term "Feliway"
- "Seresto" / "סרסטו" → create term "Seresto"
- "Advantage" / "אדוונטייג" → create term "Advantage"
- "Frontline" / "פרונטליין" → create term "Frontline"
- "M & M" (pet beds brand) → create term "M&M Pet"
- "Brokaton" / "ברוקטון" → create term "Brokaton"

**For generic/unbranded products** (beds, toys, accessories without a brand name in the title): Skip them. Do NOT invent a brand. Only set brands you can confidently identify from the product name.

---

## TASK 3: Improve 164 Short Product Descriptions

164 published products have descriptions shorter than 1000 characters. The store standard is 1500+ characters minimum.

**Rules for improving descriptions:**

1. **Language**: All descriptions must be in Hebrew (RTL)
2. **Minimum length**: 1500 characters after HTML stripping
3. **DO NOT change existing good content** — only expand short descriptions
4. **DO NOT mix categories**:
   - Dog food is NOT cat food
   - Shampoo is NOT equipment
   - Leashes are NOT toys
   - Toys are NOT food
   - Check the product categories BEFORE writing
5. **Use the product's actual categories** to understand what it is
6. **Use the existing short_description** for context about the product
7. **Structure**: Use purple emoji 🟣 for bullet points (brand style), include FAQ section with Schema markup
8. **Tone**: Expert but warm, loves animals (DogsState brand voice)
9. **Include**: Product benefits, usage instructions, ingredients/specs if applicable, why DogsState recommends it
10. **SEO**: Include the product name and brand naturally in the text

**The 164 products** are mostly:
- Fancy Feast cat food cans (many variants, ~₪5.8 each, 85g)
- Carnibest/קארניבור dog chews
- Alpha Dog dog treats
- Premio Super Gold cat food
- Best Choice dog treats
- Various cat pouches
- Various small items

**For similar product variants** (e.g., 15 Fancy Feast flavors): Write unique descriptions that differ by at least 30% — mention the specific flavor, texture, and use case. Do not copy-paste the same text for different flavors.

**Update method**: PUT to `/wc/v3/products/{id}` with `{"description": "<new HTML content>"}`

---

## CRITICAL RULES

1. **NEVER change a product's categories** — only update attributes and descriptions
2. **NEVER delete existing attributes** — only add or fix the brand attribute
3. **NEVER change prices, images, SKUs, or slugs**
4. **Always GET the product first** before updating to preserve existing data
5. **Rate limiting**: Wait 300ms between API calls to avoid overloading the server
6. **Batch operations**: Use `/wc/v3/products/batch` with `{"update": [...]}` for efficiency (max 100 per batch)
7. **Verify after updating**: Check that the brand attribute id is 24 (not 0) in the response
8. **Hebrew text direction**: Descriptions should be valid HTML with proper Hebrew content

## Execution Order

1. First: Fix the 12 local brand attributes (Task 1) — quick and easy
2. Second: Add brands to the 498 products (Task 2) — work in batches of 50
3. Third: Improve the 164 short descriptions (Task 3) — most time-consuming

## Verification

After completing each task, verify by:
- GET a sample of updated products and confirm brand attribute has `id: 24`
- Check a product page with Googlebot UA to verify Product Schema includes `"brand": {"@type": "Brand", "name": "..."}`
- For descriptions: confirm the text is properly formatted Hebrew, relevant to the product category, and over 1500 characters
