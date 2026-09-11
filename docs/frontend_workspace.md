# Frontend Workspace Architecture

## 1. Interface Overview

Vaprolls uses a dense, zero-gap Single Page Application (SPA) interface engineered to match professional desktop crawler software (such as Screaming Frog SEO Spider). The UI eliminates decorative margins and rounded corners in favor of 1px structural border dividers, universal Roboto typography, and high-contrast black text.

Related documentation:
- Visual styling rules: [Visual Design Style Guide](visual_design_style_guide.md)
- Data schema: [URL Dataset Specification](url_dataset_specification.md)
- Backend endpoints: [API & WebSocket Protocol](api_and_websocket.md)

---

## 2. Workspace Geometry and Panel Docking

The viewport is divided into three dockable, border-divided panels:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ Top Command Bar: [URL to Spider: https://... ] [Start] [Stop] [Progress] [Crawl Selector]   │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ Category Tabs: [All URLs] [Internal] [External] [Response Codes] [Page Titles] ...          │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│ Filter Sub-bar: [Filter: Type] [Include: Regex] [Exclude: Regex] [Search] [Count: 41 of 41] │
├───────────────────────────────────────────────────────────────────────┬─┬───────────────────┤
│                                                                       │ │                   │
│ Master Spreadsheet Table                                              │ │ Right Sidebar     │
│ (#, Address, Content Type, Status Code, Status, Indexability...)      │ │ (URL Overview     │
│ (Fully wrapped URLs, sticky header, clickable rows)                   │ │  & URL Issues)    │
│                                                                       │ │                   │
├───────────────────────────────────────────────────────────────────────┤ │ (Draggable width) │
│ Draggable Horizontal Splitter (#inspector-resizer)                    │ │                   │
├───────────────────────────────────────────────────────────────────────┤ │                   │
│ Bottom Split Inspector Panel                                          │ │                   │
│ [URL Details] [Inlinks] [Outlinks] [Images] [SERP] [Headers] [Schema] │ │                   │
│ (Draggable height, persisted to localStorage)                         │ │                   │
└───────────────────────────────────────────────────────────────────────┴─┴───────────────────┘
```

---

## 3. Draggable Resizing Mechanics

Both splitters are engineered with native JavaScript event listeners to provide smooth resizing without external UI library dependencies.

### 3.1 Bottom Inspector Resizer (`#inspector-resizer`)
- **Trigger**: Sits directly above `#inspector-container`.
- **Cursor**: `cursor: row-resize;`.
- **Drag Vector**: Measures `dy = startY - e.clientY`. Pulling up increases panel height.
- **Constraints**: Clamped between `120px` and `75%` of window height.
- **Persistence**: Upon `mouseup`, current height is stored in `localStorage.setItem('spider_inspector_height', height)`. Restored on `DOMContentLoaded`.

### 3.2 Right Sidebar Resizer (`#sidebar-resizer`)
- **Trigger**: Sits between the primary table section and `#right-panel-container`.
- **Cursor**: `cursor: col-resize;`.
- **Drag Vector**: Measures `dx = startX - e.clientX`. Pulling left increases sidebar width.
- **Constraints**: Clamped between `240px` and `60%` of window width.
- **Persistence**: Upon `mouseup`, current width is stored in `localStorage.setItem('spider_sidebar_width', width)`. Restored on `DOMContentLoaded`.

---

## 4. Dual-Inspection Interaction Flow

When any row in the master table is clicked (or upon initial load for Row 1):
1. **Row Highlighting**: The row receives `.selected-row` with background `#E5E7EB`.
2. **Instant Local Population**: The row's `data-*` attributes immediately populate:
   - Inspector Header: URL, Status Code, Indexability badge.
   - Inspector URL Details: 6 technical cards (URL & Status, Directives, Canonical, Content, Link Graph, Timing).
   - Right Sidebar Overview: Complete single-URL technical profile.
   - Right Sidebar Issues: Local issue count and cards for that specific URL.
3. **Deep Asynchronous Fetch**:
   - Dispatches `GET /api/audit/{audit_id}/page/{page_id}/inspector`.
   - Populates sub-tables: Inlinks (with anchor text), Outlinks, Image Assets (with alt text check), HTTP Headers, and Structured Data JSON blocks.
