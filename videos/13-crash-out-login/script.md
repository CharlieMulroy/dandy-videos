# 13 Crash-Out: "We already have a login page"

**Takeaway:** Your agent rebuilds things because it can't see what's already built. Dandy shows it.

**Kind:** crash-out (proposed fifth kind, a skit that plays like a tongue-in-cheek infomercial). Opens mid-meltdown
with no title and no setup; Dandy Man enters only after the problem has landed, delivers the fix in a few lines, and
the end card follows. Built to be a repeatable series: same structure, a different meltdown each time. The rule for
this kind is not in Dandy yet; it waits on Charlie's go-ahead.

**Look:** the night room from video 02 (a desk, a monitor, a lamp), with a new builder at the desk, not Maya. The
room is warm and dim until Dandy Man arrives; he brings the purple with him, as light spilling in from the side.
The builder's lines are big on-screen text that shakes, not narration. Hard cuts and fast timing in the first five
seconds; everything slows down the moment Dandy Man speaks.

**Audience:** anyone who has built with an AI coding tool and been through this exact moment.

**Target length:** 25.0 s, fitted to Charlie's Nov 21 read (all Dandy Man, timing in `voiceover/stage.json`). Status: draft v1, Nov 14;
first render built Nov 14 with placeholder timing (`room/render_crash.py`). Timing follows Charlie's read once recorded.

| # | Sec | Visual | On-screen text | Narration (Dandy Man, in Charlie's voice) |
| --- | --- | --- | --- | --- |
| 1 | 0-1.5 | Cold open, already mid-meltdown: the builder at the desk at night, hands in their hair. On the monitor the agent's message sits there, cheerful. | Agent: "Done! I built you a login page." | (none) |
| 2 | 1.5-4 | Smash cut closer. The builder's line slams on in shaking type. Behind it, the file list on the monitor grows: login, login_new, login_final. | "WE ALREADY HAVE A LOGIN PAGE" | (none) |
| 3 | 4-5.5 | The builder's head drops onto the keyboard with a thud. Gibberish types itself on the monitor. Silence. | "that's the third one." (small, flat) | (none) |
| 4 | 5.5-7.5 | A polite cough. Purple light spills in from the right. Dandy Man steps into frame and tips his hat. The builder lifts their head an inch. | | Rough night? |
| 5 | 7.5-12 | Dandy Man gestures at the monitor. The agent's light drifts around the room, looking at nothing in particular. | (captions only) | Your agent isn't careless. It just can't see what's already built. |
| 6 | 12-17 | He taps the cane once. A map of the project blooms over the wall: four pieces (Login, Calendar, Bookings, Payments), three marked done, Payments marked next. The agent's light reads it, skips Login, and settles on Payments, which turns to building. | Agent: "Login's done. Building payments." | Dandy shows it: every piece of your project, and where it stands, before it writes a line. |
| 7 | 17-18.5 | The builder sits up. Dandy Man tips his hat. | | There. Much better. |
| 8 | 18.5-21 | End card with Dandy Man: hat, wordmark, dandylabs.dev, 14-day free trial. | | (nothing) |

## Narration, read straight through

Rough night?

Your agent isn't careless.
It just can't see what's already built.

Dandy shows it: every piece of your project, and where it stands, before it writes a line.

There. Much better.

## Accuracy notes

- Agents rebuilding existing work is a common complaint with AI coding tools; a fresh session only knows what it
  has been shown or goes looking for.
- "Dandy shows it ... before it writes a line": the agent reads the project's pieces and their status from Dandy
  at the start of the work. Same claim as videos 09 to 11.
- No claim about tokens, speed or cost.

## Messaging check

- Problem first, and the whole first quarter is nothing but the problem.
- Dandy Man sells, but with a wink: he is calm, brief and a little dry, never a hype man.
- Does not call Dandy a project management tool, a harness or a framework; no "state layer"; no long dashes.

## Open questions for Charlie

1. The builder's lines are on-screen text, so the only voice is Dandy Man's (yours). Want to voice the meltdown
   too? A real shout in the first second would hit harder than text.
2. "Rough night?" as his opening line, or something more infomercial ("There's got to be a better way")?
3. This adds a fifth kind of video, with the rule that Dandy Man enters only after the problem lands. OK to add
   that to the rules in Dandy?
4. Other meltdowns ready to script in the same format: "I told you this yesterday", the old project nobody can
   read, and two agents overwriting each other.

## Changes made in the first render

- The map has four pieces, not five, and the two key phrases are gone: the on-screen word limit is 12 per scene, and
  the captions already carry those lines.
- The agent's second message reads "Login's done. Building payments." (one word shorter, same reason).
- No lamp on this desk, so the thud lands on the keyboard and types gibberish instead.
- Dandy Man enters from the right. The style contract says left, but the builder sits on the left facing the monitor.
