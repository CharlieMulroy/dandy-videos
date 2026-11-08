# 06 The New Hire

**Takeaway:** An AI agent is the best employee you have ever hired, and it forgets everything about the job every single morning. Dandy is what it reads first. (Dandy: the last two beats only.)

**Kind:** metaphor video (third kind). No Dandy Man. Own look: a painted office, warm morning light through the
blinds, one desk, one whiteboard, the only purple is the Dandy ledger on the desk and the light it throws in the
turn. Comic, not dark. Grows out of the "Employee with a cape" beat from the 00 render test and video 01: same idea,
told as a full story about one hire. Video 04 explains context rot and 05 shows the body count; this one plays it for
laughs in a workplace everyone recognises.

**Target length:** about 52 s (about 120 narrated words). Status: draft v1, Nov 8. Cast built the same way as the
graveyard rider and reaper: painted stills generated in ChatGPT on a transparent background, cut into parts and
rigged in code. Prompts for the stills are at the bottom of this file.

| # | Sec | Visual | On-screen text | Narration (plain, dry, straight-faced) |
| --- | --- | --- | --- | --- |
| 1 | 0-5 | Cold open, no logo. A quiet painted office at 9:00, dust in the light. A superhero landing by the desk: the new hire drops in from above, one knee down, cape settling. Button-down shirt and tie under the cape, lanyard, coffee in hand, not a drop spilled. | "DAY 1" | Your company just hired the best employee in the world. |
| 2 | 5-13 | He can do anything. Fast cuts, all in the one office: the whiteboard fills itself with an architecture diagram as he points at it; three monitors light up with code at once; he carries a server rack under one arm; the keyboard smokes. A manager's hand sets down a stack of docs, he fans through it in a second and nods. | "backend before lunch" / "frontend after" / "read every doc you own" | He can do anything. Backend before lunch. Frontend after. Hand him every document you own and he has read it before you sit down. |
| 3 | 13-22 | DAY 2. The same landing, the same coffee. He stands, looks at the full whiteboard, then at the manager, and a question mark forms where a thought bubble would be. A chat window at the lower right: "Morning! So. What are we building?" The manager's hand, off-screen, points at the whiteboard. | "DAY 2" / "Morning! So. What are we building?" | There is one problem. Every morning he forgets. All of it. What the project is. What he built. What he decided. What is left. |
| 4 | 22-33 | The weeks. DAY 3, DAY 5, DAY 9 on hard cuts. Sticky notes multiply over the monitor bezels, then the wall, then the whiteboard. The manager's hand re-explains with a marker. He rebuilds the login page: v1, v2 in a different colour, v3 in a third, three windows side by side, none matching. A sticky note reads "DO NOT rebuild login" and he is reading it while rebuilding login. The manager's coffee cup count on the desk goes from one to four. | "DAY 3" / "DAY 5" / "DAY 9" / "login v1 · v2 · v3" | So you explain it again. He rebuilds the login page, a little differently. You leave notes. He does not find them, or they are wrong by Tuesday, because you wrote them and you were busy. By week two you spend more time briefing him than he spends building. |
| 5 | 33-44 | The turn. DAY 10. The desk is cleared except for one thing: a slim purple ledger, the only purple in the film, glowing faintly. He lands, sees it, and opens it before he says a word. On its pages, a graph of the product: what it is, what is done, what is next, what he decided and why, in his own handwriting, dated yesterday. The sticky notes peel off the walls and drift away. He nods once, cracks his knuckles, and sits. | "reads this first. every morning." / "written by him. yesterday." | Unless the first thing he does every morning is read the truth about the project. Not your notes. His. Written down as he worked, kept current by him, read before he touches anything. |
| 6 | 44-52 | Resolution into the end card. He is working, three monitors, the whiteboard diagram growing where it left off. The manager's hand lifts a single coffee cup and leaves the frame. The purple light from the ledger spreads and settles behind the end card: wordmark, dandylabs.dev, 14-day free trial. | "picks up where he left off" / "Same superpowers. Now he remembers." | Same superpowers. Now he remembers. Dandy is what your agent reads first. |

## Narration, read straight through

Your company just hired the best employee in the world.

He can do anything. Backend before lunch. Frontend after. Hand him every document you own and he has read it before you sit down.

There is one problem. Every morning he forgets. All of it. What the project is. What he built. What he decided. What is left.

So you explain it again. He rebuilds the login page, a little differently. You leave notes. He does not find them, or they are wrong by Tuesday, because you wrote them and you were busy. By week two you spend more time briefing him than he spends building.

Unless the first thing he does every morning is read the truth about the project. Not your notes. His. Written down as he worked, kept current by him, read before he touches anything.

Same superpowers. Now he remembers. Dandy is what your agent reads first.

## Sticky notes and on-screen gags (the bench; use five or six)

- "DO NOT rebuild login" (he is reading it while rebuilding login)
- "the project is a BUDGET APP" underlined three times
- "ask Priya before touching the schema" / below it, in his hand: "who is Priya"
- "we use Postgres" / "we use Postgres!!" / "POSTGRES"
- "yesterday you said no to this"
- "read this first" (buried under four other notes)
- on the whiteboard, the same box drawn three times in three colours, labelled "auth", "login", "sign in"

## Messaging check

- Leads with the problem; the pitch is two sentences at the end.
- Approved framing used: planning tools and notes failed because a human kept them current; here the agent keeps the record current itself ("Not your notes. His.").
- Says what Dandy is in one plain phrase, "what your agent reads first"; no "state layer" lecture (that is video 03).
- No Jira or project-management-tool comparison, no harness or framework, no promises, no long dashes.
- No Dandy Man anywhere, including the end card (metaphor kind).
- The word "memory" is deliberately avoided in the narration: the product is a record he reads, not a brain upgrade.

## Open questions for Charlie

1. Does the hire need a name? The script works without one ("he"); a name on the lanyard would be a gag on its own.
2. Is the manager a hand and a coffee cup only, or a second painted figure? A hand keeps the cast to one puppet and the viewer in the manager's seat.
3. Final line: "Dandy is what your agent reads first." Alternatives: "Give your agent somewhere to write it down." / "Hire the superpowers. Keep the context."

## Painted stills: prompts for ChatGPT

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
