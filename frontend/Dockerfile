# --- Build stage -----------------------------------------------------------
FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# --- Runtime stage -----------------------------------------------------------
FROM nginx:1.27-alpine

# Templated via the nginx image's built-in envsubst entrypoint (runs on
# container start, substituting ${BACKEND_URL} and ${API_KEY} into
# /etc/nginx/conf.d/).
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html

# Backend service to proxy "/api" and "/health" to. Override in
# docker-compose if the backend service has a different name/port.
ENV BACKEND_URL=http://backend:8000

# API_KEY is required and has no default (see ../.env.example): nginx's
# envsubst entrypoint only replaces ${API_KEY} for vars that are actually set
# in the environment, so if it's missing the container fails to start with an
# "unknown variable" error - the same fail-fast behaviour as the backend.
# Same value as the backend's API_KEY - the frontend's nginx attaches it to
# proxied "/api/" requests so logged-in (Authentik-authenticated) users don't
# need to know it.

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -q -O- http://127.0.0.1/ >/dev/null || exit 1
