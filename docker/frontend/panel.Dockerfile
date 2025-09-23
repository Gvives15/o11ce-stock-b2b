# Panel Operations Frontend Dockerfile
FROM node:18-alpine

# Set working directory
WORKDIR /app

# Copy package files (will be created when Panel project is initialized)
COPY Panel/package*.json ./

# Install dependencies
RUN npm ci --only=production=false

# Copy source code
COPY Panel/ .

# Expose port
EXPOSE 5175

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5175/ || exit 1

# Start development server
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5175"]