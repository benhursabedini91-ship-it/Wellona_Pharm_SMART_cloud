# Design System - Orders Pro Plus UI

**Project**: WPH AI Order Management  
**Last Updated**: November 6, 2025  
**Version**: 3.0

---

## Color Palette

### Dark Theme (Primary)

**Core Colors**
```css
:root {
  --bg: #0f172a;              /* Slate 900 - Main background */
  --panel: #1e293b;           /* Slate 800 - Cards, panels */
  --border: #334155;          /* Slate 700 - Borders, dividers */
  --hover: #475569;           /* Slate 600 - Hover states */
  
  --text: #e2e8f0;            /* Slate 200 - Primary text */
  --text-secondary: #94a3b8;  /* Slate 400 - Secondary text */
  --text-muted: #64748b;      /* Slate 500 - Muted text */
  
  --primary: #3b82f6;         /* Blue 500 - Primary actions */
  --primary-hover: #2563eb;   /* Blue 600 - Primary hover */
  --primary-active: #1d4ed8;  /* Blue 700 - Primary active */
  
  --success: #10b981;         /* Emerald 500 - Success, approve */
  --success-hover: #059669;   /* Emerald 600 - Success hover */
  
  --warning: #f59e0b;         /* Amber 500 - Warnings */
  --warning-hover: #d97706;   /* Amber 600 - Warning hover */
  
  --danger: #ef4444;          /* Red 500 - Danger, delete */
  --danger-hover: #dc2626;    /* Red 600 - Danger hover */
  
  --chip: #1e293b;            /* Slate 800 - Filter chips */
  --skeleton: #334155;        /* Slate 700 - Loading skeleton */
}
```

**Semantic Colors**
```css
:root {
  /* Status Colors */
  --status-ordered: #3b82f6;     /* Blue - Ordered */
  --status-delivered: #10b981;   /* Green - Delivered */
  --status-pending: #f59e0b;     /* Amber - Pending */
  --status-cancelled: #ef4444;   /* Red - Cancelled */
  
  /* Data Visualization */
  --chart-1: #3b82f6;  /* Blue */
  --chart-2: #10b981;  /* Green */
  --chart-3: #f59e0b;  /* Amber */
  --chart-4: #8b5cf6;  /* Purple */
  --chart-5: #ec4899;  /* Pink */
  
  /* Highlights */
  --highlight-yellow: rgba(251, 191, 36, 0.2);  /* Yellow with opacity */
  --highlight-blue: rgba(59, 130, 246, 0.2);    /* Blue with opacity */
  --highlight-red: rgba(239, 68, 68, 0.2);      /* Red with opacity */
}
```

### Light Theme (Alternative)

```css
:root[data-theme="light"] {
  --bg: #ffffff;              /* White background */
  --panel: #f8fafc;           /* Slate 50 - Cards */
  --border: #e2e8f0;          /* Slate 200 - Borders */
  --hover: #cbd5e1;           /* Slate 300 - Hover */
  
  --text: #0f172a;            /* Slate 900 - Primary text */
  --text-secondary: #475569;  /* Slate 600 - Secondary text */
  --text-muted: #94a3b8;      /* Slate 400 - Muted text */
  
  /* Action colors remain same for consistency */
  --primary: #3b82f6;
  --primary-hover: #2563eb;
  --success: #10b981;
  --danger: #ef4444;
}
```

---

## Typography

### Font Families

**Primary**: System Font Stack
```css
font-family: -apple-system, BlinkMacSystemFont, 
             "Segoe UI", Roboto, "Helvetica Neue", 
             Arial, sans-serif, 
             "Apple Color Emoji", "Segoe UI Emoji";
```

**Monospace**: Code/Numbers
```css
font-family: "Fira Code", "Courier New", 
             Consolas, Monaco, monospace;
```

### Type Scale

```css
/* Headings */
.h1 { font-size: 32px; line-height: 40px; font-weight: 700; }
.h2 { font-size: 24px; line-height: 32px; font-weight: 700; }
.h3 { font-size: 20px; line-height: 28px; font-weight: 600; }
.h4 { font-size: 18px; line-height: 26px; font-weight: 600; }
.h5 { font-size: 16px; line-height: 24px; font-weight: 600; }
.h6 { font-size: 14px; line-height: 20px; font-weight: 600; }

/* Body Text */
.body-lg   { font-size: 18px; line-height: 28px; font-weight: 400; }
.body      { font-size: 14px; line-height: 20px; font-weight: 400; }
.body-sm   { font-size: 12px; line-height: 18px; font-weight: 400; }
.body-xs   { font-size: 10px; line-height: 16px; font-weight: 400; }

/* Labels */
.label     { font-size: 14px; line-height: 20px; font-weight: 500; }
.label-sm  { font-size: 12px; line-height: 18px; font-weight: 500; }

/* Code/Numbers */
.code      { font-size: 14px; line-height: 20px; font-family: monospace; }
```

### Font Weights
- **Regular**: 400 (body text)
- **Medium**: 500 (labels, subtle emphasis)
- **Semibold**: 600 (headings, buttons)
- **Bold**: 700 (major headings, important numbers)

---

## Spacing System

### Spacing Scale (4px base unit)

```css
--space-0: 0px;      /* No spacing */
--space-1: 4px;      /* xs */
--space-2: 8px;      /* sm */
--space-3: 12px;     /* md */
--space-4: 16px;     /* lg */
--space-5: 20px;     /* xl */
--space-6: 24px;     /* 2xl */
--space-8: 32px;     /* 3xl */
--space-10: 40px;    /* 4xl */
--space-12: 48px;    /* 5xl */
--space-16: 64px;    /* 6xl */
--space-20: 80px;    /* 7xl */
```

### Component Spacing

**Container Padding**
- Desktop: 16px (--space-4)
- Tablet: 12px (--space-3)
- Mobile: 8px (--space-2)

**Component Gaps**
- Between filters: 12px
- Between buttons: 8px
- Between rows: 8px
- Between sections: 24px

**Table Spacing**
- Cell padding: 12px 16px
- Row height: 48px (min)
- Header height: 56px

---

## Layout Grid

### Breakpoints

```css
/* Mobile first approach */
--breakpoint-sm: 640px;   /* Small devices */
--breakpoint-md: 768px;   /* Tablets */
--breakpoint-lg: 1024px;  /* Laptops */
--breakpoint-xl: 1280px;  /* Desktops */
--breakpoint-2xl: 1536px; /* Large screens */
```

### Container Widths

```css
.container {
  width: 100%;
  margin: 0 auto;
  padding: 0 var(--space-4);
}

@media (min-width: 640px) {
  .container { max-width: 640px; }
}
@media (min-width: 768px) {
  .container { max-width: 768px; }
}
@media (min-width: 1024px) {
  .container { max-width: 1024px; }
}
@media (min-width: 1280px) {
  .container { max-width: 1280px; }
}
```

### Grid System

```css
.grid {
  display: grid;
  gap: var(--space-4);
}

/* Common layouts */
.grid-2 { grid-template-columns: repeat(2, 1fr); }
.grid-3 { grid-template-columns: repeat(3, 1fr); }
.grid-4 { grid-template-columns: repeat(4, 1fr); }

/* Responsive */
@media (max-width: 768px) {
  .grid-2, .grid-3, .grid-4 {
    grid-template-columns: 1fr;
  }
}
```

---

## Components

### Buttons

```css
/* Base Button */
.btn {
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid transparent;
}

/* Primary Button */
.btn-primary {
  background: var(--primary);
  color: white;
  border-color: var(--primary);
}
.btn-primary:hover {
  background: var(--primary-hover);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

/* Success Button */
.btn-success {
  background: var(--success);
  color: white;
  border-color: var(--success);
}
.btn-success:hover {
  background: var(--success-hover);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
}

/* Ghost Button */
.btn-ghost {
  background: transparent;
  color: var(--text);
  border-color: var(--border);
}
.btn-ghost:hover {
  background: var(--panel);
  border-color: var(--hover);
}

/* Sizes */
.btn-sm { padding: 6px 12px; font-size: 12px; }
.btn-md { padding: 10px 20px; font-size: 14px; }
.btn-lg { padding: 12px 24px; font-size: 16px; }
```

### Input Fields

```css
/* Base Input */
.input {
  padding: 10px 14px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg);
  color: var(--text);
  font-size: 14px;
  transition: all 0.2s ease;
}

.input:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.input::placeholder {
  color: var(--text-muted);
}

/* Sizes */
.input-sm { padding: 6px 10px; font-size: 12px; }
.input-md { padding: 10px 14px; font-size: 14px; }
.input-lg { padding: 12px 16px; font-size: 16px; }
```

### Cards

```css
.card {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: var(--space-4);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.card-hover:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.15);
  border-color: var(--primary);
  transition: all 0.3s ease;
}
```

### Tables

```css
.table {
  width: 100%;
  border-collapse: collapse;
  background: var(--panel);
}

.table th {
  padding: 16px;
  text-align: left;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--text-secondary);
  border-bottom: 2px solid var(--border);
  position: sticky;
  top: 0;
  background: var(--panel);
  z-index: 10;
}

.table td {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
  color: var(--text);
}

.table tr:hover {
  background: var(--hover);
}

.table tr.edited {
  background: rgba(59, 130, 246, 0.1);
  border-left: 3px solid var(--primary);
}
```

### Chips/Tags

```css
.chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: var(--chip);
  border: 1px solid var(--border);
  border-radius: 20px;
  font-size: 12px;
  color: var(--text-secondary);
}

.chip .close {
  cursor: pointer;
  opacity: 0.6;
  transition: opacity 0.2s;
}

.chip .close:hover {
  opacity: 1;
  color: var(--danger);
}
```

### Modals

```css
.modal {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.modal-pane {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: var(--space-6);
  max-width: 600px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.3);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-4);
}

.modal-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text);
}

.modal-close {
  cursor: pointer;
  color: var(--text-secondary);
  font-size: 24px;
  line-height: 1;
}

.modal-close:hover {
  color: var(--text);
}
```

---

## Icons & Emoji

### Current System: Emoji-based

**Benefits:**
- No external dependencies
- Universal support
- Instant visual recognition

**Icon Map:**
```
🔍 - Search
📅 - Calendar/Date
⏳ - Time/Duration
🏢 - Supplier/Organization
📥 - Download/Import
📊 - Export/Reports
✅ - Approve/Success
❌ - Cancel/Delete
⚙️ - Settings
📋 - List/Orders
🔄 - Refresh/Sync
👤 - User/Person
🔔 - Notifications
⚠️ - Warning
ℹ️ - Information
```

### Alternative: Lucide Icons

If switching from emoji:

```html
<script src="https://unpkg.com/lucide@latest"></script>
<script>
  lucide.createIcons();
</script>

<!-- Usage -->
<i data-lucide="search"></i>
<i data-lucide="calendar"></i>
<i data-lucide="download"></i>
```

**Size Guidelines:**
- Small: 16px (inline text)
- Medium: 20px (buttons, chips)
- Large: 24px (headings, prominent actions)
- XL: 32px (empty states, illustrations)

---

## Animation & Transitions

### Timing Functions

```css
:root {
  --ease-in: cubic-bezier(0.4, 0, 1, 1);
  --ease-out: cubic-bezier(0, 0, 0.2, 1);
  --ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);
  --bounce: cubic-bezier(0.68, -0.55, 0.265, 1.55);
}
```

### Durations

```css
:root {
  --duration-fast: 150ms;
  --duration-base: 200ms;
  --duration-slow: 300ms;
  --duration-slower: 500ms;
}
```

### Common Transitions

```css
/* Hover Effects */
.hover-lift {
  transition: transform var(--duration-base) var(--ease-out);
}
.hover-lift:hover {
  transform: translateY(-2px);
}

/* Color Transitions */
.color-transition {
  transition: color var(--duration-base) var(--ease-in-out),
              background var(--duration-base) var(--ease-in-out);
}

/* Scale Effect */
.scale-hover {
  transition: transform var(--duration-base) var(--ease-out);
}
.scale-hover:hover {
  transform: scale(1.05);
}

/* Fade In */
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.fade-in {
  animation: fadeIn var(--duration-base) var(--ease-out);
}

/* Skeleton Loading */
@keyframes skeleton-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.skeleton {
  background: var(--skeleton);
  animation: skeleton-pulse 2s var(--ease-in-out) infinite;
}
```

---

## Shadows & Elevation

```css
:root {
  /* Elevation Levels */
  --shadow-xs: 0 1px 2px rgba(0, 0, 0, 0.05);
  --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.1),
               0 1px 2px rgba(0, 0, 0, 0.06);
  --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.1),
               0 2px 4px rgba(0, 0, 0, 0.06);
  --shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.1),
               0 4px 6px rgba(0, 0, 0, 0.05);
  --shadow-xl: 0 20px 25px rgba(0, 0, 0, 0.15),
               0 10px 10px rgba(0, 0, 0, 0.04);
  --shadow-2xl: 0 25px 50px rgba(0, 0, 0, 0.25);
}

/* Component Shadows */
.card { box-shadow: var(--shadow-sm); }
.card-hover:hover { box-shadow: var(--shadow-lg); }
.modal-pane { box-shadow: var(--shadow-2xl); }
.dropdown { box-shadow: var(--shadow-md); }
```

---

## Border Radius

```css
:root {
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;
  --radius-2xl: 24px;
  --radius-full: 9999px;
}

/* Usage */
.btn { border-radius: var(--radius-md); }
.card { border-radius: var(--radius-lg); }
.chip { border-radius: var(--radius-full); }
.modal { border-radius: var(--radius-xl); }
```

---

## Accessibility

### Focus States

```css
/* Keyboard Focus Indicator */
:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

/* Remove default focus for mouse users */
:focus:not(:focus-visible) {
  outline: none;
}
```

### Screen Reader Only

```css
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}
```

### Contrast Ratios

**Minimum Requirements (WCAG AA):**
- Normal text: 4.5:1
- Large text (18px+): 3:1
- Interactive elements: 3:1

**Current Compliance:**
- `--text` on `--bg`: 11.2:1 ✅
- `--text-secondary` on `--bg`: 6.8:1 ✅
- `--primary` on `--bg`: 4.9:1 ✅

---

## Responsive Design

### Mobile First Approach

```css
/* Base styles for mobile */
.header {
  flex-direction: column;
  gap: var(--space-2);
}

/* Tablet and up */
@media (min-width: 768px) {
  .header {
    flex-direction: row;
    gap: var(--space-4);
  }
}

/* Desktop */
@media (min-width: 1024px) {
  .header {
    gap: var(--space-6);
  }
}
```

### Common Patterns

**Stacking Filters**
```css
/* Mobile: Stack vertically */
.filters {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

/* Desktop: Horizontal row */
@media (min-width: 768px) {
  .filters {
    flex-direction: row;
    flex-wrap: wrap;
  }
}
```

**Collapsible Sidebar**
```css
/* Mobile: Hidden by default */
.sidebar {
  position: fixed;
  left: -280px;
  transition: left 0.3s ease;
}

.sidebar.open {
  left: 0;
}

/* Desktop: Always visible */
@media (min-width: 1024px) {
  .sidebar {
    position: static;
    left: 0;
  }
}
```

---

## Browser Support

**Target Browsers:**
- Chrome/Edge: Last 2 versions ✅
- Firefox: Last 2 versions ✅
- Safari: Last 2 versions ✅
- Opera: Last 2 versions ✅

**Not Supported:**
- Internet Explorer 11 ❌

**Progressive Enhancement:**
- CSS Grid with Flexbox fallback
- CSS Variables with fallback values
- Modern JavaScript (ES6+) with polyfills if needed

---

## Resources

**Design Tools:**
- Figma: Component library
- Adobe XD: Prototypes
- Sketch: UI mockups

**Color Tools:**
- [Coolors.co](https://coolors.co) - Palette generator
- [Contrast Checker](https://webaim.org/resources/contrastchecker/) - WCAG compliance
- [ColorBox](https://colorbox.io) - Scale generator

**Icon Libraries:**
- [Lucide Icons](https://lucide.dev)
- [Heroicons](https://heroicons.com)
- [Feather Icons](https://feathericons.com)

**Fonts:**
- System fonts (current)
- [Inter](https://fonts.google.com/specimen/Inter) - Alternative
- [Fira Code](https://fonts.google.com/specimen/Fira+Code) - Monospace

---

**End of Design System**  
Version 3.0 | November 2025
