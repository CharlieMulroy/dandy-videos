# dandy-videos

Code-generated marketing videos for Dandy (dandylabs.dev).

Every video is rendered by the same Python template from a scene spec, using the shared
Style Contract and Cast. Rules live in Dandy (product "Dandy Marketing", id 35809f49-b7df-47fd-bdfb-5429ea6b7576);
this repo holds the files those rules point at. Dandy invariants 2, 3 and 4 are enforced by
`render/checks.py`; report each run's results back to Dandy after rendering.

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

## Picking this up in a new session

1. Read the Dandy product "Dandy Marketing" (get_product) for the rules and the state of each video.
2. Clone this repo. `pip install cairosvg pillow pocketsphinx`; ffmpeg and the Inter font must be present.
3. Smoke test: `python3 render/render.py videos/00-render-test --preview` must pass QA.
4. New video: copy `videos/01-why-dandy/` as a template (script.md, scenes.json, captions.json, voiceover/).
   Claim the video's nodes in Dandy with your own session_id; review from a different session.
5. Voiceover alignment: transcribe with pocketsphinx (absolute word times) plus ffmpeg silencedetect,
   map speech chunks to script sentences, set each scene's duration so its narration starts ~0.5 s in,
   write captions.json cues from the chunk times. Audio is muxed by render.py from scenes.json "audio".
6. Drafts: `render.py <video> --canvas vertical`; final: `--final` (2x supersample, crf 17, ~7 min).
7. After every render, report_test_results to Dandy for the three check names in invariants 2, 3, 4.

Video 01 final: videos/01-why-dandy/out/01-why-dandy-vertical-final.mp4 (44.6 s, take 2 narration, captions).
Held for Nick's review alongside videos 02 and 03 before posting.
