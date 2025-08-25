FROM nginx:alpine

# Set working directory
WORKDIR /app

# Copy web files
COPY html /usr/share/nginx/html/

# Copy custom nginx configuration
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf

# Create volume mount point for generated files
VOLUME ["/usr/share/nginx/html/plots"]

# Expose port 80
EXPOSE 80
