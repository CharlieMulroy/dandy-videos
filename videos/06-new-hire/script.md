# 06 The New Hire

**Takeaway:** AI agents are the most capable employee you will ever have, and they forget the job every session. Dandy holds the state of the project so you get their full potential. (Dandy: the last two beats.)

**Kind:** metaphor video (third kind). No Dandy Man. Look: the Maya lofi style from video 02, moved to an office.
Code-drawn SVG room layers (back wall, desk, figure, front props) rastered at 2x, a fixed camera that only ever
drifts or pushes a little, hard cuts between still shots, and tiny ambient motion: coffee steam, a blinking cursor,
light through the blinds, a slow sky change outside the window. The hire is a Maya-style figure, realistic but
cartoonish, in a shirt and tie with glasses (the cape was cut after v1). No ChatGPT stills for now; the v1 prompts are parked at the bottom in
case we want painted upgrades later.

**Target length:** about 38 s (about 95 narrated words). Status: v2 approved Nov 8 (turn line, final line and cape chosen). v1 was a 55 s workplace comedy
with a painted cast; Charlie asked for shorter and straight to the point, still shots with a little motion, the
Maya look, and an explicit turn: this employee is your AI agent, don't let your use of them be limited, unlock
their potential with Dandy, one sentence on how.

| # | Sec | Visual | On-screen text | Narration (plain, dry) |
| --- | --- | --- | --- | --- |
| 1 | 0-4 | Cold open. Lofi office, morning light in beams through the blinds. The hire at his desk, cape over the back of the chair, mug steaming. One slow push in. | "the new hire" | Meet your new hire. He can do anything. |
| 2 | 4-11 | Three still shots, about 2.3 s each, one small motion in each. (a) The whiteboard: a full architecture diagram already drawn, he stands beside it with a marker, the last arrow draws itself. (b) The desk: three monitors, code scrolling slowly on all of them, his hands on the keyboard. (c) A stack of binders on the desk, he holds the top one open, pages flip once. | "designs it before lunch" / "builds it after" / "reads everything you have" | Designs the whole system before lunch. Builds it after. Reads every document you have in seconds. |
| 3 | 11-18 | Back to the shot-1 framing, next morning: the light is a touch different, the whiteboard behind him is wiped to a few grey smears, two sticky notes on the monitor bezel. On the screen, a chat window: "Morning! So, what are we working on?" Cursor blinks. He looks at the board. | "day 2" | He has one flaw. Every morning, he forgets. The project, the plan, what he built yesterday. All of it. |
| 4 | 18-25 | The turn. Same shot, the room holds. The colour drains a little from everything except him, and big centred type lands. Then a small second line. | "This is your AI agent" / "Powerful. And starting from zero every session." | That employee is your AI agent. Extremely powerful. And starting from zero every single session. |
| 5 | 25-33 | Push in on the monitor (the Maya screen move). A Dandy panel opens, the only purple in the film: a project card, "Budget app: auth done, billing next, decided: Postgres." The sticky notes peel off the bezel and drift away. Chat: "Reading Dandy. Auth is done, billing is next. Starting there." | "reads the state first" / "writes back what changed" | Don't let that limit what they can do. Dandy holds the state of your project. The agent reads it before it starts, and writes back what it changed. Nothing is forgotten. |
| 6 | 33-38 | End card, the panel's purple settling behind it: the hat logo, the wordmark, dandylabs.dev, 14-day free trial. | "Unlock their full potential." / "Use Dandy." | Unlock their full potential. Use Dandy. |

## Narration, read straight through

Meet your new hire. He can do anything.

Designs the whole system before lunch. Builds it after. Reads every document you have in seconds.

He has one flaw. Every morning, he forgets. The project, the plan, what he built yesterday. All of it.

That employee is your AI agent. Extremely powerful. And starting from zero every single session.

Don't let that limit what they can do. Dandy holds the state of your project. The agent reads it before it starts, and writes back what it changed. Nothing is forgotten.

Unlock their full potential. Use Dandy.

## Build notes (for the scene spec)

- Reuse from videos/02-maya/lofi: the layer pipeline (gen_room.py pattern, SVG layers rastered at SCALE 2), room_frame camera with WIDE and SCREEN_CAM style presets, draw_steam, draw_screen chat window, sticky-note peel from NOTES_PEEL, caption and end_card. New: an office back wall (blinds, whiteboard, shelf), a desk with three monitors, the hire figure in three poses (at desk, at whiteboard, holding binder), a cape.
- Six shots, all fixed camera except the shot-1 push and the shot-5 screen push. Ambient motion only: steam, cursor, light beams, one drawing arrow, slow code scroll, one page flip.
- The turn (beat 4) is a grade change plus type, not a scene change: desaturate the room 30 percent over 0.6 s, keep the figure at full colour, slam the headline.
- Purple appears only in the Dandy panel and the end card. Gold: nothing except the end card line.
- Sound: a soft lofi bed like 02, a page-flip, a marker squeak, a chat pop, the Dandy chime at the panel.

## Messaging check

- Leads with the hire and his flaw; the product arrives at 25 s with two sentences.
- Says what Dandy is in plain words (holds the state of your project) and how it fixes the flaw (reads before it starts, writes back what changed): the approved "agents keep it current" framing.
- No comparison to project management tools, no harness or framework, no promises, no long dashes, no Dandy Man.

## Decisions (Nov 8)

1. On-screen turn: "This is your AI agent".
2. Final line: "Unlock their full potential. Use Dandy." on the end card with the hat logo, wordmark and dandylabs.dev.
3. The hire is a normal guy: no cape (cut after the v1 preview), shirt, tie, lanyard and glasses. His "superpowers" are only what he does in beat 2.

## Parked: v1 painted-still prompts

Not needed for v2. Kept in case we want painted upgrades of the figure or the room later.

### Painted stills: prompts for ChatGPT (v1)

Same method as the graveyard rider and reaper. Every still on a transparent background (or, if the model cannot, a
flat solid green #00FF00 that I can key out), painterly realistic, consistent lighting (soft warm key from the upper
left, as if from a window). Generate the character sheet first, then every pose in the same thread so the face,
cape, shirt and tie stay consistent. Full body, nothing cropped, feet visible, no ground shadow, no background
objects, no text.

### A. The office (one backdrop, not transparent)

> A painted, realistic illustration of a small modern office seen from a fixed camera at standing eye level, slightly wide angle. One desk centre-left with three dark monitors (screens blank black, no UI), a chair, a tall whiteboard on the right wall that is completely blank, venetian blinds on the back wall with soft warm morning light coming through in visible beams, light dust in the air, a plain carpet floor with open space in front of the desk where a person could stand. Muted palette: warm greys, soft wood, pale blue-grey walls. Absolutely no people, no sticky notes, no text, no plants in the foreground. Painterly but realistic, soft edges, cinematic. Portrait format, 9:16.

### B. The new hire, character sheet

> A painted, realistic character illustration of a superhero office worker: a man in his early thirties, friendly open face, short dark hair, wearing a light blue button-down shirt with the sleeves rolled, a slightly loose dark tie, grey trousers and brown shoes, an employee lanyard with a blank white badge, and a full-length deep red superhero cape fastened at the shoulders. He holds a paper coffee cup in one hand. Standing straight, confident, slight smile, looking at the viewer. Full body head to toe, nothing cropped. Soft warm light from the upper left. Transparent background, no shadow on the ground, no text, no other objects. Painterly but realistic, soft edges.

### C. Poses (same character, same thread, one at a time)

1. Superhero landing: one knee on the ground, one fist down, other hand holding the coffee cup up and level so none spills, cape flaring out behind and above him, head up, grinning. Side-on, facing left. Transparent background.
2. Confused: standing, shoulders up in a shrug, coffee in one hand, other palm open, eyebrows raised, mouth slightly open, looking off to the right. Three-quarter view. Transparent background.
3. Pointing up and to the right at something off-frame with a confident smile, cape hanging still. Three-quarter view. Transparent background.
4. Carrying a black server rack under one arm as if it weighed nothing, other hand holding the coffee, walking left to right, cape trailing. Side-on. Transparent background.
5. Reading: standing, holding a slim closed book-sized ledger open in both hands, head tilted down toward it, calm and focused, coffee cup set aside (not in frame), cape hanging still. Three-quarter view. Transparent background.
6. Sitting at a desk, side-on, facing left, hands on an invisible keyboard (no desk or keyboard in the image, just the pose), leaning in slightly, cape draped over the back of an invisible chair. Transparent background.
7. Cracking his knuckles, standing, small determined smile, cape hanging. Front view. Transparent background.

### D. The manager's hand (optional)

> A painted, realistic illustration of a single adult hand and forearm in a rolled grey shirt sleeve, entering from the left edge of the frame, holding a black whiteboard marker and pointing with it. Transparent background, no body, no other objects, soft warm light from the upper left. Second version: the same hand holding a white ceramic coffee mug.

### E. The Dandy ledger

> A painted, realistic illustration of a slim hardcover notebook or ledger, closed, lying flat and seen from a high three-quarter angle, cover in a deep royal purple (#6B3FA0) with a thin gold line along the spine, no text, no logo, faint soft glow around its edges. Transparent background. Second version: the same ledger open flat, pages blank cream paper, no writing.

Checks before handing stills to the renderer: cape and shirt the same colours in every pose, feet visible, no
ground shadow, no stray background colour at the edges (hold them over a white and a black background to see).

## v1 build notes (Nov 8)

- Built in videos/06-new-hire/lofi/: gen_office.py writes the SVG layers (back, front, hire-typing/confused/binder/board, binder); render_office.py composes the shots on the Maya pipeline (SCALE 2 room, camera crop, shared finish pass).
- Office palette is blue-grey wall, warm wood, red cape; brand purple only in the Dandy panel on the main monitor (with a soft purple spill) and the end card.
- Shots: s1-hire 4.0, s2-design 2.4, s3-build 2.3, s4-docs 2.3, s5-day2 7.0, s6-turn 7.0, s7-dandy 8.0, end 5.0 (38 s). Timings move to voiceover/office.json once narration is recorded.
- Each shot has one small motion: push-in, last arrow drawing, code scroll, page flip, ticking second hand, "?" bubble, grade change, panel slide and sticky-note peel. Ambient: steam, light beams, dust.
- Preview is silent; sound bed and narration come with the recording.
- v2 (Nov 8): cape removed, glasses added; the binder is now held side-on facing him (a shallow V of covers, page turning toward him) instead of facing the camera.
- v3 (Nov 8): the book is held open like a normal book at chest height, pages tipped up toward him, head down reading; one page turns right to left.
