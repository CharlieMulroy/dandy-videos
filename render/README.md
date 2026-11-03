# render

Python renderer. Planned stack: Pillow + cairosvg for frames, ffmpeg for assembly.

- `render.py <videos/NN-slug>` reads `scenes.json`, `style/contract.json`, and the cast/motif
  SVGs, renders every frame for both canvases, runs `checks/`, writes MP4s and a contact
  sheet to `out/`.
- `checks/` fail the render (and the Dandy QA verdict) on: element overlap or gap < 48 px,
  anything outside the safe zone, banned characters or phrases, more than one gold element
  per frame, missing or modified end card.
