FROM nginx:alpine

# Set working directory
WORKDIR /app

# Copy web files
COPY html /usr/share/nginx/html/

# Make AUTO_VERSION available for the web pages
COPY AUTO_VERSION /usr/share/nginx/html/AUTO_VERSION

# Copy custom nginx configuration
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf

# Create volume mount point for generated files
VOLUME ["/usr/share/nginx/html/plots"]

# Expose port 80
EXPOSE 80
