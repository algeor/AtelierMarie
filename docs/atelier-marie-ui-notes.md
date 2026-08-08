# Atelier Marie UI Notes

## Scope

- Whole Atelier Marie website

## Rebrand Context

- We are rebranding the Atelier Marie website.
- Use this file as the running notes source for UI, brand, visual direction, references, and implementation decisions.

## Hard Rebrand Rule: Preserve Existing Functionality

- The rebrand must not remove, hide, or break any already exposed functionality.
- Existing public and admin features must remain available after visual redesign work.
- Rebranding is a visual/UX improvement, not a feature reduction.
- When simplifying layouts, do not remove actions, links, states, settings, forms, filters, admin tools, checkout steps, account flows, product details, legal pages, or support paths that already exist.
- If a feature needs to move for better UX, it must still be findable and usable.
- If there is any doubt whether something is actively used, preserve it until confirmed otherwise.
- Before implementation, audit existing pages/components/routes and map current functionality to the new design.
- After implementation, verify that the same workflows still work.

### Preserve Especially

- Product browsing, filtering, sorting, search, product detail pages, media/gallery, comments/reactions, product safety/details, add-to-cart.
- Cart, checkout, delivery/courier choices, payment flows, order confirmation, retry payment, order history, account pages, login/logout.
- Contact, FAQ, Atelier/About, Terms, Privacy, Cookies, cookie settings, language toggle, social links.
- Admin products, orders, inventory, accounting, analytics, FAQ/content management, legal/privacy/cookie/terms management, delivery/courier settings, promotions, payment settings.
- Loading, empty, error, not-found, low-stock, out-of-stock, validation, and success states.

### Rebrand QA Requirement

- Every rebrand implementation pass should include a functionality preservation check.
- Visual changes must be tested on mobile and desktop.
- Focus states, keyboard access, reduced motion, and readable contrast must remain intact.

## Desired Feel

- Romantic
- Soft
- Elegant
- Warm
- Handmade / boutique

## Avoid

- Corporate
- Childish
- Too loud

## Leading Colors

### Blush / Rose

- Soft Blush: `#ECC6C6`
- Coral Dream: `#F0CCD0`
- Muted Rose: `#DBAAAC`

### Mauve / Clay

- Vintage Mauve: `#C28E8D`
- Dusty Terra: `#B27474`
- Warm Clay: `#A15958`

### Neutrals

- Soft off-white: `#EEEFE9`
- Warm cream: `#E7D9CC`
- Sand taupe: `#BBA58E`

### Depth / Contrast

- Sage: `#959D90`
- Dark brown: `#513D34`
- Deep green-black: `#223030`

## Color Customization Direction

- Make the color palette easy to customize during implementation.
- Use central design tokens / CSS variables for brand colors instead of hardcoding colors inside components.
- Components should reference semantic tokens like background, surface, text, muted text, border, primary action, secondary action, accent, success, warning, and error.
- Keep palette values in one obvious place so the brand colors can be adjusted without hunting through the app.
- Public storefront and admin can share the same base palette, but admin should use quieter token choices.
- Avoid one-off Tailwind hex values or inline color styles unless there is a strong reason.
- Document token names clearly so future updates are simple.
- Any palette change must preserve readable contrast, focus states, hover states, disabled states, and reduced-motion fallbacks.
- Rebrand QA should include a quick scan for hardcoded colors after major visual changes.

## Working Direction

- Use soft neutral backgrounds.
- Use blush and rose as the main brand warmth.
- Use clay tones for important accents.
- Use deep green-black for text, navigation, and strong contrast.
- Keep the site elegant and boutique, not playful or corporate.

## Mobile-First Direction

- Design mobile first, then adapt upward for tablet and desktop.
- The landing page should be vertically scrollable and feel natural on a phone.
- Key animation should be driven by vertical scroll, not hover or desktop-only gestures.
- Keep each mobile scroll step focused: hero, story, featured product, collections.
- Avoid heavy pinned sections that trap or fight mobile scrolling.
- Keep CTAs easy to reach and tap.
- All motion needs a reduced-motion fallback.

## Utility Pages: 404 And Error States

### 404 Page Reference

- Source: `https://dribbble.com/shots/24031702-Premium-Attire-Ecommerce-Shop-Website-404-Page-Design`
- Reviewed: 2026-08-02
- Use as inspiration for the mood and composition only. Do not copy the fashion brand, exact layout, images, or text styling.

### What The 404 Reference Shows

- A dedicated editorial 404 page, not a plain browser-style error screen.
- Large `404` number in elegant serif typography.
- Huge `NOT FOUND` headline across the bottom.
- Cream / ivory content panel over a dark, muted photographic background.
- Small top navigation with logo, menu, search, wishlist, journal, profile, and bag.
- A small `ERROR` label in bright red on the right.
- A centered `BACK TO HOME` link with a small arrow.
- A small lifestyle/product thumbnail adds visual detail without crowding the page.
- The whole page feels premium, minimal, editorial, and intentional.

### Atelier Marie 404 Direction

- Create a dedicated branded 404 page.
- Use oversized elegant serif typography for `404` and `Not Found`.
- Use Atelier Marie colors instead of the reference palette:
  - Background/panel: `#EEEFE9` or `#E7D9CC`
  - Main large text: `#B27474`, `#A15958`, or `#513D34`
  - Body/nav text: `#223030`
  - Small warning/accent: clay/rose, not harsh red
- Add a soft product or atelier lifestyle image in the background or as a small accent.
- Keep the page romantic and boutique, but slightly quieter than the homepage.
- Primary action: `Back to Home`.
- Optional secondary action: `Browse Shop`, only if it does not clutter the layout.
- On mobile, stack the content clearly:
  - `404`
  - `Not Found`
  - short friendly line
  - `Back to Home` CTA
  - small image/accent
- Make sure the CTA is visible without needing a long scroll.

### Generic Error Page Direction

- Create a separate generic error page for unexpected failures.
- Tone should be calm and useful, not dramatic.
- Main message: `Something went wrong.`
- Primary action: `Back to Home`.
- Optional secondary action: `Try Again`, only where retrying makes sense.
- Do not show technical stack traces or scary system wording to shoppers.
- Keep the design related to the 404 page, but simpler:
  - smaller headline
  - less dramatic typography
  - same soft palette
  - one clear CTA
- This page should help the user recover quickly.

## Visual Reference: Lumora Handmade Candle Shop Landing Page

- Source: `https://dribbble.com/shots/27464560-Lumora-Handmade-Candle-Shop-Landing-Page`
- Reviewed: 2026-08-02
- Use as inspiration only. Do not copy the exact layout, brand, image, wording, or typography.

### What The Reference Shows

- A soft handmade candle e-commerce landing page concept.
- Main visual is a large hero image with bow-shaped candles in blush pink, ivory, and cream.
- The product is the first thing visible. It fills the frame and is cropped at the edges for an editorial feel.
- Text sits centered directly on top of the image.
- The hero copy is minimal:
  - Large brand wordmark: `LUMORA`
  - Delicate script tagline: `Light Crafted for Beautiful Moments`
  - Single CTA: `Browse Candles`
- The CTA is an outlined rounded pill with a transparent / glassy feel.
- The image uses soft daylight, warm candle flames, gentle shadows, and a muted grey-beige background.
- The whole design feels calm, feminine, luxurious, romantic, gift-ready, and handmade.

### Composition Notes

- Use full-width, image-led sections rather than card-heavy layouts.
- Let the product photography carry the emotion.
- Keep the hero uncluttered: one headline, one short line, one action.
- Use centered composition when the image has balanced left/right visual weight.
- Use edge cropping on product images to make the page feel premium and editorial.
- Keep generous empty space around text so the layout breathes.
- Avoid busy overlays, badges, excessive buttons, or dense navigation in the hero.

### Typography Notes

- Combine three roles:
  - Elegant display type for brand / hero moments.
  - Delicate script type for romantic accent lines only.
  - Clean sans-serif for navigation, buttons, product names, prices, and body text.
- Script should be used sparingly. It should add softness, not hurt readability.
- Large hero typography can be dramatic, but product cards and shop UI should stay practical.
- Letter spacing should feel calm and refined, not overly spaced out.

### Color Notes From The Reference

- The Dribbble page lists this palette:
  - Warm grey: `#6E6963`
  - Rose clay: `#AD554A`
  - Soft ivory: `#E7D5CE`
  - Warm beige: `#D5BAA6`
  - Candle gold: `#CE946A`
  - Deep brown: `#582D27`
  - Bright blush: `#EF7E81`
  - Dusty pink: `#DFACA1`
- For Atelier Marie, keep our existing palette as the lead.
- Borrow the principle, not the exact colors: blush + ivory + warm clay + deep grounding color.
- Use green / dark contrast from our palette to stop the site from becoming only pink.

### UI Guidance For Atelier Marie

- The homepage should open with a product or atelier lifestyle image, not a generic marketing block.
- The first viewport should immediately say `Atelier Marie` visually and emotionally.
- Use soft, real-looking product imagery as the main brand signal.
- Favor warm off-white and blush backgrounds with dark green-black text.
- Use clay / rose buttons for warm CTAs.
- Use deep green-black for navigation, footer, important text, and high contrast moments.
- Keep product pages and checkout more functional than the hero: readable labels, clear prices, obvious actions.
- Add romantic details through typography, spacing, photography, and small accents, not decorative clutter.

### Cautions

- Do not put white text over pale images unless contrast is verified.
- Do not overuse script fonts.
- Do not make every section pink.
- Do not let aesthetics hide shopping actions.
- Do not turn the site into a Dribbble-only concept; it still needs to work as a real store.

## Landing Page Hero Media Direction

- Product picture source folder: `/Users/I551270/Desktop/untitled folder`.
- Use these product pictures as available source material for the landing page rebrand.
- Photos from this folder may be used where applicable across the rebrand after optimization and placement in app-owned public/static assets.
- Hero concept: a woman's hand lighting a candle.
- The hand should feel gentle, elegant, and natural.
- Manicure should be beautiful but not long, dramatic, or distracting.
- Candle flame should move subtly, ideally as a short elegant loop / cinemagraph-style effect.
- Leave intentional free space in the composition for the Atelier Marie brand name and logo.
- The image/video should feel soft, romantic, premium, and real, not stock-like or overly staged.
- Avoid heavy blur, dark moodiness, harsh contrast, or anything that hides the candle/product.
- Text/logo placement must remain readable over the free space on mobile and desktop.

## Logo / Brand Mark Direction

- Do not use a candle as the logo.
- The logo / brand mark should be a beautiful signature-style letter `M`.
- It should feel handmade, DIY, elegant, personal, and boutique.
- It can be slightly artistic, but must still be recognizable as an `M`.
- The mark should pair with the `Atelier Marie` wordmark, not replace all readable brand text everywhere.
- Candle drawings can still be used for product/category decoration, but not as the main brand mark.
- Possible animation: the `M` draws itself like a signature stroke, then settles softly.
- Keep the logo animation subtle and optional. It should not loop loudly or distract from shopping.
- Provide a static fallback for reduced-motion users and for small header/footer placements.
- The mark must remain readable at small sizes, including header, mobile nav, favicon-style usage, and tab/category accents if used there.

## Animation Reference: Floral Decor Ecommerce Website

- Source: `https://dribbble.com/shots/14197728-Floral-Decor-Ecommerce-Website`
- Reviewed: 2026-08-02
- Use as inspiration for landing page motion only. Do not copy the exact flower/vase design, orange palette, text, or layout.

### What The Animation Shows

- A short looping landing page animation, about 6.6 seconds long.
- The page starts as a large editorial hero with a vase/floral product image and oversized serif headline.
- The hero then scrolls / slides into a storytelling state with descriptive text on the right.
- The same product image remains visually dominant while the surrounding text changes.
- The animation continues into a product-detail state:
  - Product title appears large on the right.
  - A small `Add to cart` button appears below.
  - Price appears separately, large and clean.
- The loop returns to the original hero state smoothly.
- The motion is calm and deliberate, not flashy.

### Motion Style To Borrow

- Use scroll-driven or scroll-like transitions on the landing page.
- Prioritize mobile vertical scrolling as the main animation path.
- Move large product/lifestyle imagery slowly across the viewport.
- Let text panels fade, slide, or reveal while the main image stays connected to the scene.
- Use parallax carefully: foreground product moves at a different pace than text/background.
- Animate between three landing states:
  - Mood / brand hero
  - Story / craft explanation
  - Featured product / shop action
- Make animations feel editorial, premium, and smooth.
- Keep the timing slower than typical web UI animations.

### What This Means For Atelier Marie

- The homepage can begin with a soft Atelier Marie hero image.
- On scroll, the hero should gently transition into a brand/story section.
- A featured item can then become shoppable without feeling like a hard page jump.
- Product images should remain the emotional anchor during the animation.
- Use our blush, ivory, clay, sage, and deep green palette instead of the orange/yellow reference palette.
- The motion should support the handmade boutique feeling: graceful, tactile, and calm.

### Animation Rules

- Prefer transform and opacity animations for smooth performance.
- Avoid jittery, bouncy, or playful effects.
- Avoid spinning, shaking, confetti, or loud hover effects.
- Keep CTAs stable and easy to click.
- Respect reduced-motion settings with a simpler fade/position fallback.
- Do not animate checkout, forms, payment, or critical shopping actions in a way that slows the user down.

### Possible Landing Page Sequence

- First view: Atelier Marie hero image with large brand text and one CTA.
- Scroll 1: image shifts softly; short atelier/story copy appears.
- Scroll 2: featured product enters with title, price, and add-to-cart action.
- Scroll 3: transition into product collections or category tiles.

## Landing Page Trust Recap

- Add a short landing-page section that recaps the About / Atelier page.
- Purpose: quickly show visitors that Atelier Marie is trustworthy, careful, and product-led.
- Keep it short, warm, and concrete. This should not feel like a long About page duplicate.

### Core Points To Communicate

- Every candle is made by hand.
- Wax is a premium organic blend of high-quality ingredients.
- Scents / fragrance blends are selected for quality, softness, and a refined home feel.
- Products are made with care, not mass-produced.
- Handmade variation is part of the character, but quality and finish should feel consistent.
- The atelier is reachable for questions, custom requests, and order support.

### Possible Short Copy Direction

- `Hand-poured in small batches with a premium organic wax blend and carefully selected fragrances, each Atelier Marie candle is made to feel beautiful, personal, and gift-ready.`
- Alternative shorter line: `Made by hand with premium organic wax, refined fragrances, and careful attention to every detail.`
- Tone should be confident and calm, not exaggerated.

### Trust Signals To Show

- Handmade / small-batch craft.
- Premium organic wax blend.
- High-quality fragrance ingredients.
- Gift-ready presentation.
- Personal support from the atelier.
- Clear contact, FAQ, terms, privacy, and cookie links.

### Claim Caution

- If the site says `organic`, `premium`, or `highest quality`, make sure those claims are true and supportable from supplier/product information.
- Prefer concrete wording over vague hype.
- Avoid overpromising health, sustainability, or safety benefits unless we have proof.

## Landing Page Product Categories

- Add product categories to the first page / landing page, not only the product listing page.
- Purpose: quickly show the range of Atelier Marie products and guide shoppers into the shop.
- Categories should feel visual, elegant, and handmade, not like plain filter buttons.

### Category Availability Rule

- Show a category only when there is at least one product of that type.
- Do not show empty categories.
- Category availability should come from real product/category data, not hardcoded assumptions.

### Initial Category Set

- Christmas balls.
- Custom boxes.
- Candles.
- Notebooks.
- Add more categories later only when real product types exist.

### Visual Direction

- Each category should have a pretty one-line animated drawing.
- Drawings should feel delicate, boutique, and handmade.
- Good drawing subjects:
  - Christmas ball: hanging ornament / bauble outline.
  - Custom box: gift box with ribbon.
  - Candle: candle jar or sculptural candle silhouette.
  - Notebook: small notebook with ribbon/bookmark or soft page outline.
- Use fine strokes, soft clay/dark-green colors, and minimal detail.
- Animation should be subtle: line draw, soft reveal, small hover motion, or gentle shimmer.
- Respect reduced-motion settings with a static drawing fallback.
- Do not make the illustrations childish or cartoon-like.

### Interaction

- Clicking a category should lead to the products page filtered to that category/type.
- The transition should feel animated and editorial, inspired by the reference below.
- Keep the link behavior clear and reliable. The animation should support navigation, not delay it.
- Category cards/tiles should have comfortable tap targets on mobile.

### Animation Reference: Vivienne Rose Ecommerce Website Design

- Source: `https://dribbble.com/shots/26565388-Vivienne-R-se-Ecommerce-Website-Design`
- Reviewed: 2026-08-02.
- Use as inspiration for category-to-shop motion only.
- Do not copy the exact brand, product imagery, layout, typography, or colors.
- Borrow the feeling: elegant category/product movement, smooth transitions, premium editorial flow.

### Mobile Direction

- Categories should work well near the top of the landing page.
- On mobile, show categories as a horizontally scrollable row or compact grid.
- Keep labels short and readable.
- Do not let animated drawings resize or shift the layout.
- Each category tile should have stable dimensions.

## FAQ And Help Page Interaction Direction

- FAQ and similar help pages should feel interactive and polished, not like a static wall of text.
- Questions should appear as popup-like expandable panels / accordions.
- By default, all questions should be collapsed.
- Users can expand and collapse each question.
- The interaction should feel soft and elegant: gentle fade/slide, no harsh jumps.
- Do not use blocking modal popups for FAQ answers. Keep content on the page so it is easy to scan, scroll, and use on mobile.

### FAQ Categories

- FAQ categories should be visible as a horizontal scroll area.
- On mobile, categories should scroll sideways with comfortable tap targets.
- On desktop, categories can still be horizontal, either scrollable or fitting in one row when space allows.
- Category tabs/chips should clearly show the active category.
- Switching category should show only the relevant collapsed questions.
- Keep the current category position stable and easy to understand.

### Accordion Behavior

- All questions collapsed by default.
- Allow opening one or multiple questions depending on what feels best in implementation, but avoid overwhelming the page.
- Each question should have a clear expand/collapse icon.
- Expanded answers should read like small elegant panels.
- Use accessible controls with proper keyboard support and `aria-expanded` behavior.
- Respect reduced-motion settings.

### Similar Pages

- Reuse this pattern for pages with grouped guidance or policy content where it helps scanning.
- Good candidates: FAQ, candle care/help content, shipping/returns guidance, terms/privacy section summaries.
- Avoid hiding critical legal text too deeply if regulations require it to be plainly visible.

## Admin Panel Direction

- Rework the admin panel mobile first again.
- Keep it in the same Atelier Marie visual spirit, but more practical and simplified than the public storefront.
- Admin should feel calm, clear, and easy to use on a phone.
- Avoid many animations. Use only small, useful transitions for focus, save confirmation, loading, and drawer open/close.
- Do not make admin feel decorative or marketing-like.

### Mobile-First Admin UX

- Design every admin workflow for mobile first, then adapt to tablet and desktop.
- Use single-column forms on mobile.
- Keep labels, inputs, errors, and save actions easy to scan.
- Tables should become mobile-friendly lists/cards with the most important fields first.
- Filters/search/actions should be reachable without horizontal squeezing.
- Navigation should be simple: drawer, compact section list, or bottom-friendly controls if appropriate.
- Primary actions should stay obvious and easy to tap.

### Visual Style

- Use the same soft Atelier Marie palette, but quieter:
  - warm ivory / cream backgrounds
  - deep green-black or charcoal text
  - clay/rose accents only for important actions or status
- Keep typography readable and restrained.
- Avoid oversized editorial typography inside admin surfaces.
- Avoid decorative imagery, large hero sections, heavy cards, and nested cards.
- Use compact spacing where it helps repeated work.

### Simplification Goals

- Reduce visual clutter.
- Group related settings and actions clearly.
- Make common tasks fast: products, orders, inventory, FAQ/content, legal pages, promotions.
- Keep advanced/admin-only details available, but not all visible at once.
- Prefer clear sections, collapsible groups, tabs, or segmented controls over long overloaded pages.
- Keep feedback direct: saved, error, required field, loading, empty state.

### Animation Rules For Admin

- Minimal motion only.
- No scroll-driven storytelling, parallax, decorative reveals, or playful effects in admin.
- No bouncy/jittery animations.
- Respect reduced-motion settings.
- Prioritize speed and stability over visual flourish.

## Luxury Animation Ideas Across The Site

- Overall animation direction: slow luxury reveal, not flashy website effects.
- The site should feel like opening a handmade gift box: soft layers, careful pacing, beautiful product reveal, and delicate details.
- Motion should support the spacious, luxurious, romantic feeling of the brand.
- Use animations to guide attention, not to decorate every element.

### Hero Animation Ideas

- Product or atelier hero image moves gently on vertical scroll.
- Brand text fades in like editorial print.
- Supporting copy appears after the brand text.
- Primary CTA appears last.
- Keep the first impression calm, cinematic, and product-led.

### Landing Category Animation Ideas

- Category one-line drawings draw themselves in as they enter the viewport.
- Drawings can have a tiny hover motion, but should stay delicate.
- Category click can transition toward the products page with a smooth editorial movement.
- Keep category animations stable so they do not resize or shift the layout.

### Trust Recap Animation Ideas

- Handmade / wax / scent / gift-ready trust points appear one by one.
- The reveal can feel like soft stamped notes or gentle paper layers.
- Avoid cards flying in or loud motion.
- Keep the copy readable and quick to scan.

### Product Card Animation Ideas

- Product image gently zooms or settles on hover.
- Candle glow / shadow can warm slightly on hover.
- Add-to-cart feedback should be quick, elegant, and clear.
- Avoid delaying shopping actions.

### FAQ And Help Animation Ideas

- Questions open like soft paper panels.
- Category strip glides horizontally.
- Answer panels should expand smoothly without hard jumps.
- Keep all questions collapsed by default.

### Footer Animation Ideas

- Huge `ATELIER MARIE` wordmark slowly reveals as the user reaches the bottom.
- Footer background image can drift very slightly.
- The translucent footer panel should feel settled and calm, not animated like a modal.

### Animation Boundaries

- Avoid decorative animations in checkout, payment, forms, admin, and legal-heavy pages.
- Always support reduced-motion preferences.
- Prefer opacity and transform animations for performance.
- Avoid spinning, bouncing, shaking, confetti, and playful effects.

## Footer Reference: Editorial Link Panel

- Source: user-provided screenshot, `codex-clipboard-49f1075e-5bb9-4cc9-bbcd-7e641b6030a6.png`.
- Reviewed: 2026-08-02.
- Use as inspiration for the bottom of the landing page / site footer only.
- Do not copy the exact brand, birds, typography, image, or labels from the reference.

### What The Reference Shows

- A wide muted background band with a soft floral/lifestyle image.
- A large translucent cream panel sits over the image.
- Footer links are grouped into elegant columns with serif headings.
- A newsletter area sits in the right column with a single-line email field and small subscribe action.
- Small social icons appear below the newsletter input.
- Copyright and legal links sit low in the panel.
- A huge cropped wordmark sits behind/below the panel and acts as an editorial background element.
- The overall feel is premium, calm, soft, and boutique.

### Atelier Marie Footer Direction

- Make the landing page end with an editorial footer section inspired by this composition.
- Use an Atelier Marie candle/product or atelier lifestyle image instead of generic flowers or birds.
- Use a translucent warm-cream/off-white panel over the image.
- Add a large cropped `ATELIER MARIE` wordmark behind or below the panel for a dramatic brand finish.
- Keep typography elegant: serif headings, practical sans-serif links.
- Keep spacing airy on desktop, but compact and readable on mobile.
- Do not create a card-heavy footer. It should feel like one composed editorial section.
- Current footer still feels too much like a plain rectangular link panel.
- Push it further toward an editorial magazine-style composition.
- Reduce the feeling of a single box by using layered background image, oversized cropped wordmark, softer panel edges, more intentional asymmetry, and lighter dividers.
- Consider letting some brand elements break the strict grid visually while keeping links easy to scan.
- Footer links should remain practical, but the section should feel like a designed final scene rather than a utilitarian site map card.

### Links To Reuse

- Reuse existing site links and routes. Do not invent new pages only to match the reference.
- Public navigation:
  - Home: `/`
  - Shop: `/products`
  - Atelier: `/atelier`
  - FAQ: `/faq`
  - Contact: `/contact`
- Account/auth links already present in the app:
  - Sign in / Login action
  - My Account: `/account`
  - My Orders: `/orders`
- Legal / privacy links already present in the footer:
  - Terms & Conditions: `/terms`
  - Privacy Policy: `/privacy`
  - Cookie Policy: `/cookies`
  - Cookie settings button
- Social links already present:
  - Instagram
  - TikTok
- Do not add reference-only links like Order Tracking, Delivery, Return, Appointment, Find a Store, Sustainability, or Giving Back unless those pages/features already exist.

### Suggested Link Grouping

- Explore: Home, Shop, Atelier.
- Help: Contact, FAQ.
- My Account: Sign in, My Account, My Orders.
- Legal: Terms & Conditions, Privacy Policy, Cookie Policy, Cookie settings.
- Social: Instagram, TikTok.

### Newsletter Note

- The reference includes a newsletter area.
- Add a newsletter block only if the app has or adds a real subscription flow with consent handling.
- Do not fake a working newsletter signup.
- If the subscription flow is not ready, reserve the visual space for social/contact copy instead.

### Mobile Direction

- Stack the footer sections vertically.
- Keep link groups in clear columns or two-column grids depending on width.
- Put the copyright/legal row at the bottom.
- Keep the large background wordmark decorative and non-blocking.
- Make sure every link has comfortable tap height and strong contrast over the panel.

## Whole-Site Shape Direction

- The whole website should feel less boxy overall.
- This should not be handled only by increasing border radius.
- Prefer fewer visible rectangles, softer section transitions, full-width editorial bands, gentle spacing, subtle shadows, and blur where appropriate.
- Remove unnecessary borders around repeated content when spacing, typography, or background tone can separate the content cleanly.
- Keep operational pages readable and structured, but soften the visual rhythm so the site feels boutique rather than grid-heavy.

## Landing Page Animation Map

- Global animation rule: motion should be slow, soft, one-time where possible, and scroll-triggered where it helps orientation.
- Avoid constant motion except for very subtle hero image drift or carousel rotation.
- Avoid bouncing, confetti, aggressive parallax, shaking, and animations that fight scrolling.
- Always respect reduced-motion preferences.

### Hero Section

- Background product image should use a slow `1.03` scale and tiny drift over roughly 10-14 seconds.
- Hero text should fade up once on load, with eyebrow, title, body, and CTA staggered subtly.
- Primary CTA can use a subtle shine sweep on hover.

### Trust Cards

- Use soft staggered fade-up when the section enters view.
- On hover, cards may lift about `2px` and soften the border/shadow.
- Avoid large movement or looping animation.

### Spotlight Product

- Product image should slowly zoom on hover.
- Text side should slide in softly from the left when scrolled into view.
- CTA row should fade up with a slight delay.

### Category Cards

- Category line art should draw when the section enters the viewport.
- On hover, the title can lift slightly, line art can darken, and the card can shift upward by about `4px`.
- No looping animation.

### Featured Products

- Desktop featured products should enter as three asymmetric previews with staggered slide/fade motion.
- Hovering a featured product should expand the active product, subtly zoom the image, and slide/fade in richer details.
- Abstract editorial strokes behind the products should use draw-on-scroll.
- Mobile should use smooth snap/swipe carousel motion with small dots.

### Product Cards

- Product images can zoom to about `1.04` on hover.
- Details and CTAs may use a slight fade/slide reveal.
- Add-to-cart success can use a soft checkmark pop.

### Footer

- Glass/footer panel should fade up and settle with a subtle blur effect when scrolled into view.
- Oversized footer wordmark should use a slow opacity reveal.
- Editorial line strokes may draw on scroll, but should be fewer and more restrained than the featured-products strokes.

## Homepage Hero Cleanup

- Source: user-provided screenshot, `codex-clipboard-3221c790-6927-44f3-88af-2a207c532c39.png`.
- Reviewed: 2026-08-02.
- Remove the secondary featured-product price button from the homepage hero area.
- In the screenshot, this is the button beside `Shop Collection` that reads like `Featured glass-bowl-rose-candle EUR14.00`.
- The hero does not need that product/price button there.
- Keep the primary `Shop Collection` call to action unless a later design decision changes it.
- If featured products remain in the hero and there is more than one, redesign that area as a subtle sliding carousel rather than a static boxed button.
- Carousel behavior should show one featured product at a time, use gentle slide/fade motion, pause on hover/focus, and respect reduced-motion preferences.
- If there is only one featured product, show it statically only if it does not clutter the hero, or hide the secondary featured slot entirely.

## Featured Products Section

- Add a dedicated featured products section underneath the homepage hero.
- This should be a richer browsing area than the hero CTA, not another boxed hero button.
- Remove the existing simple `Ready to shop` / `Featured` homepage block shown in the user-provided screenshot `codex-clipboard-a4d1a0c7-30b1-48fe-8086-c61bb53c6e6e.png`.
- That current block duplicates the featured-products concept and feels too sparse.
- Replace it with the richer featured-products section instead of keeping both.
- Keep only one featured-products area on the homepage.
- Avoid repeating the same product preview in multiple homepage sections.
- Treat it as a featured-products section such as `Featured candles` or `Editor's picks`, not necessarily a taxonomy category unless it needs to behave as a real shop filter.
- Use carousel mode when there is more than one featured product.
- The carousel should rotate slowly and gently, with manual arrows or dots so users stay in control.
- Each featured product item must link to its product detail page so shoppers can inspect details and buy.
- Pause rotation on hover or focus.
- Stop or delay auto-rotation after user interaction.
- Respect reduced-motion preferences.
- Keep the hero clean; put richer featured-product browsing below it.
- Preferred visual direction: show three featured products in a curated asymmetric layout rather than a rigid grid.
- The three items may sit at different visual positions/sizes to feel editorial and less boxy, but placement should be deterministic and responsive rather than truly random on every load.
- On hover-capable devices, hovering a featured product should enlarge the product preview, subtly zoom the image, and reveal more detail with a soft slide/fade.
- The hover state should feel like a rich preview into the product detail page, but should not embed/render the full product page inside the card.
- Use a rich preview card with product image, name, price, scent/category or short descriptor, stock/CTA state, and a link to the real product detail page.
- On touch devices, replace hover behavior with tap/focus, swipe, or carousel controls.
- On mobile, show the three featured products as a horizontal swipe carousel rather than the desktop asymmetric layout.
- Mobile carousel behavior should keep one product as the main focus, allow the next product to peek in from the side, and include small dots underneath.
- Mobile should use tap/focus to reveal expanded product details instead of hover.
- After the user swipes or taps carousel controls, pause or delay auto-rotation.
- Keep mobile product images large and product text compact.
- Free space in this section should use stronger abstract editorial line strokes rather than delicate wavy floral lines.
- The line strokes should feel premium, intentional, and magazine-like, supporting the asymmetric featured-product composition.
- Keep the strokes sparse, non-interactive, and away from product text/buttons so they never compete with shopping actions.
- The strokes may animate with a subtle draw-on-scroll effect when the featured section enters view.
- Draw-on-scroll animation must be slow, understated, and disabled or reduced for users who prefer reduced motion.
