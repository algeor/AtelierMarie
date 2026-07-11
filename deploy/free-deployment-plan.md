# Free Deployment Plan

This plan compares several low-cost deployment paths, starting with the simplest frontend-only options and then outlining full-stack options for a real production store.

## Current Project Context

- The frontend is a Next.js app in `frontend/`.
- The frontend can run without the backend when `NEXT_PUBLIC_USE_MOCK_API=true`.
- The backend is a FastAPI app in `app/`.
- The current local database is SQLite (`atelier_marie.db`), which is fine for development but not a safe production choice on most free hosts.

## Option 1: Vercel Frontend-Only Demo

Use this when the goal is the fastest free public deployment of the website UI.

### Stack

- **Frontend:** Vercel Free
- **Backend:** Not deployed
- **Database:** Not required
- **Data mode:** Mock API

### Setup

1. Push the repository to GitHub.
2. Create a new project in Vercel.
3. Import the GitHub repository.
4. Configure the Vercel project:
   - **Root Directory:** `frontend`
   - **Install Command:** `npm install`
   - **Build Command:** `npm run build`
5. Add this environment variable:
   - `NEXT_PUBLIC_USE_MOCK_API=true`
6. Deploy.

### Pros

- Best fit for Next.js.
- Very quick setup.
- Good preview deployments for branches and pull requests.
- No backend or database cost.

### Cons

- Demo data only.
- No real orders, authentication persistence, or admin data changes.

## Option 2: Netlify Frontend-Only Demo

Use this when you prefer Netlify's dashboard, forms, or deployment workflow, while still keeping the site frontend-only.

### Stack

- **Frontend:** Netlify Free
- **Backend:** Not deployed
- **Database:** Not required
- **Data mode:** Mock API

### Setup

1. Push the repository to GitHub.
2. Create a new Netlify site from the GitHub repository.
3. Configure the build:
   - **Base directory:** `frontend`
   - **Build command:** `npm run build`
   - **Publish directory:** `.next`
4. Add this environment variable:
   - `NEXT_PUBLIC_USE_MOCK_API=true`
5. Deploy.

### Pros

- Free and simple for a public demo.
- Good GitHub integration.
- Nice option if Netlify features are preferred later.

### Cons

- Next.js support is generally less native than Vercel.
- May require Netlify's Next.js runtime/plugin depending on project settings.
- Still demo data only.

## Option 3: Cloudflare Pages Frontend-Only Demo

Use this when you want a very fast global CDN and are comfortable handling Cloudflare-specific Next.js deployment requirements.

### Stack

- **Frontend:** Cloudflare Pages Free
- **Backend:** Not deployed
- **Database:** Not required
- **Data mode:** Mock API

### Setup

1. Push the repository to GitHub.
2. Create a Cloudflare Pages project from the GitHub repository.
3. Configure the project for the `frontend` directory.
4. Use Cloudflare's supported Next.js adapter/runtime if needed.
5. Add this environment variable:
   - `NEXT_PUBLIC_USE_MOCK_API=true`
6. Deploy.

### Pros

- Very strong free CDN offering.
- Good long-term option if the project later uses Cloudflare services.
- No backend or database required for the demo mode.

### Cons

- More setup friction than Vercel for Next.js.
- Some Next.js features may need Cloudflare-specific adaptation.
- Still demo data only.

## Option 4: Vercel Frontend + Render Backend + Supabase/Neon Postgres

Use this when the store needs real API behavior, orders, admin flows, and persistent data while staying on free tiers as much as possible.

### Stack

- **Frontend:** Vercel Free
- **Backend API:** Render Free web service
- **Database:** Supabase Free Postgres or Neon Free Postgres
- **Data mode:** Real API

### Setup

1. Deploy the frontend to Vercel from `frontend/`.
2. Deploy the FastAPI backend to Render.
3. Create a hosted Postgres database in Supabase or Neon.
4. Update the backend database configuration to use Postgres instead of local SQLite.
5. Set frontend environment variables:
   - `NEXT_PUBLIC_USE_MOCK_API=false`
   - `NEXT_PUBLIC_API_URL=https://<backend-domain>`
6. Configure backend CORS to allow the Vercel frontend domain.
7. Test products, cart, checkout, orders, admin, and authentication against the live API.

### Pros

- Good free-tier architecture for a real store prototype.
- Keeps frontend on the platform that best supports Next.js.
- Supabase and Neon both provide managed Postgres without running your own database server.

### Cons

- More moving parts.
- Free backend instances may sleep after inactivity.
- Requires database migration work before it is production-safe.

## Option 5: Netlify Frontend + Koyeb/Render Backend + Neon Postgres

Use this when you want alternatives to Vercel while keeping a similar full-stack shape.

### Stack

- **Frontend:** Netlify Free
- **Backend API:** Koyeb Free or Render Free
- **Database:** Neon Free Postgres
- **Data mode:** Real API

### Pros

- Avoids depending on a single hosting provider.
- Neon is a good fit for lightweight Postgres hosting.
- Koyeb and Render can both run Python web services.

### Cons

- More configuration work than the Vercel-only frontend demo.
- Free-tier availability, sleep behavior, and limits can change.
- Still requires replacing SQLite with hosted Postgres.

## Option 6: GitHub Pages Static Export

Use this only if the project is converted into a fully static website.

### Stack

- **Frontend:** GitHub Pages
- **Backend:** Not deployed
- **Database:** Not required
- **Data mode:** Static/mock data

### Pros

- Completely free.
- Very simple hosting once the app is static.
- Good for a brochure site or fixed catalog.

### Cons

- Not a good fit for the current Next.js app without changes.
- Next.js redirects, dynamic behavior, app routing, and image/runtime features may need adjustment.
- No real backend behavior.

## Recommendation

Start with **Option 1: Vercel Frontend-Only Demo** because it is the fastest and cleanest fit for the current codebase.

If Vercel is not preferred, use **Option 2: Netlify Frontend-Only Demo** as the next simplest alternative.

When the project needs real orders and persistent data, move to **Option 4: Vercel Frontend + Render Backend + Supabase/Neon Postgres**.

Avoid treating the local SQLite database as production storage on free hosting. For real customer data, use hosted Postgres.
