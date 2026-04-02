# Montex - Lightweight Server Monitoring Application

## Project Overview

**Project Name:** Montex  
**Type:** Web Application (Flask)  
**Core Functionality:** A lightweight self-hosted server monitoring tool that connects to remote servers via SSH, collects CPU, memory, and storage metrics, displays them in a web dashboard, and sends Telegram notifications when thresholds are exceeded.  
**Target Users:** System administrators, DevOps engineers, and developers who need to monitor remote servers.

---

## UI/UX Specification

### Layout Structure

**Page Sections:**
1. **Header** - App logo/name, navigation
2. **Sidebar** - Server list, add server button
3. **Main Content** - Dashboard with metrics cards, charts
4. **Settings Panel** - Telegram configuration, threshold settings

**Grid/Flex Layout:**
- Sidebar: Fixed width 280px on desktop
- Main content: Flexible grid with metric cards
- Cards: CSS Grid with auto-fit columns (min 300px)

**Responsive Breakpoints:**
- Desktop: > 1024px (sidebar visible)
- Tablet: 768px - 1024px (collapsible sidebar)
- Mobile: < 768px (hamburger menu, stacked cards)

### Visual Design

**Color Palette:**
- Background Dark: `#0d1117`
- Surface: `#161b22`
- Surface Elevated: `#21262d`
- Border: `#30363d`
- Primary: `#58a6ff` (blue accent)
- Success: `#3fb950` (green)
- Warning: `#d29922` (amber)
- Danger: `#f85149` (red)
- Text Primary: `#f0f6fc`
- Text Secondary: `#8b949e`

**Typography:**
- Font Family: `"JetBrains Mono", "Fira Code", monospace` for data
- Font Family: `"IBM Plex Sans", system-ui, sans-serif` for UI
- Headings: 24px (h1), 20px (h2), 16px (h3)
- Body: 14px
- Data/Metrics: 32px (large), 18px (small)

**Spacing System:**
- Base unit: 8px
- Card padding: 24px
- Gap between cards: 16px
- Section margins: 32px

**Visual Effects:**
- Card shadows: `0 4px 12px rgba(0,0,0,0.4)`
- Hover transitions: 200ms ease
- Subtle glow on critical alerts: `0 0 20px rgba(248,81,73,0.3)`
- Glassmorphism on modals: `backdrop-filter: blur(8px)`

### Components

**1. Server Card**
- Server name, IP address, status indicator (online/offline)
- Last check timestamp
- Quick metrics preview (CPU%, Memory%)
- States: normal, warning, critical, offline

**2. Metric Card**
- Icon, metric name, current value
- Progress bar showing usage percentage
- Threshold indicator line
- States: normal (green), warning (amber), critical (red)

**3. Server Detail Modal**
- Full metrics display with charts
- Historical data (last 24h mini sparklines)
- Edit/delete server buttons

**4. Add Server Form**
- Server name, IP/hostname, SSH port
- SSH username, authentication method (password/key)
- Credentials (encrypted storage)
- Test connection button

**5. Settings Panel**
- Telegram bot token input (masked)
- Chat ID input
- Threshold sliders (CPU, Memory, Storage)
- Test notification button

**6. Navigation**
- Dashboard (home)
- Servers list
- Settings
- About

---

## Functionality Specification

### Core Features

**1. Server Management**
- Add/Edit/Remove remote servers via SSH
- Store server configurations (encrypted credentials)
- Group servers by tags (optional)
- Test SSH connection before saving

**2. Metric Collection**
- **CPU:** Overall CPU usage percentage
- **Memory:** Used/Total RAM with percentage
- **Storage:** Disk usage per partition with percentage
- Collection interval: configurable (default 60 seconds)
- Parallel collection using thread pool

**3. Data Display**
- Real-time dashboard with auto-refresh
- Individual server detail view
- Sortable server list
- Filter by status (all/online/warning/critical)
- Search servers by name

**4. Threshold & Alerts**
- Configurable thresholds per metric (CPU, Memory, Storage)
- Default thresholds: CPU 80%, Memory 85%, Storage 90%
- Visual indicators when threshold exceeded
- Alert history log

**5. Telegram Notifications**
- User configurable bot token and chat ID
- Notification on threshold breach
- Notification on server offline
- Notification when server comes back online
- Test notification button

### User Interactions

1. **Adding a Server:**
   - Click "Add Server" button
   - Fill form with SSH details
   - Test connection
   - Save server

2. **Viewing Metrics:**
   - Click server card to see details
   - View current metrics
   - See historical mini-charts

3. **Configuring Alerts:**
   - Navigate to Settings
   - Enter Telegram bot token
   - Enter chat ID
   - Adjust threshold sliders
   - Test notification

### Data Handling

- **Storage:** SQLite database (montex.db)
- **Tables:** servers, metrics_history, settings, alerts
- **Credentials:** Encrypted with Fernet (symmetric encryption)
- **Metrics History:** Keep last 24 hours per server

### Edge Cases

- SSH connection timeout/failure → mark server as offline
- Invalid credentials → show error, don't save
- Telegram token invalid → show validation error
- Server unreachable → retry 3 times before marking offline
- Duplicate server entry → prevent with validation

---

## Technical Architecture

### Backend (Flask)

```
montex/
├── app.py                 # Main Flask application
├── config.py              # Configuration
├── models.py              # Database models
├── ssh_client.py          # SSH connection handling
├── metrics_collector.py   # Metrics collection logic
├── telegram_bot.py        # Telegram notifications
├── encryptor.py           # Credential encryption
├── utils.py               # Utility functions
├── templates/
│   └── index.html         # Main HTML template
├── static/
│   ├── css/
│   │   └── style.css      # Styles
│   └── js/
│       └── app.js         # Frontend JS
└── requirements.txt       # Dependencies
```

### API Endpoints

- `GET /` - Main dashboard
- `GET /api/servers` - List all servers
- `POST /api/servers` - Add new server
- `PUT /api/servers/<id>` - Update server
- `DELETE /api/servers/<id>` - Remove server
- `GET /api/servers/<id>/metrics` - Get server metrics
- `GET /api/settings` - Get settings
- `POST /api/settings` - Update settings
- `POST /api/test-telegram` - Test Telegram notification

---

## Acceptance Criteria

### Visual Checkpoints
- [ ] Dark theme with #0d1117 background renders correctly
- [ ] Server cards display with proper styling and status colors
- [ ] Metric cards show progress bars with correct threshold markers
- [ ] Responsive layout works on mobile/tablet/desktop
- [ ] Animations and transitions are smooth

### Functional Checkpoints
- [ ] Can add a new server with SSH credentials
- [ ] Can test SSH connection before saving
- [ ] Metrics (CPU, Memory, Storage) display correctly
- [ ] Auto-refresh updates metrics every 60 seconds
- [ ] Threshold warnings show with correct colors
- [ ] Can configure Telegram bot token and chat ID
- [ ] Telegram notification fires when threshold exceeded
- [ ] Server offline notification sent via Telegram
- [ ] Settings persist after app restart

### Performance
- [ ] Page loads in under 2 seconds
- [ ] Metrics refresh without page reload (AJAX)
- [ ] Support monitoring up to 50 servers

---

## Security Considerations

- SSH credentials encrypted at rest
- No plain-text passwords in database
- CSRF protection on forms
- Secure session management
- Input sanitization for all user inputs