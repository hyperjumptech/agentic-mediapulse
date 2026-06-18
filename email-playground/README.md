# email-playground

The home for MediaPulse's [React Email](https://react.email/components) templates and their live
preview. Each template lives as a React component under `emails/`. A template can also export a
tokenized HTML build that the Python app fills at send time. The newsletter is the first such
template; others can be added the same way.

## Setup

```
npm install
```

## Design and preview

```
npm run dev
```

Opens the React Email preview server at http://localhost:3000. Every component in `emails/` shows
up, rendered from its `PreviewProps`. Edits hot-reload. Styling is Tailwind via react-email's
`<Tailwind>` component, inlined into the HTML at render time.

## Build the tokenized templates

```
npm run build:templates
```

For every `emails/*.tsx` that exports both a default component and a `templateProps` object, this
renders the component in template mode and writes `../src/emails/templates/<name>.html`: a tokenized HTML
file with `{{placeholders}}` and `<!--#region-->…<!--/region-->` blocks that the Python side fills
per message. The output is a gitignored build artifact, regenerated in CI and the Docker build.
**The Python tests and the running app require these files**, so run it once after `npm install`.

## Adding a template that the Python app can fill

1. Create `emails/<name>.tsx` with a default-exported component and a `PreviewProps` for the dev
   server.
2. Add a `templateMode` prop. When set, wrap variable, repeatable, and optional regions in
   `<Region name="...">` (which emits `[[#name]]`/`[[/name]]` markers) and leave content as
   `{{token}}` placeholders.
3. Export `templateProps`: the props that drive template-mode rendering.
4. Run `npm run build:templates`, then fill `src/emails/templates/<name>.html` from Python.

Templates without `templateProps` are preview-only and are skipped by the build.

## Newsletter token reference

| Token / region                         | Filled by Python with                          |
| --------------------------------------- | ---------------------------------------------- |
| `{{title}}`                             | title (the markdown `#` heading)               |
| `<!--#standfirst-->` `{{summary}}`      | the standfirst paragraph (omitted if empty)    |
| `<!--#sections-->`                      | placeholder for all rendered sections          |
| `<!--#section-->` `{{section_name}}`    | a standard section, repeated per section       |
| `<!--#quickhits-->`                     | the highlighted Quick Hits panel variant       |
| `<!--#sectionsep-->`                    | separator, kept between sections, dropped first|
| `<!--#item-->` `{{item_summary}}`       | repeated once per item in a section            |
| `<!--#itemsep-->`                       | separator, kept between items, dropped on first|
| `<!--#readlink-->` `{{item_url}}` / `{{item_title}}` | the "Read:" citation (omitted if no URL) |
| `{{footer_note}}`                       | the subscription footer line                   |
| `<!--#unsubscribe-->` `{{unsubscribe_url}}` / `{{symbol}}` | unsubscribe link (omitted if no URL) |

The section names come from [`src/utils/sections.py`](../src/utils/sections.py); the one matching
`QUICK_HITS` renders in the highlighted panel.
