FROM docker.io/node:20-alpine

# Set working directory
WORKDIR /app

# Copy package files
COPY frontend/package.json frontend/package-lock.json* ./

# Install dependencies
RUN npm install

# Copy application code
COPY frontend /app

# Expose port
EXPOSE 3000

# Start development server
CMD ["npm", "run", "dev"]
