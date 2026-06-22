# ==========================================
# Stage 1: Build the Astro Static Frontend
# ==========================================
FROM node:22 AS builder

WORKDIR /app

# Copy dependency files
COPY package.json ./

# Install packages
RUN npm install --legacy-peer-deps

# Copy rest of the code
COPY . .

# Build static output to dist/
RUN npm run build

# ==========================================
# Stage 2: Serve using Nginx
# ==========================================
FROM nginx:stable-alpine

# Copy static files to nginx html root
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port 80
EXPOSE 80

# Run nginx
CMD ["nginx", "-g", "daemon off;"]
