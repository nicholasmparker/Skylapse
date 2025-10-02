# Lessons Learned: Building Skylapse

## What Went Wrong

### 1. Over-Complicated Architecture

**Mistake**: Built complex scheduling system with edge-based intelligence, multiple APIs, weather integration, custom presets, manual captures, etc.

**Result**:

- Couldn't answer "where do schedules live?"
- Frontend couldn't reliably reach capture device
- No coordination for multiple cameras
- Too many moving parts to debug

**Lesson**: Start with the simplest thing that works. Add complexity only when needed.

---

### 2. Wrong Brain-Edge Split

**Mistake**: Put scheduling logic on the Raspberry Pi (edge device).

**Result**:

- Each camera acts independently
- No way to coordinate multiple cameras
- Frontend talks directly to edge (CORS issues)
- Business logic scattered across services

**Lesson**: Edge devices should be dumb executors. Brain (backend) should make all decisions.

---

### 3. Unclear Deployment Story

**Mistake**: Mixed local development, Docker, and Pi deployment without clear boundaries.

**Result**:

- Agents kept forgetting Docker
- Tests ran against wrong services
- "Works on my machine" problems
- Deployment was manual and error-prone

**Lesson**: Document Docker workflow prominently. Make deployment scriptable and foolproof.

---

### 4. Too Many Features Too Soon

**Mistake**: Built manual captures, weather integration, custom presets, two scheduling UIs, etc. before core functionality worked.

**Result**:

- Core feature (automated scheduling) was broken
- Couldn't validate if the product was valuable
- Maintenance burden for unused features

**Lesson**: Build the smallest thing users care about. Ship it. Iterate.

---

### 5. No Clear Use Case

**Mistake**: Built generic "timelapse system" without specific user story.

**Result**:

- Feature creep (what if we need X?)
- Over-engineering (might need to scale to 100 cameras!)
- Lost sight of actual goal

**Lesson**: Define the exact scenario you're building for. "User wakes up and watches today's sunrise timelapse."

---

## What Went Right

### 1. Docker Containerization

**Why it worked**: Consistent environments, easy deployment, isolated services.

**Keep doing**: Use Docker for all services except Pi (hardware access).

---

### 2. Transfer Queue Pattern

**Why it worked**: Capture → Transfer → Processing is simple and reliable.

**Keep doing**: Async image transfer with filesystem queue is good enough.

---

### 3. Separation of Services

**Why it worked**: Capture, Processing, Backend, Frontend are distinct concerns.

**Keep doing**: Microservices pattern, but keep them simple (not nano-services).

---

### 4. Modular Camera Controller

**Why it worked**: Hardware abstraction made testing possible without real camera.

**Keep doing**: Abstract hardware behind interfaces.

---

## New Principles Going Forward

### 1. Start Stupidly Simple

- Hardcode schedules (sunrise, daytime, sunset)
- Use filesystem, not database
- Direct HTTP calls, not message queues
- Three-button UI, not admin dashboard

**Add complexity only when users demand it.**

---

### 2. Brain-Edge Pattern

- **Backend = Brain**: Stores state, makes decisions, coordinates
- **Pi = Edge**: Executes commands, reports status
- **Frontend = Eyes**: Displays data from brain only

**Never let edge devices make decisions.**

---

### 3. One Clear Use Case

"User wants to see beautiful sunrise, daytime, and sunset timelapses automatically."

That's it. Build for that. Everything else is future.

---

### 4. Docker by Default

- All dev in Docker (except Pi)
- Tests against Docker containers
- Deploy Docker images
- Make it impossible to forget

**Update CLAUDE.md to shout "THIS IS DOCKER" at agents.**

---

### 5. Deployment = One Command

```bash
./scripts/deploy-pi.sh      # Deploy capture to Pi
./scripts/deploy-server.sh  # Deploy backend/frontend
```

No manual steps. No SSH and edit files. Scriptable or it doesn't exist.

---

## Architecture Comparison

### ❌ Old (Complex)

```
Frontend → (CORS issues) → Helios
                             ↓
                      Stores schedules
                      Evaluates schedules
                      Executes captures
                             ↓
                      Processing (reactive)
```

**Problems**: No coordination, CORS issues, edge too smart

---

### ✅ New (Simple)

```
Frontend → Backend (Brain)
            ↓
     Stores 3 schedules
     Calculates exposure
     Sends commands
            ↓
         Pi (Edge)
            ↓
      Captures photo
            ↓
      Upload to backend
            ↓
      Processing (stacking)
            ↓
      Video generation
```

**Benefits**: Single source of truth, coordinated, scalable

---

## Specific Technical Decisions

### Storage: Filesystem, Not Database

**Why**:

- 3 schedules = overkill for DB
- JSON files are easy to debug
- No migration headaches

**When to change**: 100+ schedules or multi-user

---

### Scheduling: 30-Second Loop, Not Cron

**Why**:

- Simple to understand and debug
- Good enough for timelapse (30s precision)
- No cron syntax to maintain

**When to change**: Need second-level precision (unlikely)

---

### Communication: HTTP POST, Not Message Queue

**Why**:

- Reliable enough for our use case
- Simple to debug (curl commands)
- No RabbitMQ/Redis to maintain

**When to change**: High frequency or unreliable network

---

### Frontend: Three Video Players, Not Admin Panel

**Why**:

- User doesn't need to manage schedules daily
- Set and forget is the goal
- Complexity kills adoption

**When to change**: User needs custom schedules (later)

---

## Metrics for Success

### Product Success

- ✅ User opens app and sees today's timelapses
- ✅ Videos are beautiful (good exposure, stacked)
- ✅ Zero manual intervention required
- ✅ Works every day without touching it

### Technical Success

- ✅ Deploy Pi in < 2 minutes
- ✅ Deploy server in < 5 minutes
- ✅ All tests pass in Docker
- ✅ No "works on my machine" issues
- ✅ Agent never forgets Docker

### Maintenance Success

- ✅ Can understand entire system in 30 minutes
- ✅ Can debug issues by reading logs
- ✅ Can add feature without breaking existing
- ✅ Can hand off to someone else easily

---

## What to Build Next (After MVP)

Only add these if users ask:

1. **Custom schedules** - If users want different intervals
2. **Weather gating** - If users complain about cloudy timelapses
3. **Manual captures** - If users want ad-hoc photos
4. **Multi-camera** - If users have multiple Pis
5. **Cloud storage** - If users want remote access
6. **Mobile app** - If users want phone notifications

**Don't build features speculatively.**

---

## The One-Month Test

After 30 days of running:

### Good Signs ✅

- System ran without intervention
- Videos generated every day
- User checks app regularly
- User shows timelapses to friends

### Bad Signs ❌

- Required manual fixes
- Videos missing or broken
- User forgot about it
- Too complicated to maintain

**If bad signs: Simplify more.**

---

## Summary: Build Less, Better

### Old Approach

- Build everything users might need
- Over-engineer for scale
- Complex architecture "just in case"
- Features > functionality

### New Approach

- Build minimum viable delight
- Simple until painful
- Architecture for today's problem
- Functionality > features

**The goal is working timelapses, not impressive architecture.**

---

## Final Reminder

When tempted to add complexity, ask:

1. **Does this help sunrise/daytime/sunset timelapses?**
2. **Is there a simpler way?**
3. **Can we defer this?**
4. **Would a user pay for this feature?**

If any answer is no, don't build it.

---

**Keep it simple. Ship it. Make it work. Then iterate.**
