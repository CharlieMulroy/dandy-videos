# dandy-videos

Code-generated marketing videos for Dandy (dandylabs.dev).

Every video is rendered by the same Python template from a scene spec, using the shared
Style Contract and Cast. Rules live in Dandy (the "Dandy Marketing" product); this repo holds
the files those rules point at.

```
style/contract.json        palette, type, grid, safe zones, motion, copy rules
cast/dandy-man/            Dandy Man SVG poses
cast/figures/              stick-figure templates (employee, boss, team)
motifs/                    graph, session reset, context rot, end card
render/                    the renderer (one template for every video)
render/checks/             automated QA: overlap, safe zone, copy rules, gold count
videos/NN-slug/            script.md, scenes.json, out/ (rendered MP4s, contact sheet)
```

Rendered MP4s are not committed; they go to the shared drive and Dandy stores the link.
