# Web Designer Handoff Package
## Orders Pro Plus UI - Template Creation Guide

**Project**: WPH AI Order Management System  
**Current Template**: `web_modern/public/orders_pro_plus.html`  
**Backend**: FastAPI (Python) with PostgreSQL  
**Date**: November 2025

---

## 1. Backend API Documentation

### Primary Endpoint: `/api/orders`

**Method**: `GET`

**Parameters** (all via query string):
- `sales_window` (integer): Number of days to analyze for sales history (7-180)
- `target_days` (integer): Target days of stock to maintain (typically 28)
- `include_zero` (string): "1" = include products with zero sales, "0" = exclude
- `q` (string, optional): Search query for sifra/barkod/emri (name)
- `supplier` (array, optional): Filter by suppliers - can repeat parameter: `?supplier=PHOENIX&supplier=VEGA`

**Response Format**: JSON array of product objects

**Sample Response**:
```json
[
  {
    "sifra": "99575549",
    "emri": "CONTOUR PLUS TRAKE A50",
    "barkod": "5016003764004",
    "current_stock": 543,
    "avg_daily_sales": 62.42857,
    "days_cover": 8.7,
    "min_zaliha": 1747,
    "qty_to_order": 1746,
    "supplier_name": "PHOENIX"
  },
  {
    "sifra": "10002487",
    "emri": "PARACETAMOL 500MG TBL X20",
    "barkod": "8606001234567",
    "current_stock": 120,
    "avg_daily_sales": 4.2,
    "days_cover": 28.6,
    "min_zaliha": 118,
    "qty_to_order": 0,
    "supplier_name": "SOPHARMA"
  }
]
```

**Field Descriptions**:
- `sifra`: Internal product code (string)
- `emri`: Product name (string)
- `barkod`: Barcode / EAN (string)
- `current_stock`: Current inventory quantity (integer)
- `avg_daily_sales`: Average daily sales based on sales_window (decimal, 2-5 places)
- `days_cover`: How many days current stock will last (decimal)
- `min_zaliha`: Minimum recommended stock level (integer)
- `qty_to_order`: Quantity to order to reach target (integer)
- `supplier_name`: Selected supplier (PHOENIX | VEGA | SOPHARMA | FARMALOGIST | UNKNOWN)

### Download Endpoints

**CSV Export**: `/api/orders?<same params>&download=csv`  
**XLSX Export**: `/api/orders?<same params>&download=xlsx`

Both trigger file download with proper headers.

### Approval Endpoint: `/api/orders/{supplier}`

**Method**: `POST`  
**Path Parameter**: `supplier` (PHOENIX, VEGA, SOPHARMA, FARMALOGIST, or "ALL")  
**Body**: JSON object with edited quantities and approval metadata

**Sample Request Body**:
```json
{
  "orders": [
    {"sifra": "99575549", "qty": 1750, "supplier": "PHOENIX"},
    {"sifra": "10002487", "qty": 100, "supplier": "SOPHARMA"}
  ],
  "approved_by": "John Doe",
  "approval_date": "2025-11-06T14:30:00"
}
```

---

## 2. Business Logic

### Ordering Calculation
**Formula**: `qty_to_order = MAX(0, CEIL(avg_daily_sales × target_days) - current_stock)`

**Key Concepts**:
1. **Sales Window**: Historical period analyzed (7/15/30/60/180 days)
2. **Target Days**: How many days of stock we want to maintain
3. **Min Zaliha**: Minimum recommended stock = `avg_daily × target_days`
4. **Days Cover**: How long current stock will last = `current_stock ÷ avg_daily_sales`

### Supplier Selection
- System automatically selects **cheapest supplier** for each product
- Uses PostgreSQL `DISTINCT ON` with `ORDER BY price ASC NULLS LAST`
- Frontend allows filtering by specific suppliers

### Date Range Flexibility
- **Original**: Fixed dropdown (7/30/60/180 days)
- **New**: Date pickers (from/to) with dynamic `sales_window` calculation
- **Calculation**: `Math.ceil((date_to - date_from) / (1000 * 60 * 60 * 24))`

### Computed Columns
- **AVG/D**: Daily average from selected sales window
- **AVG/30D**: Monthly average = `avg_daily_sales × 30`
- **AVG/WINDOW**: Custom window average = `avg_daily_sales × sales_window_days`

---

## 3. Current UI Structure

### Layout Overview
```
┌─────────────────────────────────────────────────┐
│  SIDEBAR (collapsible)                          │
│  - Logo                                         │
│  - Navigation links                             │
│  - Export buttons                               │
│  - Health checks                                │
└─────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────┐
│  HEADER                                         │
│  Row 1: [Large Search] [Include Zero ☑] [Refresh]│
│  Row 2: [📅 Date From] [📅 Date To] [⏳ Target] [🏢 Suppliers]│
│  Row 3:                   [📥 CSV] [📊 XLSX] [✅ Approve]│
└─────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────┐
│  FILTER CHIPS (active filters)                  │
└─────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────┐
│  TABLE                                          │
│  - Sticky header                                │
│  - Editable qty_to_order column                 │
│  - Row highlighting for edited values           │
└─────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────┐
│  FOOTER (totals bar)                            │
│  Total Rows | Total Qty | Total Stock           │
└─────────────────────────────────────────────────┘
```

### Key Features
1. **Column Visibility Toggle**: Modal to show/hide columns
2. **Saved Views**: Save and load filter combinations
3. **Editable Cells**: Inline editing for qty_to_order
4. **Search**: Real-time search across sifra/barkod/emri
5. **Supplier Multiselect**: Filter by one or more suppliers
6. **Export**: CSV and XLSX download with current filters applied
7. **Approve**: Submit orders with approval metadata

### Color Scheme (Dark Theme)
```css
:root {
  --bg: #0f172a;           /* Background */
  --panel: #1e293b;        /* Panel background */
  --border: #334155;       /* Borders */
  --text: #e2e8f0;         /* Primary text */
  --text-secondary: #94a3b8; /* Secondary text */
  --primary: #3b82f6;      /* Primary action */
  --primary-hover: #2563eb;
  --success: #10b981;      /* Approve button */
  --danger: #ef4444;       /* Delete/Cancel */
  --chip: #1e293b;         /* Filter chips */
  --skeleton: #334155;     /* Loading skeleton */
}
```

### Typography
- **Body Font**: System stack: `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`
- **Search Field**: 15px, padding 12px 16px
- **Table Headers**: 14px, uppercase, font-weight 600
- **Table Cells**: 14px

### Spacing
- **Container Padding**: 16px
- **Row Gap**: 12px (primary rows), 8px (tertiary row)
- **Component Gap**: 12px (filters), 8px (buttons)

---

## 4. CSS Framework

**Primary**: Tailwind CSS (via CDN)
```html
<link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
```

**Custom CSS**: Inline in `<style>` block (lines 15-115 in orders_pro_plus.html)

**Icons**: Emoji-based (🔍 📅 ⏳ 🏢 📥 📊 ✅)  
Alternative: [Lucide Icons](https://lucide.dev/) can be integrated

---

## 5. JavaScript State Management

### Global State Object
```javascript
const state = {
  rows: [],           // Array of order objects from API
  columns: [],        // Array of column definitions
  edits: {},          // Object tracking edited quantities {sifra: {qty: newValue}}
  windowDays: 30      // Current sales_window from date calculation
};
```

### Key Functions
- `paramsBase()`: Builds URLSearchParams from form inputs, calculates sales_window
- `fetchOrders()`: Fetches data from API and updates state
- `renderAll()`: Renders header, rows, totals, and chips
- `currentFilters()` / `setFilters()`: Save/load filter configurations
- `effectiveQty(row)`: Returns edited qty if exists, otherwise DB value

### Local Storage
- `orders.columns.v1`: Saved column visibility configuration
- `orders.views.v1`: Named filter presets

---

## 6. Sample Data

### Typical Dataset Size
- **Total Products**: ~4,700 products with sales history
- **Products Needing Order**: ~76 (qty_to_order > 0)
- **Response Time**: 200-500ms for full dataset

### Supplier Distribution (sample)
```
PHOENIX:       21 products
VEGA:          12 products
SOPHARMA:      18 products
FARMALOGIST:   18 products
UNKNOWN:        7 products (no supplier price available)
```

### Edge Cases to Consider
- Products with `avg_daily_sales = 0` (no sales)
- Products with `supplier_name = "UNKNOWN"` (no price in system)
- Products with `qty_to_order = 0` (sufficient stock)
- Large orders: `qty_to_order > 5000`
- Decimal sales: `avg_daily_sales = 0.142857`

---

## 7. File Structure

### What to Provide to Designer

**✅ SEND THESE FILES:**

1. **`web_modern/public/orders_pro_plus.html`**
   - Working template (704 lines)
   - Contains HTML structure, CSS, and JavaScript
   - Self-contained (no external dependencies except Tailwind CDN)

2. **`docs/WEB_DESIGNER_HANDOFF.md`** (this document)
   - Complete API documentation
   - Business logic explanation
   - UI specifications

3. **`docs/DB_INFRASTRUCTURE.md`**
   - Database schema overview
   - Context on data sources

4. **Color Palette Document** (`docs/DESIGN_SYSTEM.md` - create this):
   ```
   Primary Colors:
   - Background: #0f172a
   - Panel: #1e293b
   - Primary Action: #3b82f6
   - Success: #10b981
   - Danger: #ef4444
   
   Typography Scale:
   - Heading 1: 24px, 700
   - Heading 2: 18px, 600
   - Body: 14px, 400
   - Small: 12px, 400
   ```

5. **Sample API Responses** (JSON files):
   - `docs/samples/api_orders_sample.json` (20-30 rows)
   - `docs/samples/api_orders_filtered.json` (filtered by supplier)
   - `docs/samples/api_orders_search.json` (search results)

**❌ DO NOT SEND:**
- `web_modern/app_v2.py` (backend source code - security risk)
- `sql/*.sql` (database scripts - unnecessary for designer)
- `.env` files or any files with credentials
- Python virtual environment folders

---

## 8. Designer Guidelines

### Creating New Templates

**Step 1: Copy Base Template**
```powershell
Copy-Item "web_modern\public\orders_pro_plus.html" "web_modern\public\orders_<template_name>.html"
```

**Step 2: Modify Structure**
- Keep same JavaScript state management
- Maintain same API call patterns
- Preserve `id` attributes for form inputs:
  - `id="q"` (search)
  - `id="date_from"` and `id="date_to"` (date pickers)
  - `id="target_days"` (target input)
  - `id="include_zero"` (checkbox)
  - `id="supplier"` (multiselect)
  - `id="btnFetch"` (refresh button)
  - `id="btnCsv"`, `id="btnXlsx"` (export buttons)
  - `id="btnApprove"` (approve button)

**Step 3: Customize Appearance**
- Change color scheme (CSS variables in `:root`)
- Modify layout (grid, flex, positioning)
- Add animations, transitions, hover effects
- Change typography (fonts, sizes, weights)

**Step 4: Test with Sample Data**
- Load sample JSON files into state.rows
- Verify table rendering
- Test search functionality
- Check responsive behavior

**Step 5: Register Route**
Backend needs new route in `app_v2.py`:
```python
@app.get("/ui/template_name")
async def serve_template_name():
    return FileResponse("public/orders_<template_name>.html")
```

### Design Considerations

**Responsive Breakpoints**:
- Desktop: > 1024px (primary target)
- Tablet: 768px - 1024px
- Mobile: < 768px (optional)

**Accessibility**:
- ARIA labels on interactive elements
- Keyboard navigation support (Tab, Enter, Escape)
- Focus indicators
- High contrast mode support

**Performance**:
- Avoid expensive animations on large tables (> 1000 rows)
- Use CSS transforms for smooth transitions
- Implement virtual scrolling for very large datasets (optional)

**Browser Support**:
- Chrome/Edge: Last 2 versions (primary)
- Firefox: Last 2 versions
- Safari: Last 2 versions
- IE11: Not supported

---

## 9. Additional Templates (Ideas)

### Template Variants to Consider

**1. Compact View**
- Smaller font sizes, reduced padding
- More rows visible per screen
- Minimal sidebar
- Target: Pharmacists who want to see maximum data

**2. Visual Dashboard**
- Cards instead of table
- Charts for sales trends
- Large KPI tiles
- Target: Managers who want overview

**3. Mobile-First View**
- Swipe gestures for actions
- Collapsible filters
- Bottom sheet for details
- Target: On-the-go ordering

**4. Split-Screen View**
- Left: Product list
- Right: Order form/details
- Target: Data entry specialists

**5. Kanban Board**
- Columns: "Need Order", "Ordered", "Delivered"
- Drag-and-drop between stages
- Target: Order workflow tracking

---

## 10. Support & Questions

**Technical Questions**: Contact backend team
- API changes or additions
- New fields needed
- Performance issues
- Database schema questions

**Design Questions**: Internal review
- Color palette approval
- Brand guidelines
- Accessibility requirements
- User feedback

**Deployment**: DevOps team
- Hosting new templates
- CDN configuration
- SSL certificates
- Load balancing

---

## 11. Version Control

**Current Version**: `orders_pro_plus.html` v3.0
- Date: November 2025
- Features: Date pickers, computed columns, checkbox filters
- Previous: `orders_ai.html` v2.0 (legacy, still available)

**Naming Convention**: `orders_<variant>_<version>.html`
- Example: `orders_compact_v1.html`, `orders_dashboard_v2.html`

**Git Repository**: (if applicable)
```
c:\Wellona\wphAI\
c:\Users\Lenovo\OneDrive\Documents\GitHub\wphAI\
```

---

## 12. Quick Start Checklist

**For Designer:**
- [ ] Received `orders_pro_plus.html` template
- [ ] Received API documentation (this file)
- [ ] Received sample JSON responses
- [ ] Received color palette/design system
- [ ] Access to staging environment for testing
- [ ] Contact information for technical questions

**For Backend Team:**
- [ ] Confirm API endpoints are stable
- [ ] Provide CORS configuration for testing
- [ ] Set up staging database with sample data
- [ ] Document any rate limiting or authentication
- [ ] Prepare deployment process for new templates

---

**End of Handoff Document**  
Last Updated: November 6, 2025  
Contact: <your-email@wellona.com>
