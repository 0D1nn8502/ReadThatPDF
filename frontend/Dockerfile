FROM node:18-alpine

WORKDIR /app

# Install dependencies for native modules
RUN apk add --no-cache libc6-compat

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Set environment variables
ENV NEXT_TELEMETRY_DISABLED 1

# Expose port
EXPOSE 3000

# Start in development mode to avoid build issues
CMD ["npm", "run", "dev"]