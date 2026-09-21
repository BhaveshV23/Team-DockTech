# Product Design System

## Product
**DockTech** is a web-based decision-support platform for bulk-cargo vessel chartering to India’s East Coast ports. It helps chartering teams forecast freight trends, validate vessel–port compatibility, compare cost/risk, and choose an informed market-entry strategy.

This document defines the visual language, interaction patterns, accessibility standards, page layouts, reusable React component contracts, and UX rules for a consistent product experience.

## Visual Design Direction

DockTech uses a **Professional Data-Driven Minimalism + Structured Bento Grid** design direction.

This is the primary visual system for the product:
- **Minimalism** is the foundation: clean surfaces, restrained color, strong typography, clear hierarchy, low visual noise, and high information readability.
- **Bento grid** is used to organize dashboard information into purposeful modules such as metrics, forecasts, recommendations, risk, and recent decisions.
- **Subtle glass effects** may be used only as small accents for floating controls, overlays, scenario controls, or selected recommendation surfaces. Glassmorphism is not the default card style.
- **Spatial visualization** may be introduced later for route/vessel visualizations, but is not the primary application layout.
- Do not use neomorphism, claymorphism, maximalism, skeuomorphism, or heavy liquid-glass styling as the core visual language.

The goal is to make DockTech look like a serious operational-intelligence product rather than a decorative UI showcase. Visual styling must never reduce readability of freight rates, forecasts, vessel constraints, cost ranges, risks, or recommendations.

## Design Principles

### Decision-first, not data-first
The interface must lead with the recommended action, expected cost impact, confidence, and operational risk. Detailed charts and calculations should support the decision rather than bury it.

### Operational clarity
Use direct language familiar to chartering and logistics teams. Explain technical terms when needed, retain units beside values, and make planning assumptions visible.

### Explainable intelligence
Never show a recommendation without a short reason, a confidence/uncertainty indicator, relevant assumptions, and source/data-recency context. The product is decision support, not autonomous charter execution.

### Progressive disclosure
Show essential information first. Place model details, formulas, raw inputs, and alternative assumptions behind expandable sections, tabs, or a detail view.

### Calm, professional, and trustworthy
Use restrained color, clear spacing, meaningful hierarchy, and predictable controls. Avoid decorative visuals, excessive animation, or alarmist language.

### Accessible by default
The application must be usable with keyboard navigation, screen readers, zoom, and high-contrast needs. Color must never be the only way information is communicated.

## Brand and Voice

### Product personality
- Professional and precise
- Operationally practical
- Calm under uncertainty
- Transparent about assumptions
- Helpful rather than prescriptive

### Writing style
- Prefer active voice: “Fix now” rather than “A fixing action is recommended.”
- Use short, action-oriented labels.
- Use plain language first, followed by a domain term where required.
- Keep units explicit: `USD/tonne`, `days`, `m`, `DWT`, `nm`, `%`.
- Avoid false certainty: use “Estimated,” “Likely,” “Expected range,” and “Based on available data.”
- Avoid unexplained acronyms on first use: write “Length Overall (LOA)” before using “LOA.”

### Examples
| Use | Avoid |
|---|---|
| “Fix now: rates are likely to rise before your delivery window.” | “Recommendation generated successfully.” |
| “Panamax is not feasible: draft exceeds Paradip planning limit.” | “Constraint violation.” |
| “Forecast confidence: medium. The range is wider than usual.” | “Confidence = 0.62.” |
| “Data updated 2 days ago.” | “Last refresh: 2026-09-18T04:34:00Z.” |

## Technology Context
- **Frontend:** React + TypeScript.
- **Styling:** CSS Modules, Tailwind CSS, or a token-aware component library; use one approach consistently.
- **Charts:** Recharts, Nivo, Visx, or Plotly React wrapper; selected library must support accessible labels/tooltips.
- **Icons:** Lucide React or another single, consistent SVG icon set.
- **Routing:** React Router or framework router.
- **Data fetching:** a centralized API client, optionally React Query/TanStack Query.
- **Authentication:** Supabase Auth for identity and session management.
- **Data platform:** Supabase PostgreSQL for application/reference data and Supabase Storage for reports/uploads where needed.
- **Backend:** FastAPI API layer for business logic, protected application operations, server-side Supabase access, forecasting, feasibility, recommendations, and scenarios.
- **Caching:** Redis may be used for performance-sensitive cached data.
- **Security boundary:** React may use the Supabase client for authentication/session operations, but core application data access goes through FastAPI; Supabase service-role credentials are never exposed to the browser.

## Design Tokens
All UI must use shared tokens. Do not hard-code arbitrary colors, font sizes, shadows, border radii, or spacing values inside individual components.

### Color palette

#### Core brand colors
| Token | Value | Usage |
|---|---:|---|
| `--color-navy-950` | `#0B1F33` | Primary headings, sidebar, dark text |
| `--color-navy-800` | `#163A5F` | Primary buttons, active navigation |
| `--color-blue-600` | `#2563EB` | Links, focus states, interactive highlights |
| `--color-blue-100` | `#DBEAFE` | Soft informational backgrounds |
| `--color-teal-600` | `#0F766E` | Positive operational highlights |
| `--color-teal-100` | `#CCFBF1` | Positive soft background |

#### Neutral colors
| Token | Value | Usage |
|---|---:|---|
| `--color-slate-950` | `#0F172A` | High-emphasis text |
| `--color-slate-700` | `#334155` | Body text |
| `--color-slate-500` | `#64748B` | Secondary text, labels |
| `--color-slate-300` | `#CBD5E1` | Borders, disabled outline |
| `--color-slate-200` | `#E2E8F0` | Dividers |
| `--color-slate-100` | `#F1F5F9` | Subtle surface |
| `--color-slate-50` | `#F8FAFC` | Application background |
| `--color-white` | `#FFFFFF` | Cards and primary surfaces |

#### Semantic colors
| Token | Value | Meaning |
|---|---:|---|
| `--color-success-700` | `#15803D` | Feasible, favorable, completed |
| `--color-success-100` | `#DCFCE7` | Success background |
| `--color-warning-700` | `#A16207` | Caution, medium risk, stale data |
| `--color-warning-100` | `#FEF3C7` | Warning background |
| `--color-danger-700` | `#B91C1C` | Infeasible, critical risk, destructive action |
| `--color-danger-100` | `#FEE2E2` | Error background |
| `--color-info-700` | `#1D4ED8` | Informational state |
| `--color-info-100` | `#DBEAFE` | Informational background |

### Semantic usage rules
- Use green only for confirmed feasibility, favorable movement, completion, or positive status.
- Use amber for uncertainty, stale data, medium risk, or human review needed.
- Use red only for infeasibility, material risk, or destructive actions.
- Pair every semantic color with an icon and text label, such as `Feasible`, `Attention needed`, or `Not feasible`.
- Do not use red/green to represent forecast price direction alone; use arrows and labels such as `Rate expected to rise` and `Rate expected to fall`.

### Typography
Use **Inter** as the default UI font. Use system fallbacks for reliability.

```css
font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
```

| Token | Size / line height | Weight | Usage |
|---|---|---:|---|
| `--text-display` | 32px / 40px | 700 | Page hero or major dashboard title |
| `--text-h1` | 28px / 36px | 700 | Page title |
| `--text-h2` | 22px / 30px | 700 | Major section heading |
| `--text-h3` | 18px / 26px | 600 | Card or subsection heading |
| `--text-body` | 14px / 22px | 400 | Default body content |
| `--text-body-strong` | 14px / 22px | 600 | Emphasized supporting copy |
| `--text-small` | 12px / 18px | 400 | Labels, helper text, metadata |
| `--text-metric` | 24px / 30px | 700 | Important numeric values |
| `--text-metric-lg` | 32px / 38px | 700 | Primary recommendation/cost metric |

Typography rules:
- Use sentence case for buttons, page titles, labels, and headings.
- Use tabular numerals (`font-variant-numeric: tabular-nums`) for rate, cost, duration, and percentage values.
- Do not use all caps for long text; all caps may be used only for brief table status headers or compact labels.
- Keep body text at 14px minimum; helper text at 12px minimum.
- Do not communicate hierarchy with color alone; use size, weight, placement, and labels.

### Spacing
Use a 4px base unit.

| Token | Value | Typical usage |
|---|---:|---|
| `--space-1` | 4px | Icon/text gap, tight grouping |
| `--space-2` | 8px | Form-label gap, compact controls |
| `--space-3` | 12px | Card internal grouping |
| `--space-4` | 16px | Standard component gap |
| `--space-5` | 20px | Card padding on compact screens |
| `--space-6` | 24px | Standard card padding, section gap |
| `--space-8` | 32px | Major section gap |
| `--space-10` | 40px | Page-level separation |
| `--space-12` | 48px | Large desktop separation |

### Shape, borders, and elevation
| Token | Value | Usage |
|---|---:|---|
| `--radius-sm` | 6px | Inputs, small controls |
| `--radius-md` | 10px | Buttons, cards, popovers |
| `--radius-lg` | 14px | Large summary cards, dialogs |
| `--border-default` | `1px solid #E2E8F0` | Standard component border |
| `--shadow-sm` | `0 1px 2px rgba(15,23,42,.06)` | Cards, inputs |
| `--shadow-md` | `0 8px 20px rgba(15,23,42,.10)` | Menus, dialogs |

Use borders by default. Use shadows sparingly for floating elements, overlays, and elevated interactive panels.

### Bento and surface rules
- Use a 12-column desktop grid for purposeful dashboard composition.
- Bento modules should have one clear purpose and a predictable visual hierarchy.
- Prefer asymmetric spans only when they improve information priority; do not create decorative tile mosaics.
- Primary recommendation and key risk modules may occupy larger grid areas than secondary metrics.
- Maintain consistent card padding, alignment, and gutters across a page.
- Do not place unrelated information into a single bento tile merely to fill space.

### Subtle glass accent rules
- Glass effects are optional and limited to floating/overlay surfaces.
- Use high-opacity light surfaces, a thin border, and restrained backdrop blur.
- Never use glass effects for dense tables, primary forms, charts, or critical warning/error content.
- Maintain text contrast and clear boundaries when transparency is used.
- Do not combine heavy blur, strong gradients, large shadows, and transparency in the same component.

### Motion
- Use motion only to explain state changes, not to decorate.
- Standard transition: 150–200ms ease-out.
- Respect `prefers-reduced-motion`; remove nonessential animation.
- Avoid auto-animated charts that make reading operational data harder.

## Application Shell

### Desktop layout
```text
+--------------------------------------------------------------------------------+
| Top bar: logo | environment/data status | notifications | user menu            |
+----------------------+---------------------------------------------------------+
| Left sidebar         | Main content                                            |
| - Overview           | Breadcrumb (optional)                                   |
| - Plan shipment      | Page title + short context + primary action             |
| - Forecasts          |                                                         |
| - Scenarios          | Page content                                            |
| - Reports            |                                                         |
| - Admin (role-based) |                                                         |
+----------------------+---------------------------------------------------------+
```

### Sidebar
- Width: 248px desktop; collapsible to 72px if needed.
- Background: `--color-navy-950`.
- Show product name/logo at top and user/support links at bottom.
- Each item has icon + label. Active item uses a visible blue/teal accent and an accessible text indication.
- Admin navigation appears only after the backend has confirmed the user role. Hiding a link is not authorization.

### Top bar
- Height: 64px.
- Background: white with bottom border.
- Display `Data as of: <date>` when available. If data is stale, show an amber status badge with a tooltip.
- User menu includes profile, role, and sign out.

### Content area
- Application background: `--color-slate-50`.
- Maximum content width: 1440px.
- Desktop padding: 32px; tablet: 24px; mobile: 16px.
- Use 12-column CSS grid for desktop pages and collapse to one column on small screens.

### Responsive breakpoints
| Breakpoint | Range | Rules |
|---|---|---|
| Mobile | `< 640px` | Single column, drawer navigation, sticky primary action when appropriate |
| Tablet | `640px–1023px` | Two-column layouts only where readable; sidebar may collapse |
| Desktop | `>= 1024px` | Full sidebar, 12-column grid, comparison tables allowed |
| Wide | `>= 1440px` | Preserve max content width; do not stretch text excessively |

## Page Design

### Overview
**Purpose:** Give managers an immediate view of current planning state and decision alerts.

**Layout:**
1. Page title: `Chartering overview`.
2. A structured bento grid containing:
   - up to 4 summary metrics: current freight signal, high-risk ports, active plans, data freshness;
   - a larger freight-market trend card;
   - a prominent recommendation/action card;
   - a risk/attention card;
   - recent recommendation/history.
3. `Recommended actions` list with direct links to plans/scenarios.

Use larger grid areas for decision-critical content and smaller modules for supporting metrics. Do not create a decorative tile wall.

Avoid turning the overview into a dense analytics wall. Show at most 4 primary metrics and 3–5 actions.

### Plan shipment
**Purpose:** Main workflow for a cargo parcel.

**Desktop layout:**
- Left column (4/12): planning input card.
- Right column (8/12): recommendation, forecast, vessel comparison, and assumptions.

**Required input fields:**
- Commodity
- Cargo volume in tonnes
- Origin port
- Destination port
- Delivery start and end date
- Contract horizon/preference
- Optional: loading/discharge-rate override, freight assumption, priority/urgency

**Interaction:**
- Validate inputs on blur and on submit.
- Disable `Generate recommendation` only when required inputs are invalid or missing; explain why.
- Preserve input state while results are loading or a scenario is changed.
- On success, auto-scroll/focus to the recommendation heading on mobile only when initiated by explicit submit.

### Forecasts
**Purpose:** Explore freight-rate trends by route/vessel class without requiring a complete cargo plan.

**Layout:**
- Filter toolbar: route, vessel class, horizon, date range.
- Main forecast chart.
- Supporting metrics: latest value, 30/90-day movement, forecast range, confidence, data recency.
- Expandable `Forecast drivers and limitations` section.

### Scenarios
**Purpose:** Compare the baseline plan with controlled changes.

**Layout:**
- Left: scenario controls.
- Right: baseline vs scenario comparison.
- Bottom: impact explanation and risk changes.

Avoid hidden calculations. Every changed result must show the scenario assumption responsible for it.

### Reports
**Purpose:** Find and export saved recommendations or generated decision summaries.

**Layout:**
- Search/filter by date, route, user, status, and commodity.
- Table with a clear `View` and `Export` action per record.
- Exports include visible data and assumption timestamps.

### Admin
**Purpose:** Manage reference data for authorized users.

**Layout:**
- Separate tabs: Ports, Vessel classes, Routes, Data sources, Model metadata.
- Use tables with edit dialogs, source/effective-date fields, validation messages, and audit history.
- Destructive changes require explicit confirmation and a clear impact statement.

## Core UX Flow

### Generate a chartering recommendation
1. User opens `Plan shipment`.
2. User completes the cargo planning form.
3. User selects `Generate recommendation`.
4. System validates the input and shows a non-blocking loading state.
5. System returns a decision summary first: action, vessel, cost range, key risk.
6. User reviews forecast and vessel alternatives.
7. User optionally applies scenarios.
8. User exports or saves the decision summary.

### Information priority
Results must be ordered as follows:
1. Recommended action.
2. Recommended vessel and feasibility status.
3. Expected cost range and timing impact.
4. Key risk or blocking issue.
5. Supporting chart, vessel alternatives, assumptions, and technical details.

## Reusable React Component System

### Component folder structure
```text
frontend/src/
├── app/
│   ├── App.tsx
│   ├── routes.tsx
│   └── providers.tsx
├── pages/
│   ├── OverviewPage.tsx
│   ├── PlanShipmentPage.tsx
│   ├── ForecastsPage.tsx
│   ├── ScenariosPage.tsx
│   ├── ReportsPage.tsx
│   └── AdminPage.tsx
├── components/
│   ├── ui/
│   │   ├── Button/
│   │   ├── Card/
│   │   ├── Badge/
│   │   ├── Input/
│   │   ├── Select/
│   │   ├── DateRangePicker/
│   │   ├── Modal/
│   │   ├── Tooltip/
│   │   ├── Tabs/
│   │   ├── Table/
│   │   ├── Alert/
│   │   ├── Skeleton/
│   │   └── EmptyState/
│   ├── layout/
│   │   ├── AppShell.tsx
│   │   ├── Sidebar.tsx
│   │   ├── Topbar.tsx
│   │   ├── PageHeader.tsx
│   │   └── Section.tsx
│   └── domain/
│       ├── CargoPlanningForm.tsx
│       ├── RecommendationCard.tsx
│       ├── FreightForecastChart.tsx
│       ├── VesselComparisonTable.tsx
│       ├── RiskPanel.tsx
│       ├── ScenarioControls.tsx
│       ├── AssumptionsPanel.tsx
│       └── DataFreshnessBadge.tsx
├── features/
│   ├── auth/
│   ├── planning/
│   ├── forecasting/
│   ├── scenarios/
│   ├── reports/
│   └── admin/
├── services/
│   ├── apiClient.ts
│   ├── authApi.ts
│   ├── recommendationApi.ts
│   ├── forecastApi.ts
│   └── reportApi.ts
├── hooks/
├── types/
├── utils/
├── styles/
│   ├── tokens.css
│   ├── globals.css
│   └── utilities.css
└── test/
```

### Component rules
- `components/ui/` contains generic, reusable visual primitives. It must not contain product-specific data fetching or business calculations.
- `components/domain/` contains reusable DockTech-specific presentation components. It receives already-prepared view data via props.
- `pages/` compose components and coordinate page-level state. Keep them thin.
- `features/` owns feature-level hooks, state, API-query integration, and mapping API responses to view models.
- `services/` contains HTTP calls only; it must never connect directly to a database.
- No React component may calculate freight forecasts, vessel feasibility, port constraints, ranking, pricing, or authorization decisions.

## Component Specifications

### Button
Buttons trigger actions. They must use a verb-led label.

| Variant | Usage | Example |
|---|---|---|
| Primary | Main page action, one per visual area | `Generate recommendation` |
| Secondary | Supporting non-destructive action | `Compare scenarios` |
| Tertiary/Ghost | Low-emphasis action | `View assumptions` |
| Danger | Destructive admin action only | `Delete route` |
| Icon | Compact familiar action with tooltip/aria-label | Export, close, more actions |

**Rules**
- Minimum height: 40px; recommended 44px for primary touch actions.
- Border radius: `--radius-md`.
- Use visible keyboard focus ring: 2–3px blue outline with offset.
- Never use color alone to distinguish destructive behavior; include label and confirmation.
- Disabled buttons must explain the blocking condition when relevant.
- Prevent double submission by showing a loading label, such as `Generating…`.

### Card
Cards group related content and should have one clear purpose.

**Base style**
- White or near-white surface, subtle border, `--radius-lg`, `--shadow-sm`.
- Padding: 24px desktop, 16–20px mobile.
- Use 16px header-to-content spacing.
- Cards are the building blocks of the structured bento layout; each card should have one clear information purpose.
- Avoid gradients, excessive shadows, decorative glass effects, or ornamental shapes.

**Card types**
- **Summary card:** a metric, label, trend, and optional link.
- **Recommendation card:** strongest hierarchy; includes action, rationale, cost/risk, and confidence.
- **Data card:** chart/table plus filters and metadata.
- **Warning card:** semantic left border/icon plus explanation and action.

Do not nest more than two card levels. Prefer sections or dividers inside a card.

### Form fields
All inputs require a visible label; placeholder text is not a label.

**Input anatomy**
```text
Label (required marker if applicable)
Input control
Helper text or validation message
```

**Rules**
- Required fields use `Required` text or an accessible asterisk explanation.
- Numeric fields specify expected unit adjacent to the input, e.g., `Cargo volume (tonnes)`.
- Use input masks/formatting for quantities but preserve raw numeric values internally.
- Date-range picker prevents end date before start date.
- Select controls support search when choices exceed approximately 10 items.
- Inline validation appears after blur or submit; do not show an error before meaningful interaction.
- Do not clear user input when an API request fails.

### Status badge
Badges communicate short state, not long explanation.

Examples:
- `Feasible` with check icon
- `Not feasible` with alert icon
- `Medium risk` with warning icon
- `Proxy data` with info icon
- `Data stale` with clock icon

Rules:
- Use rounded rectangle, not a pill for large labels.
- Include text and optionally an icon.
- Provide a tooltip or adjacent explanation for non-obvious statuses.

### Recommendation card
This is the primary output component.

**Required content**
- Action: `Fix now`, `Wait`, or `Consider multi-voyage contract`.
- Recommended vessel class.
- One-sentence rationale.
- Base estimated cost and range.
- Confidence/risk indicator.
- Key blockers or warnings.
- `View details` / `Export summary` actions.

**Example layout**
```text
[Recommendation]                              [Medium confidence badge]
Fix now
Lock a short-term charter before the expected rate increase.

Recommended vessel: Panamax
Estimated cost: USD 18.40/tonne  |  Expected range: USD 16.90–20.60

[Feasible] Fits selected port draft and LOA planning limits
[Warning] Destination congestion may add 2–4 days

[View assumptions]                              [Export summary]
```

Never make the recommendation visually look like an automatic execution command. Use a small disclaimer: `Decision-support recommendation; confirm current market and port notices before fixing.`

### Freight forecast chart
**Chart type:** line chart with observed historical rate, forecast line, and translucent uncertainty band.

**Required elements**
- Title with route and vessel class.
- Clear y-axis unit, such as `USD/tonne` or `USD/day`.
- Historical vs forecast distinction using line style and legend.
- Forecast interval displayed as a subtle filled band, not multiple noisy lines.
- Date labels readable at all supported viewport sizes.
- Data-as-of label and forecast horizon.
- Accessible tabular summary alternative.

**Color guidance**
- Observed: navy/slate solid line.
- Forecast: blue solid or dashed line.
- Uncertainty: blue at 15–20% opacity.
- Do not use rainbow palettes.

**Interaction guidance**
- Tooltip includes date, observed/forecast rate, lower/upper estimate, and unit.
- Avoid requiring hover to access critical values; show key values in summary cards.
- On mobile, support tap tooltips and a compact chart mode.

### Vessel comparison table
**Purpose:** Compare feasible and infeasible vessel alternatives.

Columns:
- Vessel class
- Feasibility
- Cargo fit / required voyages
- Estimated turnaround
- Estimated cost per tonne
- Risk
- Recommendation marker

Rules:
- Place recommended option first and mark it with text: `Recommended`.
- For infeasible options, show the exact constraint reason in the feasibility cell.
- Use responsive behavior: horizontal scroll with frozen first column, or card transformation on mobile.
- Do not hide key units.
- Sort order must be explicit and stable.

### Scenario controls
**Controls**
- Freight-rate shock: slider + numeric input, percent.
- Congestion delay: slider + numeric input, days.
- Optional fuel-price shock: slider + numeric input, percent.
- Reset to baseline action.

Rules:
- All controls have visible default values and units.
- Update results after an explicit `Apply scenario` click for costly API calculations; use debounced updates only for local preview.
- Summarize active assumptions above the comparison result.
- Show baseline and scenario side by side, not only the changed value.

### Alerts, errors, empty states
| State | Pattern | Example |
|---|---|---|
| Informational | Blue info alert | “This route uses proxy freight data.” |
| Caution | Amber warning alert | “Port constraints were updated more than 30 days ago.” |
| Blocking error | Red error alert | “No feasible vessel meets both port draft limits.” |
| Empty state | Illustration/icon + explanation + action | “No saved reports yet. Generate a recommendation to create one.” |
| Loading | Skeleton for layout, spinner within action | “Generating forecast…” |

Errors must state what happened, why it matters when known, and what the user can do next.

## Data Presentation

### Numbers and units
- Format large quantity: `75,000 tonnes`, not `75000`.
- Format currency: `USD 18.40/tonne`; do not rely on `$` alone.
- Format ranges: `USD 16.90–20.60/tonne`.
- Format duration: `4.5 days`, `2–4 days`.
- Format distances: `4,250 nm`.
- Format dimensions: `14.5 m draft`, `225 m LOA`.
- Use a nonbreaking space where practical between value and unit.
- Use en dash for ranges, not a hyphen.

### Trend representation
- Display percentage change with text: `Expected to rise 8% over 30 days`.
- Use arrow icons as secondary reinforcement, not the sole signal.
- Show the comparison period: `vs. current estimate` or `vs. previous 30 days`.

### Confidence and uncertainty
- Use `High`, `Medium`, or `Low` confidence labels.
- Explain confidence in a tooltip or details panel.
- Do not equate confidence with correctness.
- When uncertainty is high, prioritize a warning and the expected range over the point estimate.

### Assumptions and source information
Every recommendation view must display or link to:
- Data as-of date.
- Data quality: actual, proxy, or simulated.
- Forecast model version.
- Port/vessel constraint effective date.
- Key cost/handling/waiting assumptions.

Use an expandable `Assumptions and data quality` panel for complete details.

## UX Requirements

### Decision support and safety
1. The interface must state that outputs are decision support and require market/port validation before a charter is fixed.
2. A user must be able to inspect why a vessel is recommended or rejected.
3. A user must be able to inspect why `Fix now`, `Wait`, or `Consider multi-voyage contract` was recommended.
4. High uncertainty, proxy data, stale inputs, and unsupported routes must be prominent.
5. The UI must never imply a contract was executed unless a future integrated workflow explicitly confirms it.

### Loading and performance
1. Use skeletons for primary result cards/charts while loading, preserving page layout.
2. Show a status message if recommendation generation takes more than 2 seconds.
3. Disable duplicate submit actions while a request is in progress.
4. Keep client-side interactions responsive; expensive calculations remain on the backend.
5. Cache stable reference lists (ports, vessel classes) through the API client/query layer.

### Validation
1. Validate required fields before API submission.
2. Use server responses as the source of truth for business validation.
3. Show field-specific errors near fields and summary errors at top of form when needed.
4. Do not rely only on client-side validation for authorization, feasibility, or business rules.

### State management
1. Persist in-progress plan form values during page navigation within a session.
2. Separate server state (API data) from local UI state (open modal, selected tab).
3. Put Supabase authentication state in an application-level provider, but validate the authenticated session/token with the FastAPI backend on protected routes.
4. Avoid storing confidential data in local storage unless necessary and explicitly approved.

### Responsive behavior
1. Planning form fields stack on mobile.
2. Recommendation card appears before charts/tables on small screens.
3. Wide comparison tables transform to stacked option cards or horizontal scroll with clear affordance.
4. Sticky actions must not obscure content or mobile browser controls.
5. Tooltips must have tap-accessible equivalents on touch devices.

## Accessibility Requirements
The product target is WCAG 2.1 AA where feasible.

- Maintain at least 4.5:1 text contrast ratio for normal text.
- All interactive controls are keyboard reachable in logical order.
- Visible focus state is mandatory.
- Use semantic HTML: `button`, `label`, `input`, `table`, headings in order, and landmark regions.
- Add accessible names to icon-only buttons with `aria-label`.
- Modals trap focus, close with Escape, restore focus to the opener, and have labelled titles.
- Charts need text summaries and accessible data tables or downloadable data alternatives.
- Error messages must be announced to screen readers using appropriate live regions.
- Do not use color alone for statuses, trends, or chart series.
- Support browser zoom at 200% without loss of functionality or overlap.

## Interaction Patterns

### Confirmation dialogs
Use confirmation dialogs only for destructive or materially consequential actions, such as deleting a route or replacing port constraints.

Dialog must include:
- Clear action title: `Delete route?`
- Consequence: `This will remove the route from new planning requests.`
- Primary destructive button: `Delete route`
- Safe escape: `Cancel`

Do not use confirmation dialogs for normal navigation, exports, or non-destructive filtering.

### Tooltips
Use tooltips for concise definitions, not essential instructions. If a user must understand something to proceed, show it as visible helper text.

### Toasts
Use toasts for transient confirmation: `Report exported`, `Scenario saved`. Do not put critical error details only in a toast; keep errors persistent near their context.

### Save behavior
- Explicit user actions save plans, scenarios, or admin changes.
- Clearly show `Saving…`, `Saved`, and failure states.
- For unsaved changes, warn before leaving only when loss would be meaningful.

## React Implementation Rules

### UI separation
1. React components must not contain SQL, ORM code, direct database calls to application tables, Supabase service-role credentials, or server secrets.
2. React components must not calculate forecast outputs, vessel feasibility, contract strategy, pricing, or ranking policy. They render API-provided results and collect inputs.
3. Reusable primitives belong in `components/ui/`; reusable DockTech display components belong in `components/domain/`.
4. Page components compose components; do not duplicate component markup across pages.
5. API calls belong in `services/` and feature hooks, never scattered in low-level UI controls.
6. Map API response objects to view models in feature-level adapters/hooks, not repeatedly in individual components.

### Authentication and authorization
7. Use Supabase Auth for user sign-in, sign-out, and client session state.
8. FastAPI must verify the Supabase access token/session for every protected API request.
9. The frontend may use route guards for navigation experience, but route guards do not replace server authorization.
10. Role-based visibility in React is cosmetic; backend role checks are mandatory for data access and mutations.
11. Never expose the Supabase service-role key or other server secrets to React.
12. Use the Supabase client only for approved identity/session operations; core application data requests go through FastAPI.
13. Do not store long-lived access tokens in insecure browser storage where avoidable; follow Supabase's supported session/token handling and project security configuration.

### Consistency
11. Use design tokens and shared components; no arbitrary one-off visual styles without review.
12. Use TypeScript types generated from or aligned with API contracts.
13. Use a shared formatter utility for currency, units, dates, ranges, and percentages.
14. All status rendering must use shared semantic status mapping.
15. Every loading, error, empty, and unauthorized state must be designed, not left as a blank screen.

## Example Design Tokens CSS
```css
:root {
  --color-navy-950: #0B1F33;
  --color-navy-800: #163A5F;
  --color-blue-600: #2563EB;
  --color-slate-950: #0F172A;
  --color-slate-700: #334155;
  --color-slate-500: #64748B;
  --color-slate-200: #E2E8F0;
  --color-slate-50: #F8FAFC;
  --color-white: #FFFFFF;
  --color-success-700: #15803D;
  --color-success-100: #DCFCE7;
  --color-warning-700: #A16207;
  --color-warning-100: #FEF3C7;
  --color-danger-700: #B91C1C;
  --color-danger-100: #FEE2E2;

  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;

  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 14px;
  --shadow-sm: 0 1px 2px rgba(15, 23, 42, 0.06);
  --shadow-md: 0 8px 20px rgba(15, 23, 42, 0.10);

  --font-sans: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
```

## AI Implementation Guidance
When an AI assistant generates a new page or component, it must:
1. Reuse existing tokens and shared UI components before creating a new visual pattern.
2. Use TypeScript interfaces/types for component props and API data.
3. Keep UI rendering, API client calls, and business logic separate.
4. Include loading, error, empty, and responsive states.
5. Include labels, units, semantic status text, and accessible names.
6. Avoid inventing freight values, port constraints, vessel specifications, or model outputs; render data returned by the backend or documented mock data.
7. Preserve source/data-quality warnings provided by the API.
8. Ensure primary decision outputs appear before supporting technical details.
9. Follow the Professional Data-Driven Minimalism + Structured Bento Grid direction; avoid overusing gradients, glass effects, animations, excessive shadows, and decorative charts.
10. Do not bypass server-side authentication or authorization.

## Design Review Checklist
Before merging a frontend change, confirm:

### Visual consistency
- [ ] Uses design tokens rather than arbitrary color, spacing, typography, or radius values.
- [ ] Reuses shared components where appropriate.
- [ ] Matches application shell, hierarchy, and semantic color rules.
- [ ] Follows the Professional Data-Driven Minimalism + Structured Bento Grid direction.
- [ ] Uses glass effects only as restrained accents, never as the default surface style.
- [ ] Does not introduce neomorphism, claymorphism, maximalism, skeuomorphism, or heavy liquid-glass styling.

### UX
- [ ] Primary user action and key result are visible without unnecessary scrolling on desktop.
- [ ] User sees loading, empty, error, and success states.
- [ ] Inputs preserve values after failed requests.
- [ ] Recommendations include rationale, uncertainty, assumptions, and data recency.
- [ ] Tables/charts remain understandable on mobile.

### Accessibility
- [ ] Controls have accessible names and visible focus.
- [ ] Labels are associated with form fields.
- [ ] Color is not the only status indicator.
- [ ] Keyboard navigation and modal behavior are correct.
- [ ] Chart has a text/table alternative.

### Architecture and security
- [ ] No application database access or server secrets in React code.
- [ ] Supabase Auth is used for identity/session operations and service-role credentials remain server-side.
- [ ] API access uses the centralized service/client layer.
- [ ] No business-critical calculations or authorization decisions in UI components.
- [ ] Protected actions are enforced server-side through FastAPI.
- [ ] API errors are handled safely and clearly.

## Definition of Done for UI
A user interface feature is complete when it:
- Uses shared design tokens and reusable components.
- Works on mobile, tablet, and desktop at supported breakpoints.
- Meets keyboard and screen-reader basics.
- Handles loading, empty, success, warning, and error states.
- Uses API-provided data without direct database access.
- Keeps business logic and authorization decisions on the backend.
- Presents assumptions, units, data recency, uncertainty, and recommendation rationale where relevant.
- Has been reviewed against this design document.

