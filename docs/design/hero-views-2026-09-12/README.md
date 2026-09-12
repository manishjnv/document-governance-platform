# Hero views — calm light direction (2026-09-12, design only)

Live interactive canvas: https://claude.ai/code/artifact/42cf7d18-6875-4c35-970c-e8db1f1fcee7

Three signature screens, each a working prototype, each fluid-width with media
queries so the same file renders at 1440 and 390:

- `Main.dc.html` — SOW review as an annotated document. Click a finding or a
  sentence to pin them; Mark fixed recomputes the risk score, bar and area chips.
- `MitreTimeline.dc.html` — ATT&CK heatmap over eight runs. Drag the timeline,
  click a dot, or Play; cells turn green in the run that covered them; hover for
  the covering rule.
- `ExploitChains.dc.html` — attack graph. Click a node or step chip to fix it;
  edges go dashed and chains flip to Broken; Fewest fixes applies the set-cover.
- `*Phone.dc.html` are the same files framed at 390px.

References held against: Linear, Attio, Vercel, Wiz, Notion. System: Instrument
Serif headlines, Instrument Sans UI, JetBrains Mono IDs; paper #FBFAF7, ink
#1B1F27, accent #2B62C9, four-step severity ramp with soft tints; 10px radius,
one shadow, one easing curve. `gen.py` regenerates everything; reseed via the
design skill. Not designed yet on purpose: shells, nav, tables, settings.
