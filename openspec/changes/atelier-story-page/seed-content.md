# Seed Content — Atelier Story Page (EN + BG)

The exact English copy plus a **drafted Bulgarian translation**. This is the source for the `app/database.py` seed. The owner should review the Bulgarian here (or in the admin UI) before launch. All `*_bg` are nullable — anything cleared falls back to English.

**Brand name** "The Atelier Marie" is kept in Latin in both languages.
**Images**: seeded as `NULL` (placeholder shown until the owner uploads).
`\n\n` marks a paragraph break in `body_*` fields.

---

## 1. `hero` — type `hero`

| Field | EN | BG |
|---|---|---|
| heading | The Atelier Marie | The Atelier Marie |
| subheading | Handcrafted Elegance for Beautiful Spaces | Ръчно изработена елегантност за красиви пространства |
| cta_label | Explore our collection | Разгледайте нашата колекция |
| cta_href | `/products` | `/products` |

**body_en:**
> At The Atelier Marie, we create handcrafted candles designed to bring beauty, warmth, and a touch of luxury into your home.
>
> Inspired by the elegance of decorative objects, each creation is thoughtfully designed and carefully made in our atelier. From delicate floral arrangements to sculptural designs and personalised pieces, every candle reflects a passion for artistry, detail, and timeless aesthetics.
>
> More than a candle, each creation is a small piece of décor — made to enhance your space, celebrate meaningful moments, and become part of the memories you cherish.

**body_bg:**
> В The Atelier Marie създаваме ръчно изработени свещи, замислени да внесат красота, топлина и лек досег на лукс във вашия дом.
>
> Вдъхновено от елегантността на декоративните предмети, всяко творение е обмислено с внимание и изработено грижливо в нашето ателие. От нежни флорални аранжировки до скулптурни форми и персонализирани изделия — всяка свещ отразява страст към майсторството, детайла и вечната естетика.
>
> Повече от свещ, всяко творение е малко парче декор — създадено да разкраси вашето пространство, да отбележи значими мигове и да стане част от спомените, които пазите.

---

## 2. `story` — type `text_image`

| Field | EN | BG |
|---|---|---|
| heading | Our Story | Нашата история |
| subheading | From a Creative Idea to a Handmade Atelier | От творческа идея до ръчно ателие |

**body_en:**
> The Atelier Marie began with a simple thought: *"I want something this beautiful in my own home."*
>
> Inspired by the beauty of decorative candles, the journey started with creating pieces purely out of curiosity and a desire to bring something unique into everyday spaces.
>
> What began as a creative hobby slowly became a passion for designing, experimenting, and creating beautiful objects by hand. Each candle became an opportunity to explore shapes, colours, textures, and fragrances while creating something truly special.
>
> Over time, this passion grew into The Atelier Marie — a place where creativity, craftsmanship, and elegance come together to create candles designed to be enjoyed, admired, and remembered.

**body_bg:**
> The Atelier Marie започна с една проста мисъл: *„Искам нещо толкова красиво в собствения си дом.“*
>
> Вдъхновено от красотата на декоративните свещи, пътуването започна със създаването на изделия единствено от любопитство и от желание да внесем нещо уникално в ежедневните пространства.
>
> Това, което започна като творческо хоби, постепенно се превърна в страст към проектирането, експериментирането и създаването на красиви предмети на ръка. Всяка свещ се превръщаше във възможност да изследваме форми, цветове, текстури и аромати, докато създаваме нещо наистина специално.
>
> С времето тази страст прерасна в The Atelier Marie — място, където творчеството, майсторството и елегантността се срещат, за да създадат свещи, замислени да бъдат изживени, ценени и помнени.

---

## 3. `philosophy` — type `text_band`

| Field | EN | BG |
|---|---|---|
| heading | Our Philosophy | Нашата философия |
| subheading | Candles Designed to Be Admired | Свещи, създадени, за да им се възхищавате |

**body_en:**
> We believe candles can be more than a source of light or fragrance.
>
> They can become decorative pieces that add character, warmth, and beauty to a space. They can transform a room, create an atmosphere, and become part of meaningful moments.
>
> At The Atelier Marie, every creation is designed with the intention of bringing together artistic expression, luxurious fragrance, and thoughtful craftsmanship.
>
> Some pieces are created to be enjoyed through their scent and flame, while others are designed purely as decorative objects to be admired as part of your home.
>
> Every candle is made to bring a little more beauty into everyday life.

**body_bg:**
> Вярваме, че свещите могат да бъдат повече от източник на светлина или аромат.
>
> Те могат да се превърнат в декоративни предмети, които придават характер, топлина и красота на пространството. Могат да преобразят стаята, да създадат атмосфера и да станат част от значими мигове.
>
> В The Atelier Marie всяко творение е замислено с намерението да обедини артистичен изказ, луксозен аромат и премислено майсторство.
>
> Някои изделия са създадени, за да бъдат изживени чрез своя аромат и пламък, а други са замислени единствено като декоративни предмети, на които да се възхищавате като част от вашия дом.
>
> Всяка свещ е направена, за да внесе малко повече красота в ежедневието.

---

## 4. `differentiators` — type `cards`

| Field | EN | BG |
|---|---|---|
| heading | What Makes Our Candles Different | Какво отличава нашите свещи |
| subheading | More Than a Candle — A Piece of Art for Your Home | Повече от свещ — произведение на изкуството за вашия дом |

**Items** (no images):

| # | title_en / title_bg | text_en / text_bg |
|---|---|---|
| 1 | Handcrafted With Attention to Detail / Ръчна изработка с внимание към детайла | Every candle is individually created in our atelier. From the first design idea to the final finishing touches, every element is carefully considered. / Всяка свещ се създава индивидуално в нашето ателие. От първата идея за дизайна до последните завършващи щрихи — всеки елемент е обмислен внимателно. |
| 2 | Designed as Home Décor / Замислени като декор за дома | Our candles are created to complement beautiful interiors and become part of your space. Whether displayed as a statement piece or enjoyed as a sensory experience, each design is made to bring elegance and personality into your home. / Нашите свещи са създадени да допълват красивите интериори и да станат част от вашето пространство. Независимо дали като акцентен детайл, или като сетивно изживяване, всеки дизайн внася елегантност и характер във вашия дом. |
| 3 | A Luxury Fragrance Experience / Луксозно ароматно изживяване | Beautiful design deserves a beautiful scent. Our fragrances are carefully selected to create a warm and memorable atmosphere, turning everyday moments into something special. / Красивият дизайн заслужава красив аромат. Нашите аромати са внимателно подбрани, за да създадат топла и запомняща се атмосфера, превръщайки ежедневните мигове в нещо специално. |
| 4 | Personalised Creations / Персонализирани творения | Some moments deserve something truly unique. We offer personalised designs, candle bouquets, and colour combinations for those looking for a meaningful piece created especially for them. / Някои мигове заслужават нещо наистина уникално. Предлагаме персонализирани дизайни, букети от свещи и цветови комбинации за тези, които търсят значимо изделие, създадено специално за тях. |

---

## 5. `process` — type `timeline`

| Field | EN | BG |
|---|---|---|
| heading | The Art of Making | Изкуството на създаването |
| subheading | Crafted Slowly, Made With Care | Изработени бавно, създадени с грижа |

**body_en (intro above the timeline):**
> Every creation begins with an idea.
>
> Before a candle reaches your home, it goes through a careful process of design and craftsmanship. Shapes are considered, moulds are prepared, colours are carefully selected, and every decorative element is thoughtfully arranged.
>
> Each piece is handcrafted through multiple stages, including pouring, shaping, adding details by hand, and allowing the candle time to properly set and develop its final appearance.
>
> Some candles are created in small batches, while others are individually made as unique pieces.
>
> Because every detail is created with patience and care, the process often takes several days. This allows us to focus on quality, beauty, and the small details that make each candle special.
>
> Behind every candle is time, creativity, and a love for handmade design.

**body_bg:**
> Всяко творение започва с идея.
>
> Преди една свещ да стигне до вашия дом, тя преминава през внимателен процес на проектиране и изработка. Обмислят се формите, подготвят се калъпите, грижливо се подбират цветовете и всеки декоративен елемент се подрежда с внимание.
>
> Всяко изделие се изработва на ръка през множество етапи — включително отливане, оформяне, добавяне на детайли на ръка и оставяне на свещта да се стегне правилно и да придобие своя завършен вид.
>
> Някои свещи се създават в малки серии, а други се изработват индивидуално като уникални изделия.
>
> Тъй като всеки детайл се създава с търпение и грижа, процесът често отнема няколко дни. Това ни позволява да се съсредоточим върху качеството, красотата и малките детайли, които правят всяка свещ специална.
>
> Зад всяка свещ стоят време, творчество и любов към ръчния дизайн.

**Steps** (each has an image field, seeded `NULL`):

| # | title_en / title_bg | text_en / text_bg |
|---|---|---|
| 1 | Design / Дизайн | Every creation begins with an idea, a shape, and a vision. / Всяко творение започва с идея, форма и визия. |
| 2 | Moulds / Калъпи | Each shape is carefully prepared so the candle can take its intended form. / Всяка форма се подготвя грижливо, за да може свещта да приеме замисления си вид. |
| 3 | Colours / Цветове | Shades are selected and blended by hand to achieve the perfect tone. / Нюансите се подбират и смесват на ръка, за да се постигне съвършеният тон. |
| 4 | Handmade Details / Ръчни детайли | Every decorative element is carefully placed by hand. / Всеки декоративен елемент се поставя внимателно на ръка. |
| 5 | Setting / Стягане | Each candle is given time to set properly and develop its final appearance. / На всяка свещ се дава време да се стегне правилно и да придобие завършения си вид. |
| 6 | Finishing & Packaging / Завършек и опаковане | Each candle receives time and attention before leaving the atelier. / Всяка свещ получава време и внимание, преди да напусне ателието. |

---

## 6. `atelier` — type `text_image` (full-width image)

| Field | EN | BG |
|---|---|---|
| heading | Inside Our Atelier | Вътре в нашето ателие |
| subheading | Where Every Candle Comes to Life | Където всяка свещ оживява |

**body_en:**
> Behind every creation are countless small details.
>
> Inside our atelier, each candle is carefully brought to life by hand. From preparing materials and creating unique designs to adding decorative elements and finishing every piece, each stage receives individual attention.
>
> Our hands are involved in every step of the process, allowing us to create candles that feel personal, distinctive, and unlike mass-produced alternatives.
>
> Through small-batch creations and individually made pieces, The Atelier Marie celebrates the beauty of craftsmanship and the charm of handmade design.
>
> Every candle carries a little part of the process that created it.

**body_bg:**
> Зад всяко творение стоят безброй малки детайли.
>
> В нашето ателие всяка свещ се създава грижливо на ръка. От подготовката на материалите и създаването на уникални дизайни до добавянето на декоративни елементи и завършването на всяко изделие — всеки етап получава индивидуално внимание.
>
> Нашите ръце участват във всяка стъпка от процеса, което ни позволява да създаваме свещи, които усещате като лични, отличителни и различни от масово произвежданите алтернативи.
>
> Чрез творения в малки серии и индивидуално изработени изделия, The Atelier Marie възхвалява красотата на майсторството и очарованието на ръчния дизайн.
>
> Всяка свещ носи малка част от процеса, който я е създал.

---

## 7. `values` — type `cards`

| Field | EN | BG |
|---|---|---|
| heading | Our Values | Нашите ценности |
| subheading | The Principles Behind Every Creation | Принципите зад всяко творение |

**Items** (no images):

| # | title_en / title_bg | text_en / text_bg |
|---|---|---|
| 1 | Craftsmanship / Майсторство | True beauty comes from attention to detail. We believe every element matters, from the overall design to the smallest finishing touch. / Истинската красота идва от вниманието към детайла. Вярваме, че всеки елемент има значение — от цялостния дизайн до най-малкия завършващ щрих. |
| 2 | Elegance / Елегантност | Our creations are inspired by timeless aesthetics, designed to complement your home and bring a refined sense of beauty to your surroundings. / Нашите творения са вдъхновени от вечната естетика, замислени да допълват вашия дом и да внесат изтънчено усещане за красота в заобикалящата ви среда. |
| 3 | Emotion / Емоция | The most meaningful objects are those connected to memories. Whether chosen for yourself or gifted to someone special, our candles are created to celebrate moments worth remembering. / Най-значимите предмети са тези, свързани със спомени. Независимо дали са избрани за вас, или подарени на някого специален, нашите свещи са създадени да отбележат мигове, които си заслужава да бъдат помнени. |
| 4 | Personal Touch / Личен досег | Every home and every occasion is unique. Through personalised creations, we aim to create pieces that feel truly yours. / Всеки дом и всеки повод са уникални. Чрез персонализирани творения се стремим да създаваме изделия, които усещате като истински ваши. |

---

## 8. `collections` — type `collections`  *(drafted — no source copy)*

| Field | EN | BG |
|---|---|---|
| heading | Our Collections | Нашите колекции |
| subheading | Designed to Suit Every Space and Story | Създадени да подхождат на всяко пространство и история |

**Tiles** (each has an image field, seeded `NULL`; `link_href` is a **draft** — confirm against `dynamic-categories` slugs):

| # | title_en / title_bg | text_en / text_bg | link_href |
|---|---|---|---|
| 1 | Floral Collection / Флорална колекция | Romantic designs inspired by nature. / Романтични дизайни, вдъхновени от природата. | `/products?category=floral` |
| 2 | Sculptural Collection / Скулптурна колекция | Statement pieces designed to decorate your space. / Акцентни изделия, създадени да украсят вашето пространство. | `/products?category=sculptural` |
| 3 | Bespoke Collection / Колекция по поръчка | Custom creations made for meaningful moments. / Творения по поръчка за значими мигове. | `/products?category=bespoke` |

---

## 9. `emotional` — type `text_band` (soft background)

| Field | EN | BG |
|---|---|---|
| heading | A Little Beauty for Everyday Moments | Малко красота за ежедневните мигове |
| subheading | Designed to Become Part of Your Story | Създадени да станат част от вашата история |
| cta_label | Discover the collection | Открийте колекцията |
| cta_href | `/products` | `/products` |

**body_en:**
> We believe the most beautiful objects are the ones that create a feeling.
>
> A candle can transform a room, add warmth to your home, and become part of the moments you want to remember.
>
> Whether chosen as a statement piece for your own space or as a meaningful gift for someone special, every creation from The Atelier Marie is designed to bring elegance, beauty, and emotion into everyday life.
>
> From the first idea to the final detail, each candle is made with care so it can become more than decoration — it can become a small reminder of a beautiful moment.

**body_bg:**
> Вярваме, че най-красивите предмети са тези, които създават усещане.
>
> Една свещ може да преобрази стаята, да добави топлина към вашия дом и да стане част от миговете, които искате да запомните.
>
> Независимо дали е избрана като акцентно изделие за собственото ви пространство, или като значим подарък за някого специален — всяко творение от The Atelier Marie е замислено да внесе елегантност, красота и емоция в ежедневието.
>
> От първата идея до последния детайл, всяка свещ е изработена с грижа, за да може да стане повече от декорация — да се превърне в малко напомняне за един красив миг.

---

## 10. `custom_cta` — type `cta_band`  *(drafted — no source copy)*

| Field | EN | BG |
|---|---|---|
| heading | Looking for Something Unique? | Търсите нещо уникално? |
| cta_label | Request a Custom Order | Заявете индивидуална поръчка |
| cta_href | `/contact` *(placeholder — point at bespoke flow when it exists)* | `/contact` |

**body_en:**
> Create a personalised candle designed especially for you — a bespoke piece for a meaningful moment, or a truly one-of-a-kind gift.

**body_bg:**
> Създайте персонализирана свещ, замислена специално за вас — изделие по поръчка за значим миг или наистина уникален подарък.

---

### Seed order (`sort_order`)

`hero(0) → story(1) → philosophy(2) → differentiators(3) → process(4) → atelier(5) → values(6) → collections(7) → emotional(8) → custom_cta(9)`

All sections seed `is_published = 1`.
