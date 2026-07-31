FROM node:22-slim AS deps

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

FROM node:22-slim AS builder

WORKDIR /app

ARG NEXT_PUBLIC_API_URL=http://localhost:8001
ARG NEXT_PUBLIC_MEDIA_URL=http://localhost:8001/static
ARG NEXT_PUBLIC_SITE_URL=http://localhost:3000
ARG NEXT_PUBLIC_USE_MOCK_API=false
ARG NEXT_PUBLIC_STRIPE_ENABLED=false
ARG NEXT_PUBLIC_BANK_IBAN=
ARG NEXT_PUBLIC_BANK_BIC=
ARG NEXT_PUBLIC_BANK_NAME=
ARG NEXT_PUBLIC_INSTAGRAM_URL=
ARG NEXT_PUBLIC_TIKTOK_URL=
ARG NEXT_PUBLIC_ANALYTICS_CONSENT_VERSION=2026-07-31

ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NEXT_PUBLIC_MEDIA_URL=$NEXT_PUBLIC_MEDIA_URL \
    NEXT_PUBLIC_SITE_URL=$NEXT_PUBLIC_SITE_URL \
    NEXT_PUBLIC_USE_MOCK_API=$NEXT_PUBLIC_USE_MOCK_API \
    NEXT_PUBLIC_STRIPE_ENABLED=$NEXT_PUBLIC_STRIPE_ENABLED \
    NEXT_PUBLIC_BANK_IBAN=$NEXT_PUBLIC_BANK_IBAN \
    NEXT_PUBLIC_BANK_BIC=$NEXT_PUBLIC_BANK_BIC \
    NEXT_PUBLIC_BANK_NAME=$NEXT_PUBLIC_BANK_NAME \
    NEXT_PUBLIC_INSTAGRAM_URL=$NEXT_PUBLIC_INSTAGRAM_URL \
    NEXT_PUBLIC_TIKTOK_URL=$NEXT_PUBLIC_TIKTOK_URL \
    NEXT_PUBLIC_ANALYTICS_CONSENT_VERSION=$NEXT_PUBLIC_ANALYTICS_CONSENT_VERSION

COPY --from=deps /app/node_modules ./node_modules
COPY . .

RUN npm run build

FROM node:22-slim AS runtime

ENV NODE_ENV=production \
    NEXT_DIST_DIR=.next-build

WORKDIR /app

RUN addgroup --system app \
    && adduser --system --ingroup app app

COPY --from=builder --chown=app:app /app/package.json ./package.json
COPY --from=builder --chown=app:app /app/package-lock.json ./package-lock.json
COPY --from=builder --chown=app:app /app/node_modules ./node_modules
COPY --from=builder --chown=app:app /app/.next-build ./.next-build
COPY --from=builder --chown=app:app /app/public ./public
COPY --from=builder --chown=app:app /app/next.config.js ./next.config.js

USER app

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD node -e "fetch('http://127.0.0.1:3000').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

CMD ["npm", "run", "start", "--", "--hostname", "0.0.0.0", "--port", "3000"]
