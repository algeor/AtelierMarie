# Shipping Courier Integration — Explore Questions

## Timing & Priority

1. **Is this moving up from "add-on" tier?** It's in `add-ons/` alongside the blog. Meanwhile `auth-image-upload`, `bilingual-i18n`, and `social-contact-buttons` are active. What's the trigger for starting this?

2. **Dependencies on other changes?** Bilingual/i18n touches the checkout UI too. Should this land before or after i18n? (Rewriting the shipping section twice in different languages sounds painful.)

---

## Delivery Method Coverage

3. **Is local/in-person pickup a real scenario?** The design makes `delivery` required (replaces optional `shipping_address`). For a small family business, "I'll come to the atelier and pick it up" might be a real use case. Should there be a third method: `Literal["office", "door", "local"]`?

4. **"Just ship it, I don't care how" users** — The spec forces courier choice (Speedy vs Econt). Some customers genuinely don't care. Is there value in a "Без предпочитание" (no preference) option where you pick for them? Or is that over-engineering?

---

## Data: Office Lists

5. **Where does the JSON actually come from?** Speedy and Econt have thousands of offices. Are you planning to:
   - Scrape their websites manually?
   - Use their public APIs once to dump a snapshot?
   - Find a third-party aggregated dataset?

6. **Refresh cadence** — Design says "quarterly refresh, manual." Who does this? Is it just you running a script? If offices close/move, customers pick a dead office and the order fails at the courier. What's the failure mode?

7. **Data size concern** — ~4500 offices total. At ~200 bytes each that's <1MB in memory. But the city-filtered endpoint means the frontend needs at least 2 requests (cities, then offices). Is that latency acceptable? Or should the frontend preload all offices for the selected courier in one shot?

---

## Phone UX

8. **Auto-prefix `+359`?** Bulgarian mobiles are 13 chars with country code. Should the form default the `+359` prefix and only ask for the 9-digit local number? Less typing, fewer format errors.

9. **Phone for office pickup** — The spec adds phone to the `DeliveryOffice` model. UX-wise, where does this field live? Below the office picker? It's a slightly odd flow: "pick an office... now also give us your phone." Should it feel like a separate step or inline?

---

## Architecture

10. **delivery_service.py as a pure data layer** — It loads JSON at startup and filters in memory. No DB, no async, no state. This is simpler than other services (which use SQLite). Is the "service" naming misleading? Would `app/data/offices.py` or `app/delivery_data.py` be more honest? Or keep it as a service for consistency?

11. **Startup failure mode** — Spec says missing JSON = log warning, return empty arrays. But if both files are missing, the entire delivery feature is broken silently. Should there be a health-check endpoint or startup log that confirms office data is loaded? Admin dashboard indicator?

12. **Schema migration strategy** — Design adds columns via ALTER TABLE. But `database.py` currently creates tables from scratch (in-memory for tests, file for prod). Are you doing:
    - Conditional `ALTER TABLE IF NOT EXISTS` on startup?
    - Adding columns to the CREATE TABLE statement (since there's no live prod DB yet)?
    - A proper migration system (alembic)?

---

## Breaking Change & Deployment

13. **Frontend-backend coupling** — The proposal notes "frontend and backend must deploy together." Currently, how are these deployed? Same VPS, same systemd restart? Or could there be a window where old frontend hits new backend (or vice versa)?

14. **Mock API update** — `lib/mock-api.ts` needs delivery endpoints for frontend dev without backend. Is the frontend developer (you?) going to build the frontend with mocks first, or backend-first with curl testing?

---

## Scope Reduction (If Needed)

15. **Smallest useful slice?** If you wanted to ship something faster:
    - Backend only (models + endpoints + tests) — frontend keeps the textarea temporarily?
    - Single courier first (e.g., Econt only, add Speedy later)?
    - Door delivery only (no office picker, which is the complex UI)?

16. **Office picker is the hardest UI piece.** City search → filtered list → selection → confirmation card. That's autocomplete + list + detail in one component. Is there a component library already in use that has a combobox/autocomplete? Or is this from scratch?

---

## Resolved: Office Data Source

Both couriers have official APIs for fetching office lists. No scraping needed.

### Econt — Nomenclatures API
- **Test:** `POST https://demo.econt.com/ee/services/Nomenclatures/NomenclaturesService.getOffices`
- **Prod:** `POST https://ee.econt.com/services/...`
- **Auth:** HTTP Basic. Test creds: `iasp-dev` / `1Asp-dev`. Prod: e-econt account (will create).
- **Returns:** All offices with id, name, city, address, working hours.

### Speedy — Location API
- **Endpoint:** `POST https://api.speedy.bg/v1/location/office`
- **Auth:** `userName` + `password` in JSON body.
- **Params:** `countryId`, `siteId`, `siteName`, `name`, `limit` (omit = all).
- **Returns:** `{ offices: Office[] }` — includes type: `"OFFICE"` (staffed) or `"APT"` (lockers/автомати).
- **Prod:** Speedy business account (will create).

### Decisions
- ✅ Lockers (APT) included — customers can pick offices OR автомати.
- ✅ Will create accounts for both Econt and Speedy.
- MVP approach: one-off fetch script → JSON files. Upgrade to nightly sync later.

### Impact on Design
- The `DeliveryOffice` model may want a `type: Literal["office", "apt"]` field so the UI can show a locker icon vs office icon.
- Office picker UI could have a toggle/filter: "Офиси" / "Автомати" / "Всички".
- The `data/*.json` schema gains a `type` field.

---

## Future Considerations (Not Blockers)

- Shipping cost calculation — currently "flat rate or free." When does this become real?
- Courier tracking integration — how far out?
- What happens when a customer places an order and the office closes the next day? Is the courier's office_id stable enough to use as a reference?
- Nightly sync script using the same API endpoints (trivial upgrade from the one-off fetch script).
