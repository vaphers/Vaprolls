# SEO App — Visual Design Style Guide

## 01. Design Character

The product should feel:
- **Editorial**
- **Technical**
- **Mature**
- **Dense but readable**
- **Quiet**
- **Precise**
- **Earthy**
- **Functional**
- **Slightly utilitarian**
- **Designed, not decorated**

It should **NOT** feel:
- AI-generated
- “SaaS startup”
- Playful
- Futuristic
- Glassmorphic
- Overly minimalist
- Dashboard-template-like
- Full of floating cards
- Full of pills
- Full of badges
- Rounded
- Gradient-heavy

### The Basic Principle
> **Typography + spacing + borders create the interface.** Not cards, shadows, gradients, or decoration.

---

## 02. Colour System

Don't use 20 shades of green. Use a small, disciplined palette.

### Core Palette
| Token | Colour | Hex | Usage |
| :--- | :--- | :--- | :--- |
| `paper` | Warm off-white | `#F7F4EC` | Main application background canvas |
| `surface` | Clean white | `#FFFDF8` | Tables, editors, important surfaces |
| `ink` | Deep carbon | `#252A25` | Primary text |
| `muted` | Stone olive | `#737870` | Secondary text |
| `line` | Crisp divider | `#D9D8CE` | 1px borders & dividers |
| `sage` | Muted sage | `#70866B` | Primary accent & primary button |
| `sage-dark` | Deep forest | `#4F654C` | Hover, active, strong accent |
| `sage-pale` | Subtle sage wash | `#E7EDE3` | Very subtle selected state |
| `beige` | Soft stone | `#E9E1D2` | Secondary background/accent (used sparingly) |

### Semantic Colours (Muted, Not Loud)
| Role | Colour | Hex | Usage |
| :--- | :--- | :--- | :--- |
| **Success** | Muted moss | `#647A5D` | Good status, valid tests, 200 OK |
| **Warning** | Earth amber | `#A18454` | Warnings, redirects, reviews needed |
| **Error** | Muted terra cotta | `#9A6259` | Critical issues, 4xx/5xx errors |
| **Info** | Slate teal | `#687B7A` | Metadata, informational flags |

**Strict Rules**:
- No neon green.
- No bright red.
- No purple “AI” accent.
- No blue everywhere.

---

## 03. Background Philosophy

The entire application sits on **warm off-white / paper (`#F7F4EC`)**, rather than cold grey SaaS (`#F8FAFC`). Cold grey SaaS backgrounds immediately make interfaces look like generated Tailwind UI templates.

```
                    PAPER (#F7F4EC)
─────────────────────────────────────────────────────────────

                        CONTENT

─────────────────────────────────────────────────────────────
```

- **Use beige (`#E9E1D2`) extremely sparingly.**
- Beige is reserved for structural separation, not for random coloured cards.

---

## 04. Typography

Typography is the backbone of the entire product.

- **Primary Typeface**: **Inter**
- **Strict Weights**:
  - Regular (`400`)
  - Medium (`500`)
  - Semibold (`600`)
  - *Never use heavy 700 / 800 bold weights across the UI.*

### Typography Scale
| Element | Size | Weight | Line Height |
| :--- | :--- | :--- | :--- |
| **Page title** | `24px` | `500` | 32px |
| **Section title** | `16px` | `500` | 24px |
| **Body text** | `14px` | `400` | 20px |
| **Table text** | `13px` | `400` | 18px |
| **Secondary text** | `12px` | `400` | 16px |
| **Small metadata** | `11px` | `500` | 14px |
| **Numbers / KPIs** | `20–28px` | `500` | 28–34px |

### Crucial Copy Rules
- **Never use giant headings.**
- **Bad**: `Your Website's SEO Performance`
- **Good**: `Crawl overview` (immediately followed by small muted text if genuinely necessary).
- **Forbidden**: `Welcome back 👋` or `Here's what's happening with your website.` That generic copy instantly signals a generated interface.

---

## 05. Headings & Hierarchy

Every heading must answer: **Why does the user need this label?**

- **Bad**: *Overview*, *Your Website Performance*, *Important Metrics*, *Key Information*, *SEO Health*, *Performance Insights*.
- **Good**:
  ```
  Crawl overview
  184 pages crawled · 12 issues require attention
  ```

### Strict Hierarchy
```
Page title (24px, 500)
   ↓
Section label (16px, 500)
   ↓
Content
```
No 5-level nested headings (`H1` → `H2` → `H3` → `H4` → explanatory subtitle → mini heading). The UI must never read like a blog article.

---

## 06. No Rounded Cards (Hard Rule)

```css
border-radius: 0;
```
Everywhere unless there is an actual usability reason otherwise.

```
Buttons:
┌─────────────────┐
│ Run crawl       │
└─────────────────┘
(Not rounded pill buttons)

Inputs:
──────────────────────────────
Search pages...
──────────────────────────────
(Not giant pill-shaped search bars)
```

---

## 07. Borders Instead of Cards

Don't box every grouping inside a floating rounded card:

```
BAD:
╭──────────────────────╮
│                      │
│       CONTENT        │
│                      │
╰──────────────────────╯

GOOD:
CONTENT
──────────────────────────────────────────────────────────────

content content content

──────────────────────────────────────────────────────────────
```

Structure is established entirely through:
1. **1px Horizontal rules (`#D9D8CE`)**
2. **1px Vertical rules**
3. **Whitespace**
4. **Typography**
5. **Alignment**

---

## 08. Tables Should Be the Workhorse

SEO auditing is inherently data-heavy. Tables do the heavy lifting, not card grids.

```
META TITLES                                                   184 pages

Search pages...                                      Missing ▾
──────────────────────────────────────────────────────────────
URL                         TITLE                       LENGTH
──────────────────────────────────────────────────────────────
/services/cockroach         Cockroach Control...        54
/services/termite           Termite Control...          48
/about                      About PestGuard             16
/contact                    Contact PestGuard           18
──────────────────────────────────────────────────────────────
```
This feels like a serious professional instrument, not an AI template mockup.

---

## 09. Badges — Kill the AI-Looking Ones

Pill badges with rounded colored backgrounds (`🟢 Healthy`, `🟡 Warning`, `🔴 Critical`) scream generic AI-SaaS.

Instead: **Text + tiny indicator**
- `● Healthy`
- `Warning`
- `Critical`

Or in table columns:
```
Missing title              14 pages    Warning
Duplicate title             6 pages    Review
Valid title               164 pages    Good
```

When stronger visibility is required, use a subtle square marker:
- `■ Critical`
- `■ Warning`
- `■ Good`

---

## 10. Icons

- Icons are **functional**, never decorative.
- One icon family: **thin outline, 1.5px stroke, 16px, monochrome**.
- **No icons inside circles.**
- **No icons inside coloured squares.**
- **No emoji beside headings** (no `🕷️ Crawl Overview`).

---

## 11. Buttons

Three clear, restrained button tiers:

```
Primary:
┌────────────────┐
│ Run crawl      │
└────────────────┘
Background: #70866B (sage), text: #FFFFFF or #252A25, border: none, radius: 0.

Secondary:
┌────────────────┐
│ Export         │
└────────────────┘
Background: transparent, border: 1px solid #D9D8CE, text: #252A25, radius: 0.

Tertiary:
View details →
Plain text with minimal arrow.
```

**Never**:
- Gradient buttons
- Giant buttons
- Glowing buttons
- Pill buttons
- Multiple competing primary buttons
- Icon + text + badge + arrow combinations

---

## 12. Navigation

The sidebar must be quiet, confident, and structured purely through typography:

```
PestGuard
────────────────────

PROJECT
Overview
Pages
Issues

CRAWL
Crawl
Redirects
Sitemaps

ON-PAGE
Meta data
Headings
Images
Links

────────────────────
Settings
```
- No card behind every group.
- No section marketing descriptions.
- No "SEO Intelligence" or "Website Optimization" headings.

---

## 13. Page Structure & Spatial Grammar

Every page adheres to consistent spatial grammar, tailored to the specific job:

```
┌─────────────────────────────────────────────────────────────┐
│ PAGE TITLE                                      ACTION      │
│ small description if needed                                 │
│                                                             │
│ ─────────────────────────────────────────────────────────── │
│ filters / tabs / controls                                   │
│ ─────────────────────────────────────────────────────────── │
│                                                             │
│ MAIN WORK AREA (Data table, spreadsheet, or queue)         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 14. Different Personalities per Page

Avoid making every page a generic dashboard:
- **Overview**: Editorial dashboard. One important signal, not 12 cards.
- **Pages**: Master data table (URL, Title, Status, Indexability, Canonical, Words, Latency).
- **Redirects**: Relationship-focused visual chain:
  ```
  SOURCE
    ↓
  REDIRECT (301)
    ↓
  DESTINATION (200)
  ```
- **Meta Data**: Spreadsheet / editor interface.
- **Headings**: Structural outline tree (`H1` ├── `H2` ├── `H3`).
- **Issues**: Triage queue grouped cleanly by severity (`CRITICAL`, `WARNINGS`).

---

## 15. Density

- Body text: `13–14px`.
- Table rows: `44–52px`.
- High density communicates capability and respect for the user's intelligence: *"There is a lot of information here, but I can understand it."*
- Not artificial vast empty whitespace.

---

## 16. Spacing System

Base unit: **4px**
```
Scale: 4px · 8px · 12px · 16px · 24px · 32px · 40px · 48px · 64px
```
Rhythm communicates grouping:
- Label to input: `6–8px`
- Input to next field: `24px`
- Major section to next section: `48px`

---

## 17. Cards: Almost Banned

Cards are permitted **only when content genuinely requires containment**:
- ✅ Crawl progress tracker
- ✅ Google SERP snippet search preview
- ✅ Complex interactive visualization
- ✅ Isolated modal/configuration area

**Banned for**:
- ❌ Total page statistics
- ❌ Error counters
- ❌ Tables
- ❌ Settings rows
- ❌ Metadata blocks

*Rule of thumb*: If you can remove the card border/background and the content still functions cleanly, remove it.

---

## 18. Data Hierarchy

For every screen:
1. **Primary**: Main work area (the core task).
2. **Secondary**: Supporting metadata and filters.
3. **Detail**: Disclosed only upon selection.

---

## 19. Forms

Forms feel like **documents**, not settings cards:

```
Website URL
https://example.com
──────────────────────────────────────────────────────────────

Crawl scope
Entire website                 ○
Selected URLs                  ○
──────────────────────────────────────────────────────────────
                                                   Start crawl
```

---

## 20. Interaction States

- **Hover**: Subtle shift to `#F0EEE6`.
- **Selected / Active**: Sage text (`#4F654C`) + subtle sage wash (`#E7EDE3`).
- **Focus**: Thin sage outline (`1px solid #70866B`).
- **Disabled**: Muted text (`#737870`), reduced contrast.
- **Error**: Inline error text + small marker (no giant red alert boxes).

---

## 21. Empty States

Human, restrained, and action-oriented:
```
No crawl data yet.
Run your first crawl to start auditing this website.

[Run crawl]
```
- No random illustrations.
- No smiling robots.
- No giant decorative vector art.

---

## 22. Loading

- Tables: Restrained, subtle rectangular skeletons.
- Actions: Simple text updates (*"Crawling…"*, *"Exporting CSV…"*) rather than bouncing spinner wheels everywhere.

---

## 23. Motion

- Duration: **120–180ms**.
- Easing: Linear or subtle ease-out.
- Strictly for state feedback (tab switch, row hover, accordion toggle).
- No spring bounces, floating elements, or dramatic camera pans.

---

## 24. Shadows

```css
box-shadow: none;
```
Shadows are disabled by default. Elevation is expressed through **borders (`#D9D8CE`)**, **surface contrasts (`#FFFDF8` on `#F7F4EC`)**, and **typography**.

---

## 25. The “AI UI” Blacklist

Never use by default:
1. ❌ Rounded cards (`rounded-xl`, `rounded-2xl`, `rounded-3xl`)
2. ❌ Pill badges
3. ❌ Pill tabs
4. ❌ Gradient backgrounds
5. ❌ Gradient text
6. ❌ Glassmorphism / backdrop-blur cards
7. ❌ Heavy drop shadows
8. ❌ Giant 48px+ headings
9. ❌ Bold 700/800 typography everywhere
10. ❌ Emoji icons in interface titles
11. ❌ Icon circles
12. ❌ Coloured icon square backgrounds
13. ❌ 3-column metric card grids
14. ❌ "Welcome back 👋" copy
15. ❌ "Here's what’s happening" subtitles
16. ❌ "Your SEO at a glance" marketing slogans
17. ❌ Decorative vector illustrations
18. ❌ Floating action buttons
19. ❌ 10 different status colours
20. ❌ Every number presented as an isolated statistic card

---

## 26. The Visual Formula

```
WARM PAPER (#F7F4EC)
       +
DARK TYPOGRAPHY (#252A25)
       +
SAGE ACCENT (#70866B)
       +
THIN BORDERS (#D9D8CE)
       +
EDITORIAL SPACING
       +
DENSE DATA
       +
VERY FEW CONTAINERS
       +
ONE CLEAR ACTION
```

---

## 27. Golden Screen Prototype

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  Meta data                                      Export      │
│  Review titles and descriptions across crawled pages.       │
│                                                             │
│  All pages    Missing    Duplicate    Too long              │
│                                                             │
│  Search pages...                              Filter        │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ URL                         TITLE                 STATUS    │
│                                                             │
│ /services/cockroach         Cockroach Control...   Good     │
│ /services/termite           Termite Control...     Good     │
│ /about                      About PestGuard        Review   │
│ /contact                    Contact PestGuard      Good     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### The Golden Test
> **If an element exists only to make the UI "look designed," remove it.**
> Every visual element must either help navigation, establish hierarchy, communicate state, or help the user perform the SEO task.
