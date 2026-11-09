# 08 Context Windows

**Takeaway:** A context window is a desk, not a filing cabinet. Everything the AI can see has to be on it, it has a fixed size, and when it fills, the oldest pages slide off. A long chat gets worse because the desk is crowded; a fresh chat is a clean desk. Keep the record somewhere that doesn't slide off.

**Kind:** general-concept explainer (same category as 04). Instructional for 95 percent of its length. Dandy appears
only in the final spoken line, and there is a variant with no mention at all; the end card carries the brand either
way. No Dandy Man. Own look; shares the palette family, copy rules and the end card without Dandy Man.

**Look:** a desk seen straight down, drawn in code. Cool slate background, a warm wood desk with a crisp edge, and
cards that land on it: blue for what you say, grey for what the model says, cream for files you paste. The desk is
the window. Flat vector shapes, soft shadows, calm motion: cards slide in, settle, stack, and when the desk is full
the oldest slide off the bottom edge and fall into the dark. Beside the desk sits a closed notebook; it stays
neutral until the last line, when it is the only purple in the film (or stays neutral in the no-mention variant).
Type is clean and large, one short line at a time. Nothing hot or dramatic; this one teaches.

**Audience:** individual builders, many of them non-technical. One term is introduced (token) and defined in
passing. No mechanism beyond what the desk shows.

**Target length:** about 55 s (about 135 narrated words). Status: draft v1, Nov 8, for Charlie's review. No render
until the words are approved.

| # | Sec | Visual | On-screen text | Narration (plain, calm, a little dry) |
| --- | --- | --- | --- | --- |
| 1 | 0-5 | Cold open on an empty desk from above, one lamp of warm light. A label pins to its corner. | "the context window" | Every AI chat has a desk. It's called the context window. |
| 2 | 5-13 | Cards land one by one: a blue card (you), a grey one (the model), a cream sheet (a pasted file), more of each, in a tidy grid. A thin ruler along the edge ticks up as they land, labelled in tokens. | "everything you say" / "everything it says" / "every file you paste" / "measured in tokens" | Everything you say, everything it says, every file you paste: it all lands on the desk, measured in tokens, rough chunks of words. And that desk is all the model can see. |
| 3 | 13-24 | The desk is full. New cards keep landing at the top, and the bottom row slides off the edge, tips, and falls into the dark. One falling card is tagged "the decision from an hour ago", another "the file it read this morning". The model's new reply lands, oblivious. | "fixed size" / "oldest pages slide off" | The desk has a fixed size. When it fills, the oldest pages slide off. The decision from an hour ago. The file it read this morning. Gone, without a word. |
| 4 | 24-34 | Pull back a little: the desk is covered, cards overlapping, half of them dimmed. Two cards are pulled forward side by side: "use Postgres" and "switched to SQLite", one old and faded, one new; the model's reply quotes the faded one. | "crowded desk, sloppy work" | Even before it's full, a crowded desk makes it sloppy. It mixes up what's current and what's old. That's why a long chat gets dumber. |
| 5 | 34-44 | A clean sweep: the cards slide away and the desk is bare and bright again. One blue card lands squarely in the middle: a short brief. | "a fresh chat is a clean desk" / "sharp. and blank." | So a fresh chat isn't a failure. It's a clean desk. Sharp, and blank. Whatever it needs to know, you put back on the desk. |
| 6 | 44-50 | The notebook beside the desk opens: a few neat lines. Cards on the desk come and go; the notebook stays. In the Dandy variant it turns purple here and its light settles behind the end card. | "the desk is for working" / "keep the record off the desk" | The desk is for working. Keep the record somewhere that doesn't slide off. |
| 7 | 50-54 | End card without Dandy Man: hat, wordmark, dandylabs.dev, 14-day free trial. | | (variant A, no mention) nothing. (variant B) That's what Dandy is for. |

## Narration, read straight through

Every AI chat has a desk.
It's called the context window.

Everything you say, everything it says, every file you paste:
it all lands on the desk, measured in tokens, rough chunks of words.
And that desk is all the model can see.

The desk has a fixed size.
When it fills, the oldest pages slide off.
The decision from an hour ago.
The file it read this morning.
Gone, without a word.

Even before it's full, a crowded desk makes it sloppy.
It mixes up what's current and what's old.
That's why a long chat gets dumber.

So a fresh chat isn't a failure.
It's a clean desk.
Sharp, and blank.
Whatever it needs to know, you put back on the desk.

The desk is for working.
Keep the record somewhere that doesn't slide off.

(Variant B only:) That's what Dandy is for.

## Accuracy notes

- "Measured in tokens, roughly chunks of words" is the honest short version; a token is a piece of text about three quarters of a word on average.
- "The oldest pages slide off" is how most chat tools handle a full window (they drop or summarise the oldest turns). Some tools summarise instead of dropping; "usually without a word" covers both, since neither is announced clearly to the user.
- "A crowded desk makes it sloppy" is the well-documented decline in quality as the window fills (long-context degradation, the "lost in the middle" effect). The script describes the symptom, not the mechanism.
- A fresh chat really is blank: nothing carries over unless the tool has a memory feature or you paste it back. The script says "you have to put back on the desk", which is true for every tool.

## Messaging check

- Teaches first; the product, if named at all, is one line after the lesson is complete.
- No "state layer", no harness or framework, no comparisons to other tools, no promises, no long dashes.
- Plain, calm voice; short lines; one defined term.
- No Dandy Man in scenes or on the end card. Purple only on the notebook in variant B and on the end card.

## Open questions for Charlie

1. Variant A (no Dandy in the narration, the end card alone carries the brand) or variant B (one closing line, "That's what Dandy is for")? I'd ship A: the end card already says it, and the video travels further as pure teaching.
2. The desk look is my proposal for the style. The alternative is a chalk-on-slate diagram look, more classroom than desk. Happy to sketch both as stills before building.
3. Length: 135 words is about 55 s at your pace. If you want it under 45 s, beat 3 can drop the two example lines (the decision, the file) and beat 5 can drop "Sharp, and blank."
