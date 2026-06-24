FROM node:20-alpine AS base

WORKDIR /app

COPY package.json package-lock.json ./

FROM base AS deps

RUN npm ci

FROM deps AS dev

ENV NODE_ENV=development

CMD ["npm", "run", "dev"]

FROM node:20-alpine AS builder

WORKDIR /app

ARG NEXT_PUBLIC_APP_TIMEZONE=Asia/Seoul
ENV NEXT_PUBLIC_APP_TIMEZONE=$NEXT_PUBLIC_APP_TIMEZONE

COPY --from=deps /app/node_modules ./node_modules
COPY . .

RUN npm run build

FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production

COPY --from=builder /app/.next ./.next
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/next.config.ts ./next.config.ts

EXPOSE 3000

CMD ["npm", "run", "start"]
