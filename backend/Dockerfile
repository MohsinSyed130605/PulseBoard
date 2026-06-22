# ==========================================
# Stage 1: Build Dependencies
# ==========================================
FROM python:3.11-alpine AS builder

RUN apk add --no-cache gcc musl-dev linux-headers python3-dev

WORKDIR /app

COPY requirements.txt ./

# Install packages to a user directory to avoid system-level isolation conflicts
RUN pip install --no-cache-dir --user -r requirements.txt

# ==========================================
# Stage 2: Final Run Image
# ==========================================
FROM python:3.11-alpine

WORKDIR /app

# Copy compiled python libraries from builder stage
COPY --from=builder /root/.local /root/.local

# Copy main server file
COPY main.py ./

# Ensure user binaries are on path
ENV PATH=/root/.local/bin:$PATH

# Expose backend port
EXPOSE 8000

# Start FastAPI server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
