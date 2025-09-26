# Skylapse Project Planning

This directory contains the project planning and tracking documents for Skylapse.

## 📁 Planning Structure

### Core Documents
- **[EPICS.md](EPICS.md)** - High-level features broken down into user stories
- **[SUCCESS_METRICS.md](SUCCESS_METRICS.md)** - How we measure project success
- **[SPRINT_TEMPLATE.md](SPRINT_TEMPLATE.md)** - Template for sprint planning

### Active Sprints
- **SPRINT-1.md** - Current sprint (copy from template)
- **SPRINT-2.md** - Next sprint planning
- etc.

## 🔄 Workflow

### Sprint Planning Process
1. **Review Epics**: Look at [EPICS.md](EPICS.md) for available user stories
2. **Create Sprint**: Copy [SPRINT_TEMPLATE.md](SPRINT_TEMPLATE.md) to `SPRINT-X.md`
3. **Select Stories**: Choose user stories for the sprint based on capacity
4. **Set Goals**: Define clear sprint objectives and success criteria
5. **Track Progress**: Update daily progress in sprint document

### Story Lifecycle
```
📝 Epic → 🎯 User Story → 📋 Sprint Backlog → 🔄 In Progress → 🧪 Testing → ✅ Done
```

### Success Tracking
- **Daily**: Update progress in current sprint document
- **Weekly**: Review against success metrics
- **Sprint End**: Complete sprint review and plan next sprint

## 🎯 Current Status

### Active Sprint
- **Sprint**: [Current sprint number and name]
- **Goal**: [Primary objective]
- **Progress**: [X/Y stories completed]

### Next Priorities
1. [Top priority for next sprint]
2. [Second priority]
3. [Third priority]

## 📊 Quick Commands

### Create New Sprint
```bash
# Copy template and rename
cp planning/SPRINT_TEMPLATE.md planning/SPRINT-X.md

# Edit with your sprint details
vim planning/SPRINT-X.md
```

### Check Progress
```bash
# View current sprint
cat planning/SPRINT-*.md | grep -E "^\- \[[ x]\]"

# Count completed stories
grep -c "^\- \[x\]" planning/SPRINT-*.md
```

### Review Success Metrics
```bash
# Run automated metrics
./scripts/measure-success-metrics.sh

# View success criteria
grep -A 5 "Success Criteria" planning/SUCCESS_METRICS.md
```

## 🔧 Tools Integration

### GitHub Integration (Optional)
If you want to use GitHub Issues:
```bash
# Create issues from user stories
./scripts/sync-stories-to-github.sh planning/EPICS.md

# Update sprint board
./scripts/update-github-project.sh planning/SPRINT-1.md
```

### Simple Tracking (Recommended)
Just use the markdown files and update them as you work:
- Edit sprint files directly
- Use checkboxes for progress tracking
- Review and update weekly

---

*This planning system is designed to be lightweight but comprehensive for a personal project.*
