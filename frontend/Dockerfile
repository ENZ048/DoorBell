FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci || npm install
COPY . .
RUN npm run build

# Final stage exposes /app/dist as artifact. In production compose, Caddy
# mounts the host's frontend/dist directly, but this image is useful for CI.
FROM alpine:3.20
COPY --from=build /app/dist /dist
CMD ["sh", "-c", "echo 'frontend build artifact at /dist'"]
