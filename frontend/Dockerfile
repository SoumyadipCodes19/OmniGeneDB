# Stage 1: Build the static assets
FROM node:22-alpine AS builder

WORKDIR /app

# Install dependencies using clean install
COPY package.json package-lock.json ./
RUN npm ci

# Copy application source files and configurations
COPY index.html tsconfig.json vite.config.ts tailwind.config.js postcss.config.js ./
COPY public ./public
COPY src ./src

# Optional build-time argument for API URL
ARG VITE_API_URL=""
ENV VITE_API_URL=${VITE_API_URL}

# Compile TypeScript and bundle with Vite
RUN npm run build

# Stage 2: Production web server
FROM nginx:alpine

# Default environment variables for local Docker Compose and Cloud Run
ENV PORT=80
ENV BACKEND_URL=http://backend:8000

# Clean out default Nginx static files
RUN rm -rf /usr/share/nginx/html/*

# Copy built production assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Provide Nginx template for automatic envsubst by official Nginx docker-entrypoint
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
