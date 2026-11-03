# 02 Maya: Three Unfinished Projects

**Takeaway:** Non-coders building with agents don't fail for lack of skill; they fail because every new session starts from zero. Give the agent the state and the projects get finished.

**Format:** fully animated, Charlie voiceover as a plain narrator (not Dandy Man: this is a real-life
use case video, and Dandy Man only appears in educational videos). Maya is a new cast figure. Show more
than tell: the narration is short and the screen carries the story. Her three projects are small graph
panels whose fill state is the plot (half-drawn, broken, redrawn, complete).

**Target length:** 45 s (about 80 narrated words). Status: draft v2 (Dandy Man removed, narration cut), awaiting Charlie's review.

| # | Sec | Visual | On-screen text | Narration |
| --- | --- | --- | --- | --- |
| 1 | 0-5 | Maya at her desk, agent (Employee) beside her. Three small project panels pop in above them, one at a time: Budget tracker, Workout log, Side business site. Each has one or two nodes filled, the rest dashed outlines. | "Maya. Not a coder." | Maya isn't a coder. She builds things with Claude Code anyway. |
| 2 | 5-9 | Panels hold. A small grey tick lands under each: "started". The tally counts up to 3, then "finished" stays at 0. | "Started 3. Finished 0." | All started. None finished. |
| 3 | 9-14 | Session Reset wipe. Morning clock. Agent's thought bubble empties. Panel 1 (Budget tracker) greys out; agent speech bubble: "What budget tracker?" | "What budget tracker?" | Every new session, the agent starts from nothing. |
| 4 | 14-19 | Session Reset wipe again. Panel 2 (Workout log) greys out and redraws itself from node one; the old nodes fade as the new ones appear. Context Rot red on the dropped edge. | "rebuilt from scratch" | (no narration; let the redraw play) |
| 5 | 19-24 | Session Reset wipe again. Panel 3 (Side business site). Maya's thought bubble fills with tiny text lines, she slumps, the bubble drifts off. Agent bubble blank. | "re-explaining it, again" | The projects weren't dead. The agent just couldn't see them. |
| 6 | 24-33 | Maya sits up. The three panels slide down into one clean graph in the center with typed labels on the edges; a single gold node, "Dandy", at the root. The agent's eyes go to the graph; a short arrow draws from the graph to the agent (read), then back (write). No wipe; same session. | "what exists, what's connected, what's next" / "reads first, writes back" | So she put them in Dandy. Now the agent reads the state before it starts, and writes back what it changed. |
| 7 | 33-40 | Caption "3 weeks later" over a quick morning wipe. Same desk, same pose as scene 1. The three panels return fully drawn; a gold tick lands on each in turn. Tally: "Finished 3." | "3 weeks later" / "Finished 3." | Three weeks later. Same Maya. Same agent. |
| 8 | 40-45 | End card. | dandylabs.dev / 14-day free trial | Finish what you started. |

## Narration, read straight through

Maya isn't a coder. She builds things with Claude Code anyway.

All started. None finished.

Every new session, the agent starts from nothing.

The projects weren't dead. The agent just couldn't see them.

So she put them in Dandy. Now the agent reads the state before it starts, and writes back what it changed.

Three weeks later. Same Maya. Same agent.

Finish what you started.

## Notes

- Expansion of the earlier silent Maya concept: that version showed the stall and the "weeks later" jump.
  This one gives each project its own failure (forgot it, rebuilt it, made her re-explain it) so viewers
  recognise their own, and mirrors scene 1 in scene 7 so the only variable that changed is Dandy.
- Scene 4 has no narration on purpose. The redraw is the joke; a line over it would step on it.
- Charlie speaks as a plain narrator here. Dandy Man is reserved for educational videos (rule recorded in
  the Cast and Assets node in Dandy, Nov 2).
- "Claude Code" is named once, by decision (Nov 2): it is what the audience uses.
- The three projects are deliberately ordinary, by decision (Nov 2).
- New assets: Maya figure (idle, slumped, sitting-up), the project panel element in four states (sparse,
  greyed, redrawing, complete) with a tick, and the tally caption. Scene Spec lists them.
- Messaging check: leads with the problem; "state" named plainly; no Jira, harness or framework; no proof
  or traction lines (individual-builder video); no long dashes; max 12 words on screen per frame.
- Closing line "Finish what you started." is this video's own; 01 keeps "Pick up where you left off."

## v3: the room (Nov 2, after the house-style cut)

Direction change: use-case videos get their own look. This one is a cozy room at night, drawn in code
(videos/02-maya/lofi/gen_room.py, rendered by videos/02-maya/lofi/render_lofi.py). No Dandy Man; soft end card.
The agent is the chat window on Maya's monitor. The bulletin board carries the three projects as cards with
progress bars and a pink sticky note per problem.

| # | Sec | Shot | On-screen text | Narration |
| --- | --- | --- | --- | --- |
| 1 | 0-6 | Wide: Maya typing at night, rain, chat on screen (she asks for a budget tracker, the agent builds it). Slow push in. | "Maya. Not a coder." | Maya isn't a coder. She builds things with Claude Code anyway. |
| 2 | 6-13 | Board close-up: three cards pin on (Budget tracker 60%, Workout log 45%, Side business site 30%), then three notes: "where was I?", "rebuilt it. again.", "explained it 4 times". | "Started 3. Finished 0." | Three projects. None finished. |
| 3 | 13-20 | Screen close-up: Maya types "add the chart to the budget tracker"; agent: "Which budget tracker? I have no context on that." Maya slumps onto the desk. | (chat only) | (none) |
| 4 | 20-29 | Screen: a Dandy panel slides in (Budget tracker: Income done, Spend done, Chart next); agent reads it and starts at Chart; Maya sits up, then types again. | (chat only) | Then she put them in Dandy. Now every session starts from what's actually true. |
| 5 | 29-35 | Wide time-lapse: the window cycles night, day, night; rain stops; Maya keeps working. | "3 weeks later" | Three weeks later. |
| 6 | 35-42 | Board close-up: notes peel off, progress bars fill to 100%, a DONE stamp lands on each card. | "Finished 3." | Same Maya. Same agent. |
| 7 | 42-46.5 | Soft end card: the room dims and blurs; hat, Dandy, dandylabs.dev, 14-day free trial. | "Finish what you started." | Finish what you started. |

Narration, straight through (about 45 words): Maya isn't a coder. She builds things with Claude Code anyway. / Three projects. None finished. / Then she put them in Dandy. Now every session starts from what's actually true. / Three weeks later. Same Maya. Same agent. / Finish what you started.
