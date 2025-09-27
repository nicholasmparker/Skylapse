# Frontend Architecture Decision: Docker Containerization

**Date**: September 27, 2025
**Sprint**: Sprint 3 - Professional Interface Development
**Decision**: Containerize frontend with Docker (NOT static hosting)

---

## 🎯 **Architectural Decision**

### **Decision**: Docker Containerization for React Frontend
The Skylapse frontend will be **containerized with Docker** and deployed alongside the existing capture and processing services.

### **Alternative Considered**: Static Hosting (Netlify/Vercel)
Static hosting was considered but rejected in favor of the containerized approach.

---

## 🏗️ **System Architecture Overview**

```
┌─────────────────────────────────────────────────────────────┐
│ Skylapse Mountain Timelapse System                          │
├─────────────────────────────────────────────────────────────┤
│ Frontend (React + Docker)           │ Port 3000             │
│ ├── Professional UI/UX              │ Container: skylapse-ui│
│ ├── Real-time monitoring            │ Volume: frontend_build │
│ ├── Timelapse gallery               │ Network: skylapse     │
│ └── Configuration management        │                       │
├─────────────────────────────────────┼───────────────────────┤
│ Capture Service (Native Pi)         │ Port 8080             │
│ ├── Camera control                  │ Service: systemd      │
│ ├── Intelligent scheduling          │ Host: helios.local    │
│ └── Hardware integration            │                       │
├─────────────────────────────────────┼───────────────────────┤
│ Processing Service (Docker)         │ Port 8081             │
│ ├── Image processing                │ Container: skylapse-  │
│ ├── Video generation                │ processing            │
│ └── Transfer management             │ Network: skylapse     │
└─────────────────────────────────────┴───────────────────────┘
```

---

## ✅ **Why Docker Containerization?**

### **1. Architectural Consistency**
- **Processing service** already containerized with Docker
- **Unified deployment** strategy across all services
- **Single technology stack** for service management

### **2. Professional Self-Contained System**
- **On-premise deployment** suitable for private mountain installations
- **No external dependencies** (Netlify/Vercel not needed)
- **Complete system isolation** from internet dependencies

### **3. Simplified Networking**
- **Direct service communication** within Docker network
- **No CORS complications** with backend services
- **Unified reverse proxy** configuration possible

### **4. Operational Benefits**
- **Consistent deployment scripts** (capture, processing, frontend)
- **Single Docker Compose** orchestration
- **Unified logging and monitoring** across all services
- **Easy backup and restore** of entire system

### **5. Development Experience**
- **Local development** matches production exactly
- **Hot reload** during development with volume mounts
- **Isolated dependencies** prevent version conflicts

---

## 🚫 **Why NOT Static Hosting?**

### **Problems with Netlify/Vercel Approach**
1. **CORS Complexity**: Frontend on external domain accessing local APIs
2. **Network Dependencies**: Requires internet for frontend delivery
3. **Architecture Mismatch**: Breaks self-contained system design
4. **Deployment Inconsistency**: Different process from backend services
5. **Security Concerns**: External hosting for private mountain installations

---

## 🔧 **Implementation Strategy**

### **Container Strategy**
```dockerfile
# Multi-stage build for production optimization
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 3000
```

### **Docker Compose Integration**
```yaml
services:
  frontend:
    build: ./frontend
    container_name: skylapse-frontend
    ports:
      - "3000:3000"
    networks:
      - skylapse
    depends_on:
      - processing
    environment:
      - NODE_ENV=production
      - REACT_APP_API_URL=http://processing:8081
      - REACT_APP_CAPTURE_URL=http://helios.local:8080
```

### **Deployment Integration**
- **Extend existing scripts**: `deploy-frontend.sh`
- **Update** `deploy-and-validate.sh` to include frontend
- **Docker Compose**: Add frontend service to processing compose file

---

## 🎯 **Service Communication**

### **Frontend → Backend APIs**
```typescript
// API configuration for containerized environment
const API_CONFIG = {
  captureService: process.env.REACT_APP_CAPTURE_URL || 'http://helios.local:8080',
  processingService: process.env.REACT_APP_API_URL || 'http://localhost:8081',
  wsEndpoint: process.env.REACT_APP_WS_URL || 'ws://localhost:8081/ws'
};
```

### **Network Architecture**
- **Frontend container**: `skylapse-frontend` (port 3000)
- **Processing container**: `skylapse-processing` (port 8081)
- **Capture service**: Native Pi service (port 8080)
- **Docker network**: `skylapse` bridge network

---

## 📋 **Deployment Checklist**

### **✅ Required Files**
- [ ] `frontend/Dockerfile` - Multi-stage production build
- [ ] `frontend/nginx.conf` - Optimized Nginx configuration
- [ ] `frontend/docker-compose.yml` - Service orchestration
- [ ] `scripts/deploy-frontend.sh` - Deployment automation
- [ ] Update `scripts/deploy-and-validate.sh` - Include frontend

### **✅ Configuration**
- [ ] Environment variables for API endpoints
- [ ] Docker network configuration
- [ ] Volume mounts for development
- [ ] Health checks for service monitoring

### **✅ Documentation**
- [ ] Update README with frontend Docker instructions
- [ ] Document development workflow with Docker
- [ ] Update deployment guide with frontend steps

---

## 🚀 **Development Workflow**

### **Local Development**
```bash
# Start all services
docker-compose up -d

# Frontend development with hot reload
cd frontend
npm run dev  # Runs on localhost:3000

# Or run frontend in container with hot reload
docker-compose -f docker-compose.dev.yml up
```

### **Production Deployment**
```bash
# Build and deploy all services
./scripts/deploy-and-validate.sh

# Or just frontend
./scripts/deploy-frontend.sh
```

---

## 🎖️ **Success Criteria**

### **✅ Architecture Validation**
- [ ] Frontend accessible at `http://helios.local:3000`
- [ ] All APIs reachable from frontend container
- [ ] Real-time WebSocket connections functional
- [ ] Production build optimized (<500KB gzipped)

### **✅ Operational Validation**
- [ ] Single command deployment works
- [ ] Service restarts automatically on failure
- [ ] Logs centralized with other services
- [ ] Health checks report service status

---

## 📖 **References**

- **Processing Service Docker**: `/processing/docker-compose.yml`
- **Deployment Scripts**: `/scripts/deploy-*.sh`
- **Sprint 3 Requirements**: `/planning/SPRINT-3.md`

---

**This Docker architecture ensures Skylapse remains a professional, self-contained mountain photography system with unified deployment and operation! 🏔️🐳**
