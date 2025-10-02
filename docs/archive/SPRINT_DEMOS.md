# Sprint Demo Milestones

## Purpose

Each sprint ends with a stakeholder demo showing **working software**, not slides. This document defines exactly what we'll demonstrate at each milestone.

---

## Sprint 1: Core MVP (3 weeks)

### Demo Date: End of Week 3

### What Stakeholder Will See

**Opening Scene:**

```
Stakeholder opens browser → http://localhost:3000
```

**Screen shows:**

```
┌─────────────────────────────────────────┐
│     Today's Timelapses - Sept 30        │
├─────────────────────────────────────────┤
│                                         │
│  🌅 Sunrise (6:23am - 7:23am)          │
│     [▶ Play Video] [Progress bar]      │
│     47 images captured                  │
│                                         │
│  ☀️ Daytime (9:00am - 3:00pm)          │
│     [▶ Play Video] [Progress bar]      │
│     73 images captured                  │
│                                         │
│  🌇 Sunset (5:47pm - 6:47pm)           │
│     [▶ Play Video] [Progress bar]      │
│     45 images captured                  │
│                                         │
└─────────────────────────────────────────┘
```

**Live Demo Flow (5 minutes):**

1. **Click "Sunrise" play button**

   - Video plays showing smooth sunrise timelapse
   - 30-second video compressed from 1 hour of captures
   - Exposure gradually brightens as sun rises
   - Stacked images = clean, noise-free quality

2. **Click "Daytime" play button**

   - Timelapse shows 6 hours compressed to ~1 minute
   - Consistent exposure throughout (bright sunny day)
   - Clouds moving, shadows shifting

3. **Click "Sunset" play button**

   - Sunset timelapse shows fading light
   - Exposure adjusts smoothly as it gets darker
   - Stacked images = beautiful rich colors

4. **Open Settings page**

   - Show current location (lat/lon)
   - Show calculated sunrise/sunset times for today
   - Change location → times update immediately

5. **Show backend logs (terminal)**

   ```
   [09:00:00] ✓ Daytime capture triggered (ISO 100, 1/500s)
   [09:05:00] ✓ Daytime capture triggered (ISO 100, 1/500s)
   [09:10:00] ✓ Daytime capture triggered (ISO 100, 1/500s)
   ```

6. **Show real Raspberry Pi capturing live**
   - SSH into Pi
   - Show capture service running: `systemctl status capture-service`
   - Trigger manual capture: `curl http://helios.local:8080/capture`
   - See image appear in backend seconds later

### Key Messages for Stakeholder

✅ **"The core product works end-to-end"**

- System automatically captures photos all day
- Processes them into beautiful timelapses
- User just opens the app and watches

✅ **"Smart exposure is working"**

- Sunrise starts dark, ends bright
- Daytime is consistently exposed
- Sunset gracefully fades

✅ **"Image stacking delivers quality"**

- Sunrise/sunset videos are noticeably cleaner
- No noise or grain even in low light

✅ **"Deployment is simple"**

- One command to update Pi: `./scripts/deploy-pi.sh`
- Docker handles all backend/frontend updates

### What Stakeholder CANNOT See Yet

❌ Historical videos (only today)
❌ Multiple cameras
❌ Weather integration
❌ Cloud storage/sharing
❌ Mobile app

**Message:** "These are intentionally deferred. We built the simplest thing that delivers value first."

---

## Sprint 2: Polish & Reliability (2 weeks)

### Demo Date: End of Week 5 (from project start)

### What Stakeholder Will See

**New Feature 1: Historical View**

```
┌─────────────────────────────────────────┐
│  [< Sept 29]  Today: Sept 30  [Oct 1 >]│
├─────────────────────────────────────────┤
│  Week View:                             │
│  Mon Tue Wed Thu Fri Sat Sun            │
│   ✓   ✓   ✓   ✓   ✓   ✓   ✓            │
│                                         │
│  Click any day to see those timelapses  │
└─────────────────────────────────────────┘
```

**Live Demo Flow:**

1. Browse to yesterday, watch previous sunrise
2. Click through last 7 days of timelapses
3. Show automatic cleanup of old images (disk management)

**New Feature 2: System Health Dashboard**

```
┌─────────────────────────────────────────┐
│  System Status                          │
├─────────────────────────────────────────┤
│  Camera: 🟢 Online (helios.local)       │
│  Backend: 🟢 Running (4 days uptime)    │
│  Storage: 2.3 GB / 32 GB (7%)           │
│                                         │
│  Next Capture: 5:47pm (sunset)          │
│  Today's Stats:                         │
│  - 165 images captured                  │
│  - 3 videos generated                   │
│  - 0 failed captures                    │
└─────────────────────────────────────────┘
```

**New Feature 3: Error Recovery**

```
Demonstrate system resilience:
1. Unplug Raspberry Pi (simulate network failure)
2. Show frontend indicates "Camera offline"
3. Plug Pi back in
4. Show automatic reconnection and resumed captures
5. No data lost (Pi buffered images locally)
```

**New Feature 4: Improved Image Quality**

```
Show side-by-side comparison:
- Sprint 1 sunset (5-frame stacking)
- Sprint 2 sunset (10-frame stacking + better alignment)
- Noticeably sharper and cleaner
```

### Key Messages for Stakeholder

✅ **"System is production-ready"**

- Runs for weeks without intervention
- Gracefully handles failures
- Automatically recovers from network issues

✅ **"Quality improved significantly"**

- Better stacking algorithm
- Sharper final videos
- More consistent exposure

✅ **"Easy to monitor and debug"**

- Health dashboard shows what's happening
- Clear status indicators
- Logs are comprehensive

### What's Still Deferred

❌ Custom schedules (still hardcoded 3 schedules)
❌ Manual captures
❌ Multiple cameras
❌ Weather gating

---

## Sprint 3: Advanced Features (2-3 weeks)

### Demo Date: End of Week 8

### What Stakeholder Will See

**New Feature 1: Custom Schedules**

```
┌─────────────────────────────────────────┐
│  My Schedules                           │
├─────────────────────────────────────────┤
│  🌅 Sunrise          [Edit] [Delete]    │
│  ☀️ Daytime          [Edit] [Delete]    │
│  🌇 Sunset           [Edit] [Delete]    │
│                                         │
│  [+ Create New Schedule]                │
└─────────────────────────────────────────┘
```

**Live Demo: Create Custom Schedule**

```
1. Click "Create New Schedule"
2. Name: "Golden Hour"
3. Type: Time-based
4. Start: 4:00pm
5. End: 6:00pm
6. Interval: 60 seconds
7. Save
8. Tomorrow's captures include "Golden Hour" timelapse
```

**New Feature 2: Weather Integration**

```
┌─────────────────────────────────────────┐
│  Today's Forecast                       │
├─────────────────────────────────────────┤
│  6:00am - Cloudy (sunrise will be gray)│
│  12:00pm - Sunny ☀️                     │
│  6:00pm - Clear (great sunset!)         │
│                                         │
│  ⚙️ Weather-gated schedules:            │
│  ☑ Skip captures if 100% overcast       │
│  ☑ Notify if sunset will be spectacular│
└─────────────────────────────────────────┘
```

**New Feature 3: Manual Capture**

```
Show "Capture Now" button:
1. Click button
2. Select preset (sunrise/daytime/sunset)
3. Image captured immediately
4. Appears in gallery within seconds
5. Can include in next video generation
```

**New Feature 4: Notifications**

```
Demonstrate:
- Email/SMS when sunrise video is ready
- Alert if camera goes offline
- Notify if spectacular sunset is predicted
- Daily summary of captures
```

### Key Messages for Stakeholder

✅ **"System is now flexible"**

- User can create custom schedules for specific needs
- Not limited to sunrise/daytime/sunset
- Weather-aware to avoid wasted captures

✅ **"User has control"**

- Manual capture for special moments
- Notifications keep user informed
- Can fine-tune every schedule parameter

---

## Sprint 4+: Scale & Polish

### Potential Demo Features (Prioritized by Stakeholder Feedback)

**Option A: Multiple Cameras**

```
Show two Raspberry Pis capturing simultaneously:
- North-facing camera (sunrise)
- West-facing camera (sunset)
- Both appear in UI as separate camera sources
- Synchronized captures
```

**Option B: Cloud Storage & Sharing**

```
- Videos automatically backup to S3/Cloudflare
- Shareable links: "Check out today's sunrise!"
- Embeddable player for social media
- Mobile-friendly viewer
```

**Option C: Advanced Processing**

```
- Deflickering (remove exposure variations)
- Motion stabilization
- 4K video output
- HDR bracketing for better dynamic range
```

**Option D: Analytics**

```
- Heatmap of best sunrise/sunset times
- Comparison across weeks/months
- Weather correlation (clear vs cloudy)
- Time-of-year variations
```

---

## Demo Best Practices

### Before Each Demo

1. **Run the system for 3+ days** to have real data
2. **Capture at least one full sunrise and sunset** for quality demo
3. **Test the demo flow** the day before (rehearse)
4. **Have backup videos** in case of weather (cloudy days)
5. **Prepare rollback** in case demo environment breaks

### During Demo

1. **Start with the user story**: "Imagine you wake up and want to see this morning's sunrise..."
2. **Show, don't tell**: Click through the actual UI, don't use slides
3. **Highlight the 'wow' moment**: Play the sunrise timelapse first (most impressive)
4. **Address stakeholder's last feedback**: "You asked for X, here it is"
5. **Be honest about limitations**: "We intentionally didn't build Y yet because..."

### After Demo

1. **Gather feedback immediately**: "What did you think?"
2. **Prioritize requests**: "If you could only have one new feature, which?"
3. **Set expectations for next sprint**: "We'll demo again in 2 weeks"
4. **Document decisions**: Update backlog based on feedback

---

## Stakeholder Feedback Template

After each demo, ask:

1. **What surprised you (good or bad)?**
2. **What would make this more useful to you?**
3. **What features can we cut or defer?**
4. **Would you use this daily? Weekly? Why/why not?**
5. **Who else should see this?**

---

## Success: The Ultimate Demo

**End of Project Demo (Sprint 5-6)**

Stakeholder arrives at your home/office. You show them:

```
1. Open app on laptop
2. See 30 days of timelapses
3. Pick a random day, watch all three videos
4. Videos are beautiful, smooth, perfectly exposed

5. Walk over to window
6. Point at Raspberry Pi on tripod
7. Say: "That's been capturing photos every day for a month"
8. Say: "I haven't touched it once"

9. Open settings
10. Change location to Tokyo
11. Say: "If I shipped this Pi to Japan, it would just work"

12. Look at stakeholder
13. Ask: "Want one for your house?"
```

**That's the demo that matters.** Simple. Reliable. Delightful.

---

## Appendix: Demo Checklist

### Technical Setup

- [ ] All Docker containers running and healthy
- [ ] Pi connected and capturing (at least 1 day of data)
- [ ] At least 3 complete timelapses available
- [ ] Frontend loads in <2 seconds
- [ ] Videos play without buffering
- [ ] No errors in browser console
- [ ] Backend logs are clean (no warnings/errors)

### Content Preparation

- [ ] At least one beautiful sunrise timelapse
- [ ] At least one beautiful sunset timelapse
- [ ] Daytime timelapse with interesting content (clouds, people, etc.)
- [ ] Settings page configured with correct location
- [ ] System has been running for 3+ days (proves reliability)

### Presentation

- [ ] Rehearsed demo flow (< 10 minutes)
- [ ] Prepared talking points for each feature
- [ ] Ready to answer: "What's next?" and "When can I have this?"
- [ ] Backup plan if internet/network fails
- [ ] Feedback form or questions prepared

### Environment

- [ ] Large screen or projector for stakeholder to see clearly
- [ ] Good lighting for showing Raspberry Pi hardware
- [ ] Quiet space with no interruptions
- [ ] Have water/coffee available (longer demos)

---

**Remember: The best demos are simple, confident, and focused on user value, not technical complexity.**
