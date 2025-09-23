# B2B Frontend Dockerfile
FROM node:18-alpine

# Set working directory
WORKDIR /app

# Copy package files (will be created when B2B project is initialized)
COPY B2B/package*.json ./

# Install dependencies
RUN npm ci --only=production=false

# Copy source code
COPY B2B/ .

# Expose port
EXPOSE 5174

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5174/ || exit 1

# Start development server
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5174"]