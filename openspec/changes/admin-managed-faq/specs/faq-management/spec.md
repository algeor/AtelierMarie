## ADDED Requirements

### Requirement: FAQ sections storage

The system SHALL persist FAQ sections in a `faq_sections` table keyed by a stable `slug`, with a required `title_en`, optional `title_bg`, an `icon`, `sort_order`, and `created_at`/`updated_at` timestamps. Section slugs SHALL be stable and are used as page anchors; the seeded slugs are `candles`, `care`, `custom`, and `shipping`.

#### Scenario: Sections seeded with stable slugs
- **WHEN** the database is initialized and `faq_sections` is empty
- **THEN** four rows exist with slugs `candles`, `care`, `custom`, `shipping`, each with a non-null `title_en`, an `icon`, and an ascending `sort_order`

#### Scenario: Section slug is immutable
- **WHEN** an admin edits a section
- **THEN** `title_en`, `title_bg`, `icon`, and `sort_order` MAY change but `slug` SHALL NOT change

### Requirement: FAQ items storage

The system SHALL persist FAQ entries in a `faq_items` table with `id`, a `section` referencing `faq_sections(slug)`, required `question_en` and `answer_en`, optional `question_bg` and `answer_bg`, `sort_order`, `is_published` (default 1), and `created_at`/`updated_at` timestamps.

#### Scenario: Item belongs to a section
- **WHEN** an FAQ item is created with `section = "care"`
- **THEN** the row is stored with `section = "care"` and is retrievable ordered by `sort_order` within that section

#### Scenario: English content is required
- **WHEN** an FAQ item is created without `question_en` or without `answer_en`
- **THEN** the system SHALL reject the request with a validation error

### Requirement: Bilingual locale resolution with fallback

The system SHALL resolve localized FAQ text using the requested locale, falling back to English when the Bulgarian value is absent: `en` resolves to the `*_en` value; `bg` resolves to `COALESCE(*_bg, *_en)`. This applies to section titles and to item questions and answers.

#### Scenario: Bulgarian value present
- **WHEN** content is requested with `locale = bg` and `title_bg` is non-null
- **THEN** the system SHALL return `title_bg`

#### Scenario: Bulgarian value missing
- **WHEN** content is requested with `locale = bg` and `answer_bg` is null
- **THEN** the system SHALL return `answer_en`

### Requirement: FAQ content stored raw, escaped at render

FAQ questions and answers are authored by admins (behind `require_admin`) and SHALL be stored as **raw plain text with newlines preserved**. The system SHALL NOT HTML-escape FAQ content on write (unlike anonymous comment/display-name input), so display text is never double-encoded. XSS safety SHALL be provided at render: the frontend relies on React's automatic text escaping, and JSON-LD SHALL be emitted via safe serialization.

#### Scenario: Punctuation preserved verbatim
- **WHEN** an admin saves an answer containing apostrophes, ampersands, or em dashes (e.g. "we'd", "Care & Safety", "home fragrance—more")
- **THEN** the stored value retains those characters unchanged and they render as-is (never as `&#x27;`, `&amp;`, or `&mdash;`)

#### Scenario: Newlines and bullet markers preserved
- **WHEN** an answer contains blank-line-separated paragraphs and lines beginning with `* ` or `- `
- **THEN** those characters are preserved in storage so the renderer can format paragraphs and bullet lists

#### Scenario: Script markup is inert at render
- **WHEN** an answer contains `<script>` or other HTML markup
- **THEN** it is displayed as inert text via React's escaping and is never injected as live HTML, and it is safely serialized inside the JSON-LD block

### Requirement: Seeded initial FAQ content

The system SHALL insert the four sections and all initial FAQ items with the exact approved English copy and a Bulgarian draft via a marker-guarded one-time migration that runs exactly once. Re-running initialization SHALL be a no-op, and edits or deletions of seeded rows SHALL NOT be re-created on later startups.

#### Scenario: Seed populates on first run
- **WHEN** the seed migration runs for the first time
- **THEN** the four sections and all items from the seed content (see Appendix) are inserted with `is_published = 1`

#### Scenario: Seed runs only once
- **WHEN** initialization runs again after the seed migration has already completed
- **THEN** no seed rows are inserted or modified, even if some seeded rows were edited or deleted

### Requirement: Timestamp maintenance

Each table SHALL default `created_at` and `updated_at` to `datetime('now')`, and `updated_at` SHALL be refreshed automatically on row update via an `AFTER UPDATE` trigger (matching the existing `products_updated_at` convention), not by service code.

#### Scenario: updated_at advances on edit
- **WHEN** a row in `faq_items` is updated
- **THEN** its `updated_at` reflects the modification time without the service explicitly setting it

---

## Appendix: Seed Content (EN + BG draft for owner review)

> Bulgarian below is a **draft for review**. `*_bg` fields are nullable, so any unreviewed text can be cleared and the page will fall back to English.

**Page intro (chrome — lives in `messages/*.json`, shown here for context):**
- EN: "Have a question? You may find the answer below. If not, we'd love to hear from you. Simply get in touch through our Contact Form, and we'll be happy to help."
- BG: "Имате въпрос? Възможно е да намерите отговора по-долу. Ако не — ще се радваме да се свържете с нас. Просто ни пишете чрез нашата форма за контакт и с удоволствие ще ви помогнем."

### Section: candles — 🕯 "About Our Candles" / "За нашите свещи"

**Are your candles handmade? / Ръчно изработени ли са вашите свещи?**
- EN: Yes. Every candle is lovingly handcrafted in our atelier, making each piece truly one of a kind. Because they are made by hand, slight variations in colour, finish, or decorative details are part of their unique charm.
- BG: Да. Всяка свещ е изработена с любов на ръка в нашето ателие, което прави всяко изделие наистина уникално. Тъй като са изработени ръчно, леките разлики в цвета, финиша или декоративните детайли са част от техния неповторим чар.

**What wax do you use? / Какъв восък използвате?**
- EN: We carefully select different premium wax blends depending on the candle's design and intended performance. The exact wax type used for each candle is listed in its individual product description.
- BG: Внимателно подбираме различни висококачествени восъчни смеси в зависимост от дизайна и предназначението на свещта. Точният вид восък за всяка свещ е посочен в описанието на съответния продукт.

**What type of wick do you use? / Какъв вид фитил използвате?**
- EN: We use different wick types depending on the candle's size and design to ensure the best possible performance. The wick information for each candle can be found on its product page.
- BG: Използваме различни видове фитили в зависимост от размера и дизайна на свещта, за да осигурим възможно най-добро горене. Информация за фитила на всяка свещ можете да намерите на нейната продуктова страница.

**Where are your candles made? / Къде се произвеждат вашите свещи?**
- EN: All of our candles are handcrafted in our atelier with great attention to detail and quality.
- BG: Всички наши свещи са изработени ръчно в нашето ателие с изключително внимание към детайла и качеството.

**What sizes do you offer? / Какви размери предлагате?**
- EN: Our collection includes candles in a variety of sizes. Please refer to each product page for the exact dimensions and weight.
- BG: Нашата колекция включва свещи в различни размери. Моля, вижте всяка продуктова страница за точните размери и тегло.

**What makes your candles different? / Какво отличава вашите свещи?**
- EN: Our candles are designed to be more than just home fragrance—they're decorative pieces made to elevate your space. Combining handcrafted craftsmanship, luxurious fragrances, elegant designs, and premium materials, each candle is created to bring beauty and warmth into your home. Many of our products can also be customised, making them a thoughtful and unique gift.
- BG: Нашите свещи са замислени да бъдат нещо повече от аромат за дома — те са декоративни изделия, създадени да облагородят пространството ви. Съчетавайки ръчна изработка, изискани аромати, елегантен дизайн и първокласни материали, всяка свещ е създадена да внесе красота и топлина в дома ви. Много от нашите продукти могат да бъдат персонализирани, което ги прави обмислен и уникален подарък.

### Section: care — ✨ "Candle Care & Safety" / "Грижа и безопасност"

**Are all of your candles meant to be burned? / Всички ваши свещи ли са предназначени за горене?**
- EN: Not necessarily. Some of our candles are designed primarily as decorative pieces, while others are suitable for burning. Please check the product description before lighting your candle.
- BG: Не непременно. Някои от нашите свещи са създадени предимно като декоративни изделия, докато други са подходящи за горене. Моля, проверете описанието на продукта, преди да запалите свещта си.

**Do I need to trim the wick before the first burn? / Трябва ли да подрязвам фитила преди първото горене?**
- EN: No. Every candle arrives with the wick pre-trimmed and ready to light. If you burn your candle multiple times, trimming the wick before each subsequent burn will help maintain a cleaner flame.
- BG: Не. Всяка свещ пристига с предварително подрязан фитил, готова за палене. Ако горите свещта многократно, подрязването на фитила преди всяко следващо палене ще помогне за по-чист пламък.

**How long should I burn my candle? / Колко дълго да горя свещта си?**
- EN: Recommended burn times vary depending on the candle's size and design. Please refer to the individual product description for guidance.
- BG: Препоръчителното време за горене варира в зависимост от размера и дизайна на свещта. Моля, вижте описанието на съответния продукт за насоки.

**Will decorative candles drip? / Капят ли декоративните свещи?**
- EN: Yes. Sculptural candles and decorative designs naturally lose their shape as they burn and may drip wax. Always place them on a heat-resistant tray or dish large enough to catch any melted wax.
- BG: Да. Скулптурните свещи и декоративните дизайни естествено губят формата си при горене и могат да капят восък. Винаги ги поставяйте върху топлоустойчива подложка или чиния, достатъчно голяма да събере разтопения восък.

**How should I display decorative candles? / Как да излагам декоративните свещи?**
- EN: To preserve their appearance, keep decorative candles away from direct sunlight, radiators, or other heat sources. Prolonged exposure may cause colours to fade or change over time.
- BG: За да запазите външния им вид, дръжте декоративните свещи далеч от пряка слънчева светлина, радиатори и други източници на топлина. Продължителното излагане може да доведе до избледняване или промяна на цветовете с времето.

**Will my candle look exactly like the photos? / Ще изглежда ли свещта ми точно като на снимките?**
- EN: We do our best to ensure every candle closely matches the product photos. Because each piece is handmade, small variations in decorative elements—such as fruit toppings or other handcrafted details—may occur. These slight differences make every candle unique while maintaining the same overall design and colour palette.
- BG: Правим всичко възможно всяка свещ да съответства максимално на продуктовите снимки. Тъй като всяко изделие е ръчно изработено, възможни са малки разлики в декоративните елементи — като плодови акценти или други ръчно изработени детайли. Тези леки разлики правят всяка свещ уникална, като запазват същия цялостен дизайн и цветова палитра.

**Candle Safety / Безопасност при работа със свещи** (bulleted answer)
- EN:
  * Never leave a burning candle unattended.
  * Keep candles away from children and pets.
  * Always burn candles on a stable, heat-resistant surface.
  * Keep away from curtains, furniture, and other flammable materials.
  * Never move a candle while it is burning or while the wax is still hot.
  * Extinguish the candle before it burns completely.
- BG:
  * Никога не оставяйте горяща свещ без надзор.
  * Дръжте свещите далеч от деца и домашни любимци.
  * Винаги горете свещите върху стабилна, топлоустойчива повърхност.
  * Дръжте далеч от завеси, мебели и други запалими материали.
  * Никога не местете свещ, докато гори или докато восъкът е още горещ.
  * Изгасете свещта, преди да изгори напълно.

### Section: custom — 🎁 "Custom Orders & Gifts" / "Поръчки по заявка и подаръци"

**Can I customise my candle? / Мога ли да персонализирам свещта си?**
- EN: Yes. We love bringing our customers' ideas to life. If you have a specific design, colour palette, fragrance, or occasion in mind, we'd be delighted to discuss a custom order.
- BG: Да. Обичаме да претворяваме идеите на нашите клиенти. Ако имате конкретен дизайн, цветова палитра, аромат или повод предвид, с удоволствие ще обсъдим поръчка по заявка.

**Can I request a custom candle bouquet? / Мога ли да поръчам персонализиран букет от свещи?**
- EN: Absolutely. We create personalised candle bouquets and custom colour palettes for birthdays, weddings, anniversaries, baby showers, corporate gifts, and many other special occasions.
- BG: Разбира се. Създаваме персонализирани букети от свещи и индивидуални цветови палитри за рождени дни, сватби, годишнини, бебешки партита, корпоративни подаръци и много други специални поводи.

**Can I include a gift message? / Мога ли да добавя подаръчно съобщение?**
- EN: Of course. Simply leave a note with your order and send your gift message through our Contact Form. We'll include it with your order.
- BG: Разбира се. Просто оставете бележка към поръчката си и изпратете подаръчното съобщение чрез нашата форма за контакт. Ще го приложим към поръчката ви.

**Are your candles suitable as gifts? / Подходящи ли са вашите свещи за подарък?**
- EN: Yes. Every candle is beautifully presented in our custom gift-ready packaging, making it perfect for gifting without the need for additional wrapping.
- BG: Да. Всяка свещ е красиво представена в нашата специална подаръчна опаковка, което я прави идеална за подарък без нужда от допълнително опаковане.

### Section: shipping — 📦 "Orders, Shipping & Returns" / "Поръчки, доставка и връщане"

**How long does it take to prepare my order? / Колко време отнема подготовката на поръчката ми?**
- EN: Preparation times vary depending on the product and whether it is made to order. Estimated processing times are displayed on each product page and during checkout.
- BG: Времето за подготовка варира в зависимост от продукта и дали е изработван по заявка. Ориентировъчните срокове за обработка са посочени на всяка продуктова страница и при плащане.

**Can I change or cancel my order? / Мога ли да променя или отменя поръчката си?**
- EN: If your order has not yet entered production or been dispatched, we'll do our very best to accommodate your request. Please contact us as soon as possible.
- BG: Ако поръчката ви все още не е влязла в производство или не е изпратена, ще направим всичко възможно да удовлетворим молбата ви. Моля, свържете се с нас възможно най-скоро.

**What should I do if my order arrives damaged? / Какво да направя, ако поръчката ми пристигне повредена?**
- EN: We take great care when packaging every order, but if your item arrives damaged, please contact us as soon as possible through our Contact Form or by email. Include your order number along with clear photos of the item and its packaging so we can resolve the issue promptly.
- BG: Опаковаме всяка поръчка с изключително внимание, но ако изделието ви пристигне повредено, моля, свържете се с нас възможно най-скоро чрез нашата форма за контакт или по имейл. Приложете номера на поръчката си заедно с ясни снимки на изделието и опаковката, за да разрешим проблема бързо.

**Do you accept returns? / Приемате ли връщания?**
- EN: Please refer to our Returns & Refunds Policy for full details regarding returns, exchanges, and personalised items.
- BG: Моля, вижте нашата Политика за връщане и възстановяване на суми за пълна информация относно връщания, замени и персонализирани изделия.

**How can I contact you? / Как мога да се свържа с вас?**
- EN: You can contact us anytime through our Contact Form or by email. We aim to respond to all enquiries as quickly as possible.
- BG: Можете да се свържете с нас по всяко време чрез нашата форма за контакт или по имейл. Стремим се да отговаряме на всички запитвания възможно най-бързо.

**Contact banner (chrome — `messages/*.json`): "Still have a question?" / "Все още имате въпрос?"**
- EN: If you couldn't find the answer you were looking for, we're always happy to help. Get in touch through our Contact Form, and we'll get back to you as soon as we can.
- BG: Ако не сте открили отговора, който търсите, винаги сме насреща да помогнем. Свържете се с нас чрез нашата форма за контакт и ще ви отговорим възможно най-скоро.
