# Build stage
FROM node:18-alpine as build

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies (using --legacy-peer-deps to handle peer dependency conflicts)
RUN npm install --legacy-peer-deps

# Copy source code
COPY . .

# Build the React app
RUN npm run build

# Production stage
FROM nginx:alpine

# Create non-root user for nginx (nginx alpine already has nginx user)
# Set proper ownership for nginx directories
RUN chown -R nginx:nginx /var/cache/nginx /var/log/nginx /etc/nginx/conf.d && \
    touch /var/run/nginx.pid && \
    chown -R nginx:nginx /var/run/nginx.pid

# Copy built app from build stage
COPY --from=build /app/build /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Set ownership of static files
RUN chown -R nginx:nginx /usr/share/nginx/html

EXPOSE 80

# Switch to non-root user
USER nginx

CMD ["nginx", "-g", "daemon off;"]
