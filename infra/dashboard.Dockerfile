FROM node:24.15.0-slim AS build
WORKDIR /app
COPY . .
RUN npm ci && npm run build --workspace=apps/dashboard
FROM nginx:1.28.0-alpine
COPY infra/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/apps/dashboard/dist /usr/share/nginx/html
