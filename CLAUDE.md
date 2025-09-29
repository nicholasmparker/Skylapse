# Claude Code Memory - Skylapse Project

## CRITICAL REMINDERS

### 🐳 THIS IS A DOCKER APPLICATION
- **ALWAYS use Docker commands for development**
- **Frontend runs in Docker**: `docker-compose up frontend-dev`
- **Backend services run in Docker**: `docker-compose up processing backend`
- **DO NOT use npm/node commands directly** - use Docker containers
- **Tests run against Docker containers at localhost:3000**

### Service Architecture
- **Capture Service**: Runs on Raspberry Pi (helios.local:8080)
- **Processing Service**: Docker container (localhost:8081)
- **Backend Service**: Docker container (localhost:8082)
- **Frontend**: Docker container (localhost:3000)

### Development Workflow
1. Make code changes
2. Use `docker-compose up service-name` to test
3. Run Playwright tests against Docker containers
4. Use deployment scripts for Pi updates

### QA Validation Process
- **MANDATORY for every task**
- Run Playwright tests with Docker services running
- Validate all functionality before marking tasks complete

---
*Stop forgetting this is Docker! 🐳*