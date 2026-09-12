# Charts in Phlex Views (Chart.js via a house Stimulus controller)

Scope: Rails views rendered with Phlex. The other stacks have their own home — the Vite SPA uses
react-chartjs-2 (`@skills/std-reactjs/references/charts.md`), Next.js uses the shadcn/ui chart
component on Recharts (`@skills/std-shadcn-ui/references/charts.md`).

Load-bearing rules restated (this file is self-contained):

1. **Chart.js 4.5.1 (MIT) through one house controller**, `app/javascript/controllers/chart_controller.js`.
   No Chartkick, no inline `<script>`, no `style=` attribute, and no `bin/importmap pin chart.js`.
2. **Server data reaches the controller only as Stimulus values** rendered by Phlex, and an Object
   value is always `payload.to_json` — never a Ruby Hash.
3. **One controller per chart**, on a `relative`, sized container that holds only the `<canvas>`.
4. **Lifecycle:** `connect` builds (except on a Turbo preview); `disconnect` and `turbo:before-cache`
   destroy; `turbo:render` rebuilds a torn-down chart that is still connected; a payload change
   updates in place. Every build is guarded by `Chart.getChart`.
5. **Colours come from design tokens** read with `getComputedStyle`, re-read when `<html>`'s class
   changes. Never a literal, never `var()`.
6. **`prefers-reduced-motion: reduce` means `animation: false`.**
7. **Every chart ships a server-rendered figure:** caption, a one-line summary, and a data table
   outside the canvas. The canvas is `role="img"` with an `aria-label`.

**Owned elsewhere — do not duplicate:**

| Topic | Owner |
|---|---|
| Token values, series slot order, the three-series limit, never colour alone | `@skills/theming/references/platform-integration.md` (Chart colors) |
| Which chart answers which question; dashboard layout | `@skills/ui-ux-patterns/references/screen-patterns.md` |
| Stimulus scoping and values; Frames and Streams; component spec setup | `references/stimulus-wiring.md`, `references/turbo-frames-and-streams.md`, `references/testing.md` |
| Locale files, `I18n.l`, `number_to_currency` | the `std-i18n` skill |
| The Content-Security-Policy header itself | the `std-security` skill |
| Aggregating series in SQL, N+1 | the `std-database` skill |

---

## Decision: Chartkick, a community controller, or the house controller

| Criterion | Chartkick gem 5.2.1 | `@stimulus-components/chartjs` 6.0.1 | House controller |
|---|---|---|---|
| Script | One inline `<script>` per chart, nonce'd, carrying the data (Chartkick — helper.rb v5.2.1) | External module | External module |
| Styles | An inline `style` on the wrapper. A strict `style-src` blocks it — reproduced in Chrome 152, where the wrapper collapsed to 18px — and Chartkick's own guide asks for `'unsafe-inline'` styles (Chartkick — Content-Security-Policy guide; SDH research lab — Chart.js under a strict CSP, Chrome 152) | None | None |
| Teardown | Destroys only on `turbo:before-render`; a chart removed by a Frame or Stream stays registered in `Chart.instances` (chartkick.js — index.js v5.0.1) | `disconnect()` destroys; nothing for the Turbo cache or previews | Disconnect, cache, preview and morph refresh |
| Registration | The `chart.js/auto` bundle | Every registerable at import | Only what you render |
| Tokens, i18n, text alternative | English "Loading...", `#999`, a Lucida font stack; no text alternative | None | Token colours, locale, figure and table |

**Verdict: the house controller.** "Community libraries first" still holds — Chart.js does the
drawing; the house owns about 80 lines of Stimulus glue. The community controller covers only the
smallest part of that job, and its published package ships no LICENSE file
(`@stimulus-components/chartjs` — package 6.0.1).

---

## Decision: installing Chart.js

### jsbundling-rails (preferred)

```sh
npm install --save-exact chart.js@4.5.1
```

```js
// app/javascript/charts/register.js — the only module that imports chart.js; register what you render
import {
  BarController, BarElement, CategoryScale, Chart, Legend, LinearScale,
  LineController, LineElement, PointElement, Tooltip,
} from "chart.js"

Chart.register(BarController, BarElement, CategoryScale, Legend, LinearScale,
  LineController, LineElement, PointElement, Tooltip)

export { Chart }
```

- Chart.js is tree-shakeable, so a bundled app registers controllers, elements, scales and plugins
  itself; `chart.js/auto` is the quick start "if you don't care about the bundle size" (Chart.js
  docs — Integration).
- Minimums: a bar chart needs `BarController`, `BarElement`, `CategoryScale`, `LinearScale`; a line
  chart `LineController`, `LineElement`, `PointElement` and the two scales; doughnut and pie need
  their controller plus `ArcElement`. `fill` needs `Filler`: without it Chart.js 4.5.1 draws no fill
  and logs `Tried to use the 'fill' option without the 'Filler' plugin enabled` (Chart.js source
  v4.5.1 — core.datasetController.js).

### importmap-rails: why `bin/importmap pin chart.js` breaks, and what to commit instead

- **`dist/chart.js` is not one file.** It imports a relative chunk and the bare specifier
  `@kurkle/color` (chart.js — package 4.5.1). `bin/importmap pin` downloads each URL in the JSPM
  response's `imports` map and never reads its `staticDeps`, so `@kurkle/color` is vendored but the
  chunk (`../_/MwoWUuIu.js` on JSPM) is not, and it 404s at runtime (importmap-rails — packager.rb
  v2.2.3; importmap-rails — issues #153 and #302). The jsDelivr `+esm` build is no escape either: it
  still imports `/npm/@kurkle/color@0.3.4/+esm` from the CDN's host root.
- **Option A — move the app to jsbundling-rails.** Do this when charts are more than one screen.
- **Option B — commit a single-file ESM build of the exact version.** esbuild inlines
  `@kurkle/color`, so it needs **no pin of its own**; the one file rendered under a strict CSP with
  zero violations (SDH research lab — Chart.js under a strict CSP, Chrome 152).

```sh
# In a scratch directory, once per version bump — an importmap app has no node_modules.
npm install --no-save chart.js@4.5.1
npx esbuild@0.28.2 node_modules/chart.js/dist/chart.js --bundle --format=esm --minify \
  --banner:js="/* chart.js 4.5.1 + @kurkle/color, single-file ESM. Regenerate with the command in config/importmap.rb */" \
  --outfile=chart.js.js
# Copy chart.js.js into the app's vendor/javascript/.
```

```ruby
# config/importmap.rb
pin "chart.js" # vendor/javascript/chart.js.js: esbuild single-file ESM of chart.js 4.5.1 (see charts.md)
pin_all_from "app/javascript/charts", under: "charts"
```

- `pin "chart.js"` with no `to:` maps to `chart.js.js` — the file name `bin/importmap pin` itself
  would write (importmap-rails — map.rb v2.2.3). Under importmap the controller imports
  `"charts/register"`, not the relative path shown below.
- **No time scale on importmap.** The date adapter plus date-fns resolve to 264 modules through
  JSPM. Send category labels already formatted by `I18n.l`. `chart.js/helpers` is not in the single
  file either, so derived translucent fills are jsbundling-only.
- **A real time axis (jsbundling only):** `npm install chartjs-adapter-date-fns date-fns`, import the
  adapter once in `register.js`, and pass the date-fns locale as `scales.x.adapters.date.locale`.
  Without an adapter the time scale throws "This method is not implemented: Check that a complete
  date adapter is provided." (Chart.js docs — Time Cartesian Axis).

---

## Decision: the Phlex organism — figure, caption, summary, table

The controller builds a value object from already-aggregated rows. Components receive it; they never
query, format, or look up translations of their own.

```ruby
# app/models/charts/dataset.rb — built by the controller; no queries
module Charts
  class Dataset < Data.define(:type, :axis_label, :labels, :series, :number_format)
    Series = Data.define(:label, :token, :values, :formatted) # token: "--chart-1"; formatted: display strings

    def payload
      { labels:, format: number_format,
        series: series.map { |s| { label: s.label, token: s.token, values: s.values } } }
    end
  end
end
```

```ruby
# app/components/organisms/chart_figure.rb
class Components::Organisms::ChartFigure < Components::Base
  def initialize(title:, summary:, dataset:, table_visible: false)
    @title = title
    @summary = summary
    @dataset = dataset
    @table_visible = table_visible
  end

  def view_template
    figure(class: "space-y-2") do
      figcaption(class: "text-sm font-medium text-foreground") { @title }
      p(class: "text-sm text-muted-foreground") { @summary }
      div(class: "relative h-64 w-full",
          data: { controller: "chart", chart_type_value: @dataset.type, chart_payload_value: @dataset.payload.to_json }) do
        canvas(role: "img", aria_label: @title,
               data: { chart_target: "canvas", action: "turbo:before-morph-element->chart#keepCanvas" })
      end
      render Components::Molecules::ChartDataTable.new(caption: @title, dataset: @dataset, visible: @table_visible)
    end
  end
end
```

```ruby
# app/components/molecules/chart_data_table.rb
class Components::Molecules::ChartDataTable < Components::Base
  def initialize(caption:, dataset:, visible: false)
    @caption = caption
    @dataset = dataset
    @visible = visible
  end

  def view_template
    table(class: @visible ? "w-full text-sm" : "sr-only") do
      caption { @caption }
      thead { tr { th(scope: "col") { @dataset.axis_label }; @dataset.series.each { |s| th(scope: "col") { s.label } } } }
      tbody { @dataset.labels.each_with_index { |label, row| data_row(label, row) } }
    end
  end

  private

  def data_row(label, row)
    tr do
      th(scope: "row") { label }
      @dataset.series.each { |s| td { s.formatted[row] } }
    end
  end
end
```

- **`to_json`, never a Hash.** Phlex double-quotes attribute values and escapes `"` as `&quot;`, so
  the JSON survives as one attribute (Phlex source v2.4.1 — sgml/attributes.rb), and Stimulus reads
  an Object value with `JSON.parse` (Stimulus reference — Values). A Hash in `data:` is not JSON.
- **The container carries the size; the canvas carries none.** Chart.js watches the parent, which
  must be "relatively positioned and dedicated to the chart canvas only". Relative sizes on the
  canvas blur it, and `margin: auto` makes it shrink forever (Chart.js docs — Responsive Charts).
- **The table sits outside the canvas.** Children of `role="img"` are presentational, so a table
  inside the canvas is not exposed as a table (W3C — WAI-ARIA 1.2: img role). `sr-only`, or a visible
  `<details>` "Show data" — never `hidden`. The canvas label is a short name; the table carries the
  values (Chart.js docs — Accessibility).
- **The summary is a sentence built from the data** in the controller: total, peak, trend, through
  `t(".summary", …)`. `token` values are custom-property names, never colours.

```ruby
# app/controllers/dashboards_controller.rb — excerpt
def show
  months = Orders::MonthlyTotals.call(scope: policy_scope(Order)) # [[Date, BigDecimal]], aggregated in SQL
  revenue = Charts::Dataset::Series.new(label: t(".revenue"), token: "--chart-1",
    values: months.map { |(_, sum)| sum.to_f }, formatted: months.map { |(_, sum)| helpers.number_to_currency(sum) })
  dataset = Charts::Dataset.new(type: "bar", axis_label: t(".month"), series: [revenue],
    labels: months.map { |(month, _)| l(month, format: :month) },
    number_format: { style: "currency", currency: current_organization.currency }) # Intl.NumberFormat options
  peak_month, = months.max_by(&:last)
  render Views::Dashboards::Show.new(dataset:, summary: t(".summary", peak: l(peak_month, format: :month)))
end
```

---

## Decision: the Stimulus controller

```js
// app/javascript/controllers/chart_controller.js
import { Controller } from "@hotwired/stimulus"
import { Chart } from "../charts/register" // importmap: "charts/register"

const motion = window.matchMedia("(prefers-reduced-motion: reduce)")
const cssValue = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim()
const CARTESIAN = ["bar", "line"]

export default class extends Controller {
  static targets = ["canvas"]
  static values = { type: String, payload: Object }

  initialize() {
    this.build = this.build.bind(this)
    this.restyle = this.restyle.bind(this)
    this.teardown = this.teardown.bind(this)
  }

  connect() {
    if (document.documentElement.hasAttribute("data-turbo-preview")) return // a cached preview has no canvas pixels
    this.theme = new MutationObserver(this.restyle)
    this.theme.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] })
    motion.addEventListener("change", this.restyle)
    document.addEventListener("turbo:before-cache", this.teardown)
    document.addEventListener("turbo:render", this.build)
    this.build()
  }

  disconnect() {
    this.theme?.disconnect()
    motion.removeEventListener("change", this.restyle)
    document.removeEventListener("turbo:before-cache", this.teardown)
    document.removeEventListener("turbo:render", this.build)
    this.teardown()
  }

  payloadValueChanged() { this.restyle() } // also runs before connect; restyle() needs a live chart

  keepCanvas(event) { if (event.target === this.canvasTarget) event.preventDefault() }

  build() {
    if (this.chart) return
    Chart.getChart(this.canvasTarget)?.destroy()
    this.chart = new Chart(this.canvasTarget, { type: this.typeValue, data: this.chartData(), options: this.chartOptions() })
  }

  restyle() {
    if (!this.chart) return
    this.chart.data = this.chartData()
    this.chart.options = this.chartOptions() // Chart.defaults changes never reach a live chart
    this.chart.update("none")
  }

  teardown() {
    this.chart?.destroy() // restores the canvas before Turbo snapshots the page
    this.chart = null
  }

  chartData() {
    const { labels, series } = this.payloadValue
    const datasets = series.map(({ label, token, values }, index) => {
      const color = cssValue(token)
      const dash = this.typeValue === "line" && index > 0 ? [6, 4] : [] // never colour alone
      return { label, data: values, backgroundColor: color, borderColor: color,
               hoverBackgroundColor: color, hoverBorderColor: color, borderDash: dash }
    })
    return { labels, datasets }
  }

  chartOptions() {
    const text = cssValue("--muted-foreground")
    const grid = cssValue("--border")
    const axis = (ticks = {}) => ({ ticks: { color: text, ...ticks }, grid: { color: grid }, border: { color: grid } })
    return {
      maintainAspectRatio: false,
      animation: motion.matches ? false : { duration: 400 },
      locale: document.documentElement.lang || undefined,
      plugins: { legend: { labels: { color: text } } },
      ...(CARTESIAN.includes(this.typeValue) && { scales: { x: axis(), y: axis({ format: this.payloadValue.format }) } }),
    }
  }
}
```

Why each lifecycle choice:

- **The preview skip.** Turbo snapshots the page with `cloneNode(true)`, which does not copy painted
  canvas pixels, and marks `<html>` with `data-turbo-preview` while a cached preview shows (Turbo
  Handbook — Building Your Turbo Application: caching). `turbo:render` fires twice on such a visit
  (Turbo reference — Events); the real render connects a fresh controller.
- **`Chart.getChart(canvas)?.destroy()`.** Building on a canvas that still holds a chart throws
  "Canvas is already in use. Chart with ID '…' must be destroyed before the canvas with ID '…' can be
  reused." (Chart.js source v4.5.1 — core.controller.js).
- **Destroy on `disconnect`.** Stimulus calls it when the element or an ancestor is removed — which
  covers Frame and Stream replacements — and when Turbo installs a new `<body>` (Stimulus reference —
  Lifecycle Callbacks). A canvas removed without `destroy()` stays in `Chart.instances`; only
  `destroy()` deletes it (Chart.js docs — API: destroy).
- **Destroy on `turbo:before-cache`**, the event Turbo recommends for tearing down third-party
  widgets. `destroy()` restores the canvas' initial size, so the snapshot holds a pristine canvas.
- **Rebuild on `turbo:render`.** A morphing GET refresh to the same path also dispatches
  `turbo:before-cache` while the controller stays connected; a teardown alone would leave it blank
  (Turbo source 8.0.23 — Visit.loadResponse, PageView.cacheSnapshot).
- **`keepCanvas`.** Cancelling `turbo:before-morph-element` preserves the element Chart.js wrote to
  (Turbo Handbook — Page Refreshes). The payload attribute on the container still morphs, which calls
  `payloadValueChanged`. **Not tested end to end — verify in the app.**
- **Hidden containers.** Chart.js skips a 0×0 resize entry ("When its container's display is set to
  none… skip resizing") and resizes once the container has size (Chart.js source v4.5.1 —
  platform.dom.js). A chart in a closed `<details>` or a hidden tab panel draws when shown. Read from
  source, not browser-tested.
- **Name the builders `chartData`/`chartOptions`.** A `data()` method would shadow the controller's
  own `this.data`.

---

## Decision: colours, dark mode, motion

- **Tokens are complete colours.** The house stylesheet declares `--chart-1: hsl(217.2 91.2% 50%)`
  (`platform-integration.md`), a form Chart.js's colour parser accepts. It rejects `var(--chart-1)`,
  bare channels (`217.2 91.2% 50%`), slash alpha in `hsl(… / 0.5)`, `oklch()`, `color-mix()` and
  untrimmed values — hover colours become `undefined` — and the canvas silently ignores `var()` and
  bare channels (SDH research lab — @kurkle/color 0.3.4 and canvas fillStyle checks, Chrome 152).
  Always `.trim()`; always set hover colours explicitly.
- **Dark mode re-themes through the chart's own options.** The `.dark` class on `<html>` is the only
  switch (`platform-integration.md`); the observer calls `restyle()`. Setting `Chart.defaults.color`
  after a chart exists changes nothing on it; assigning `chart.options` does (SDH research lab —
  Chart.defaults vs chart.options).
- **Translucent fills** (jsbundling only): `color(cssValue("--chart-1")).alpha(0.2).rgbString()` from
  `chart.js/helpers`.
- **Motion.** Chart.js animates for 1000ms by default and contains no reduced-motion handling;
  `animation: false` also stops the tooltip's animation (Chart.js docs — Animations). The stylesheet's
  reduced-motion backstop cannot reach canvas drawing, so the controller reads the media query and
  re-applies on its `change` event.

---

## Decision: CSP, numbers, and large series

- **CSP.** Chart.js 4.5.1 writes canvas styles only through CSSOM properties (`display`,
  `box-sizing`, `width`, `height`), and "styles properties that are set directly on the element's
  style property will not be blocked" (MDN — CSP: style-src). Under `style-src 'self'` a Chart.js bar
  chart raised no violation (SDH research lab — Chart.js under a strict CSP, Chrome 152). A chart
  therefore needs no `'unsafe-inline'`, no `'unsafe-eval'` and no nonce of its own. Never put `style:`
  in chart markup.
- **HTML tooltips or legends, if ever required, build nodes with `textContent`.** The docs' external
  tooltip example concatenates labels into `innerHTML`, an XSS sink once labels carry user data
  (Chart.js docs — Tooltip: External (Custom) Tooltips). Canvas tooltips need none of this.
- **People read server-formatted strings.** The table and summary use `number_to_currency` and
  `I18n.l` (`std-i18n`). On the canvas, `locale` comes from `<html lang>` and `ticks.format` takes the
  `Intl.NumberFormat` options the server sent as `number_format`; unset, Chart.js formats in the
  platform's locale, not the app's (Chart.js docs — Locale).
- **Large series.** Aggregate in SQL first. Beyond that: pre-shaped `{ x, y }` data with
  `parsing: false` and `normalized: true`, and `animation: false`. The decimation plugin works only on
  line datasets with an `x` index axis, a linear or time x scale, `parsing: false` and more points
  than its threshold — otherwise it silently does nothing (Chart.js docs — Performance; Chart.js docs
  — Data Decimation).

---

## Decision: testing a chart

Assert the contract the server renders — payload, name, table — and one smoke check that the
controller built. Never pixels.

```ruby
# spec/components/organisms/chart_figure_spec.rb
require "rails_helper"

RSpec.describe Components::Organisms::ChartFigure, type: :component do
  let(:series) { Charts::Dataset::Series.new(label: "Revenue", token: "--chart-1", values: [1200.0, 900.0], formatted: %w[€1,200 €900]) }
  let(:dataset) { Charts::Dataset.new(type: "bar", axis_label: "Month", labels: %w[Jan Feb], series: [series], number_format: {}) }
  let(:doc) { Nokogiri::HTML5.fragment(render(described_class.new(title: "Revenue", summary: "Peak in Jan.", dataset:))) }

  it "should hand the controller its payload as JSON when rendered" do
    payload = JSON.parse(doc.at_css("[data-controller='chart']")["data-chart-payload-value"])

    expect(payload["series"].first).to include("token" => "--chart-1", "values" => [1200.0, 900.0])
  end

  it "should name the canvas as an image when rendered" do
    expect(doc.at_css("canvas").to_h).to include("role" => "img", "aria-label" => "Revenue")
  end

  it "should render every value in a table outside the canvas when rendered" do
    rows = doc.css("table tbody tr").map { |tr| tr.css("th, td").map(&:text) }

    expect(rows).to eq([%w[Jan €1,200], %w[Feb €900]])
    expect(doc.at_css("canvas table")).to be_nil
  end

  it "should write no style attribute when rendered" do
    expect(doc.css("[style]")).to be_empty
  end
end
```

```ruby
# spec/system/dashboard_chart_spec.rb — a JS driver, with the production CSP enabled
RSpec.describe "Dashboard chart", type: :system do
  it "should build the chart when the dashboard loads" do
    # Arrange: sign in with the app's auth helper as a role that can read orders
    visit dashboard_path

    expect(page).to have_css("[data-controller='chart'] canvas[style*='box-sizing']") # written by Chart.js on build
    built = "!!Stimulus.getControllerForElementAndIdentifier(document.querySelector('[data-controller=chart]'), 'chart').chart"
    expect(page.evaluate_script(built)).to be(true)
  end
end
```

- `window.Stimulus` is assigned by stimulus-rails' generated `controllers/application.js`; Chart.js
  itself is a module, not a global, so `Chart.getChart` is not reachable from `evaluate_script`.
- Also fail the system spec on any console message naming Content-Security-Policy, or Chart.js's
  `Tried to use the 'fill' option without the 'Filler' plugin enabled` warning, read through the
  driver's browser log.
- If the payload-to-dataset mapping grows logic, move it into a plain function and test it in JS.

---

## Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| A 404 for `…/_/….js` after `bin/importmap pin chart.js` | Only the entry files are vendored, not the chunk | jsbundling, or the committed single-file build |
| "Canvas is already in use" | Built twice on one canvas | `Chart.getChart(canvas)?.destroy()` before `new Chart` |
| A blank chart after Back or a refresh | Torn down for the cache, never rebuilt, or built on a preview | The preview skip plus the `turbo:render` rebuild |
| A blurred, shrinking or unsized chart | Canvas sized with relative units, or a shared container | Sized `relative` container holding only the canvas; `maintainAspectRatio: false` |
| `"arc" is not a registered element` | Missing registration | Add it to `register.js` |
| No fill under a line, and a console warning naming the `Filler` plugin | `fill` set, `Filler` not registered | Add `Filler` to `register.js` |
| Axes drawn on a doughnut | Cartesian `scales` passed to a radial type | Only cartesian types get `scales` |

---

## Sources

- Chart.js docs — Integration; Responsive Charts; Animations; Colors; Accessibility; API (destroy,
  getChart); Updating Charts; Locale; Performance; Data Decimation; Time Cartesian Axis; Tooltip —
  https://www.chartjs.org/docs/latest/
- Chart.js source v4.5.1 — core.controller.js, core.datasetController.js, platform.dom.js — https://github.com/chartjs/Chart.js/tree/v4.5.1/src
- chart.js — package 4.5.1 (MIT, `@kurkle/color` dependency) — https://cdn.jsdelivr.net/npm/chart.js@4.5.1/package.json
- importmap-rails — packager.rb and map.rb v2.2.3 — https://github.com/rails/importmap-rails/tree/v2.2.3/lib/importmap
- importmap-rails — issue #153 (multi-file dependencies) and #302 (package directory downloads) — https://github.com/rails/importmap-rails/issues
- Chartkick — helper.rb v5.2.1; Content-Security-Policy guide — https://github.com/ankane/chartkick/tree/v5.2.1
- chartkick.js — index.js v5.0.1 — https://github.com/ankane/chartkick.js/blob/v5.0.1/src/index.js
- `@stimulus-components/chartjs` — package 6.0.1 — https://registry.npmjs.org/@stimulus-components%2Fchartjs
- Turbo Handbook — Building Your Turbo Application (caching); Page Refreshes — https://turbo.hotwired.dev/handbook/
- Turbo reference — Events — https://turbo.hotwired.dev/reference/events
- Turbo source 8.0.23 — turbo.es2017-esm.js — https://cdn.jsdelivr.net/npm/@hotwired/turbo@8.0.23/dist/turbo.es2017-esm.js
- Stimulus reference — Values; Lifecycle Callbacks — https://stimulus.hotwired.dev/reference/
- Phlex source v2.4.1 — sgml/attributes.rb — https://github.com/yippee-fun/phlex/blob/2.4.1/lib/phlex/sgml/attributes.rb
- MDN — CSP: style-src — https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/style-src
- W3C — WAI-ARIA 1.2: img role — https://www.w3.org/TR/wai-aria-1.2/#img
- SDH research lab (2026-09, Chrome 152 via Playwright) — Chart.js 4.5.1 under a strict CSP;
  @kurkle/color 0.3.4 and canvas fillStyle checks; Chart.defaults vs chart.options
