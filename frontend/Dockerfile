FROM node:22-alpine AS build

WORKDIR /app

COPY package*.json ./
# package-lock.json installs cleanly with `npm ci` on Node 22 (checked, no
# peer-dependency conflicts), so --legacy-peer-deps is no longer needed.
RUN npm ci

COPY . .

ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# Production stage: serve with nginx
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
