# 07 The Relay

**Takeaway:** Your agents are world-class sprinters who start every leg cold. Dandy is the baton: it carries where the project is, so the next session starts at speed.

**Kind:** metaphor video (same category as 05 The Graveyard). No Dandy Man. Own look; shares only the palette family,
the copy rules and the end card without Dandy Man. Brand purple appears only as the baton (the Dandy element) and on
the end card. Aimed at individual builders: no traction or VC lines, no "state layer" phrasing, no long dashes.

**Look:** a night track meet. Stadium floodlights on tall towers, dark empty stands, a wet track that catches the light
in long streaks. Stylized and dramatic, not cartoon: runners are dark silhouettes with a cold rim light from the
floodlights and a blurred reflection in the wet track. Fully code-drawn (videos/07-relay/track/), with the 04
motion-and-finish pass: spring easing, a drifting camera, bloom on the lights, grain. A stadium board (lap and split)
is the only on-screen text besides the captions.

**Sound:** footfalls on a wet track, breathing, a low crowd murmur from the empty stands, a starter's pistol, a scuff
on each stumble, a clean slap on each good hand-off, a soft tone when the baton lights.

**Target length:** about 44 s (about 60 narrated words). Status: draft v1, Nov 8. Narration to be recorded by Charlie;
the first render carries the sound bed and burned-in captions only, timed to this script.

| # | Sec | Visual | Board | Narration (short lines, plain, a little dry) |
| --- | --- | --- | --- | --- |
| 1 | 0-3 | Cold open, pistol. Tight on a sprinter's feet at full speed, spikes hitting a wet track, light streaking past. Cut: side on at the exchange zone, his arm stretched out to hand off. The hand closes on empty air. The next runner is two strides off his mark, facing the stands. The first runner stumbles to a stop. | none | (none) |
| 2 | 3-10 | Side tracking shots, three legs in a row. Each runner faster than the last. Each one reaches the zone and the next runner is standing still, turned the wrong way, starting from the blocks. The board shows the split dropping and the leg counter never moving. | LEG 1 OF 4 / SPLIT 10.41, 10.32, 10.19 | Every session is brilliant. Every session starts cold. |
| 3 | 10-20 | Pull up to a wide overhead of the track. Eight lanes, eight teams, all dropping their hand-offs: runners pulling up, next runners standing still. In one lane the race is abandoned: a runner sitting on the track. | none | Look at the whole track. Every lane drops it. Some stop running. Nobody is carrying what the last runner knew. |
| 4 | 20-32 | Back to the first runner's hand. A baton appears in it, glowing brand purple, the only purple in the frame. Pistol. The hand-off lands clean: the next runner is already moving, already knows where they are. Each exchange is faster and smoother. | LEG 2 OF 4, 3 OF 4, 4 OF 4 | Dandy is the baton. It holds where the project is, what changed, and what's next. So the next runner starts at speed. Not from the blocks. |
| 5 | 32-40 | Their team pulls away from the other lanes. Cut to the finish: the baton crosses the line, the clock stops. | FINISH | Stop restarting. Start handing off. |
| 6 | 40-44 | End card, metaphor version without Dandy Man: hat, wordmark, dandylabs.dev, 14-day free trial. | none | (none) |

## Narration, read straight through

Every session is brilliant.
Every session starts cold.

Look at the whole track.
Every lane drops it.
Some stop running.
Nobody is carrying what the last runner knew.

Dandy is the baton.
It holds where the project is,
what changed,
and what's next.
So the next runner starts at speed.
Not from the blocks.

Stop restarting.
Start handing off.

## Caption timing (first render, before the voiceover is aligned)

| Sec | Caption |
| --- | --- |
| 4.0-6.6 | Every session is brilliant. |
| 6.8-9.6 | Every session starts cold. |
| 11.0-12.8 | Look at the whole track. |
| 13.0-14.8 | Every lane drops it. |
| 15.0-16.6 | Some stop running. |
| 16.8-19.6 | Nobody is carrying what the last runner knew. |
| 21.4-23.2 | Dandy is the baton. |
| 23.4-27.4 | It holds where the project is, what changed, and what's next. |
| 27.6-29.8 | So the next runner starts at speed. |
| 29.9-31.8 | Not from the blocks. |
| 34.0-38.8 | Stop restarting. Start handing off. |

## Messaging check

- Leads with the failure; Dandy is named at 21 s and described in one line of three plain things (where the project is, what changed, what's next).
- No "state layer", no traction or VC lines, no project-management comparison, no harness or framework, no promises, no long dashes.
- Purple only on the baton and the end card; gold only on the end card's trial line.
- No Dandy Man in scenes or on the end card (invariants 4 and 5).

## v1 build notes (Nov 8)

- Code in videos/07-relay/track/: relay_lib.py (stadium strips with parallax, jointed runner silhouette with rim light and wet reflection, overhead oval, baton), render_relay.py (timeline, board, captions, end card), sfx_relay.py (sound bed). Run `python3 videos/07-relay/track/render_relay.py` (add `--preview` for 10 fps, `--stills` for two frames per shot).
- Shots: s1a feet 0-1.3, s1b hand closes on air 1.3-2.15, s1c wide miss 2.15-3.0, s2a/b/c three legs 3.0-10.0, s3 overhead 10-20, s4a baton appears 20-22, s4b and s4c clean hand-offs 22-32, s5a anchor pulls away 32-35.5, s5b finish 35.5-40, end 40-44.5.
- Board: LEG n OF 4 in red, white clock. In beat 2 the split runs, freezes red at each miss (10.41, 10.32, 10.19) and the leg never moves. From beat 4 a race clock runs; LEG advances at each clean hand-off; it stops at FINISH 37.84.
- Finish pass from 04 (render/finish.py): spring zoom-out on the overhead, drifting camera, bloom on the floodlights and baton, grain, a little shake on the feet and the stumble.
- Sound bed: pistol at 0 and at the baton, wet footfalls following each runner's cadence, breathing after each miss, scuffs on stumbles, a slap on each clean hand-off, a soft tone as the baton lights, a beep as each clock stops, and a low crowd murmur that swells at the finish. No narration; captions are burned in at the times in the table above.
- Purple appears only on the baton (and its glow) and on the end card. Red is used only for the board's leg label, frozen misses and the overhead's failed hand-off rings.
- v2 (Nov 8): renumbered from 06 to 07 (06 is The New Hire); the fist is drawn over the middle of the baton so the hand holds it, with both ends showing; the sound bed is about 3 dB quieter. Output: videos/07-relay/out/07-relay-vertical.mp4.
- v3 (Nov 8): cut to Charlie's narration (voiceover/charlie-raw.wav, his Descript export). Lead-in trimmed 3.2 s so the first line lands at 4.0 s; captions follow his actual line times (voiceover/relay.json); the pull-away is 2.7 s so "Start handing off" ends as the baton crosses at 36.2 s; the board's race clock is scaled to stop on 37.84 there. Total 43.7 s. Mix: voice about -16 to -20 dB RMS, the bed ducked about 10 dB under it, -18.7 LUFS overall. The export seems to carry a very quiet music track (a 100 BPM pulse about 20 dB under the voice, running 10 s past the last line); it is nearly inaudible under the bed.
- v4 (Nov 8): footsteps 30% quieter (FOOTFALL_GAIN 0.7 in sfx_relay.py); audio rebuilt with `--audio-only`, picture unchanged.
