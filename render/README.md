# render

Python renderer: Pillow + cairosvg for frames, ffmpeg for assembly.

```
pip install cairosvg pillow      # ffmpeg and the Inter font must be installed
python3 render/render.py videos/01-why-dandy            # both canvases, 30 fps
python3 render/render.py videos/01-why-dandy --preview  # 10 fps, quick look
```

`render.py` reads `<video>/scenes.json`, `style/contract.json`, and the SVG assets; lays each
scene out on the 24 px grid; runs `checks.py`; renders frames for the vertical (1080x1920)
and horizontal (1920x1080) canvases; writes MP4s, a contact sheet (one frame per scene) and
`qa-<canvas>.json` to `<video>/out/`.

The scene spec format is documented at the top of `render.py`. Positions are fractions of
the canvas so one spec renders both sizes; `height_horizontal` overrides a sprite's height
on the wide canvas.

## QA checks (any failure stops the render)

- Layout: no element outside the safe zone; every pair of elements at least 48 px apart.
- Copy: no long dashes; no banned phrases; headline max 2 lines, body max 3; max 12 words on screen.
- Gold: at most one element flagged `gold` per scene. (The check reads the spec, not pixels:
  a sprite that contains gold, like Dandy Man holding the node, must be flagged `gold: true`.)
- End card: the last scene must be `end_card`, which is composed by the renderer from the
  contract so it is identical in every video.

`videos/00-render-test/` is a smoke test of every element type; keep it passing.
