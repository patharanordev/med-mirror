FROM node:20-slim AS builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy source code
COPY . .

# Copy VAD and ONNX assets to public directory
RUN cp node_modules/@ricky0123/vad-web/dist/*.onnx public/ && \
    cp node_modules/@ricky0123/vad-web/dist/*.js public/ && \
    cp node_modules/onnxruntime-web/dist/*.wasm public/ && \
    cp node_modules/onnxruntime-web/dist/*.mjs public/ || true

# Build the application
RUN npm run build

# Production image
FROM node:20-slim AS runner

WORKDIR /app

ENV NODE_ENV=production

# Copy necessary files from builder
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

# Copy config for runtime evaluation
COPY --from=builder /app/next.config.ts ./next.config.ts

EXPOSE 3000

CMD ["npm", "start"]
