FROM nginx:alpine

# Set working directory
WORKDIR /app

# Copy web files
COPY html /usr/share/nginx/html/

# Create volume mount point for generated files
VOLUME ["/usr/share/nginx/html/plots"]

# Expose port 80
EXPOSE 80

# Using default nginx configuration
