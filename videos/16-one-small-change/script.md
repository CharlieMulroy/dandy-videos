# 16 One Small Change

**Takeaway:** A small change in one part of a project quietly breaks the parts that depend on it. In Dandy, every
piece says what it takes in and puts out, so a change travels down the map: what depends on it is updated or
flagged, and the agent is told what it touched. This is propagation.

**Kind:** informational, about Dandy. Dandy Man presents. Stands alone; it expands the one line video 11 gives
this ("when one piece changes, Dandy flags everything it touches").

**Look:** Void Stage (render/stage.py), with a corner of the same made-up booking app: Bookings, and the three
pieces that read from it (Reminders, Payments, Reports).

**First frame (thumbnail):** a still title card, "One small change", with Dandy Man beneath it. Holds half a
second; also exported as out/16-thumbnail.png.

**Length:** about 44 s at placeholder timing (98 narrated words; Charlie's read usually comes in shorter).
Status: draft v1, Nov 24. Charlie picked the Dandy-specific version over a general-concept one and saw this
narration in chat before the first render.

| # | Sec | Visual | Key phrase | Narration |
| --- | --- | --- | --- | --- |
| 0 | 0-2.8 | Title card, still for the first half second: "One small change" with Dandy Man. | (title) | You ask your agent for one small change. |
| 1 | 2.8-7.6 | Bookings and the three pieces under it. A tag beside Bookings shows the column it puts out, "date". The agent's light lands on Bookings, the tag flips to "start_time", and the light leaves. | Done in ten seconds | Rename a column. Done in ten seconds. |
| 2 | 7.6-17.4 | A "date" tag appears under each of the three pieces: they were reading it. One by one the tags are struck through and the pieces dim and crack, with no alarm. Then all three glow red at once. | Nothing errors | What it didn't know: three other parts of your project were reading that column. Nothing errors. They just quietly go wrong, and you find out next week. |
| 3 | 17.4-20.2 | Rewind: a sweep of light runs back across the map, the cracks close and the tag returns to "date". | Propagation | That's what propagation fixes. |
| 4 | 20.2-30 | The three "takes in" tags light up, then the "puts out" tag. The light returns and renames the column again. This time a pulse runs down each connection and each tag below flips to "start_time" as it arrives. | The change travels | In Dandy, every piece of your project says what it takes in and what it puts out. So when one piece changes, the change travels down the map. |
| 5 | 30-37.2 | A flag pops on each of the three pieces. A pulse runs back up each connection to the agent's light, and a tag beside it reads "3 touched". | Nothing missed | Everything that depends on it gets updated or flagged, and your agent is told exactly what it just touched. |
| 6 | 37.2-41 | The flags clear one by one. Dandy Man tips his hat. | Nothing caught off guard | One change. Nothing caught off guard. |
| 7 | 41-44 | End card with Dandy Man. | | (nothing) |

## Narration, read straight through

You ask your agent for one small change.

Rename a column. Done in ten seconds.

What it didn't know: three other parts of your project were reading that column.
Nothing errors. They just quietly go wrong, and you find out next week.

That's what propagation fixes.

In Dandy, every piece of your project says what it takes in and what it puts out.
So when one piece changes, the change travels down the map.

Everything that depends on it gets updated or flagged,
and your agent is told exactly what it just touched.

One change. Nothing caught off guard.

## Accuracy notes

- "Says what it takes in and what it puts out": every piece in Dandy declares its inputs and its output, and each
  connection carries that contract.
- "The change travels down the map": editing a piece's output flows along its connections to the pieces that
  depend on it. Shown as the three tags below flipping to the new name.
- "Updated or flagged": the downstream pieces' declared inputs are updated on the map, and a piece whose input
  changed needs its check again. The video does not claim Dandy rewrites the downstream code; the map and the
  agent know, and the agent does the fixing.
- "Your agent is told exactly what it just touched": the result of the edit lists what changed downstream.
- The word "propagation" is said once and shown once. Nothing about how it is implemented.
- This describes mechanics, so it should get a read from Nick before recording.
- No claim about tokens, speed or cost.

## Messaging check

- Opens on the problem, then the fix (fear, then relief). Does not call Dandy a project management tool, a
  harness or a framework; no "state layer"; no long dashes.
- Dandy Man appears because this is an informational video about Dandy; end card with him.
- Red is used for the silent breakage in beat 2. The flags in beat 5 are the same red badge as videos 11 and 12.

## Open questions for Charlie

1. "Column" and the tag names "date" and "start_time": right level for individual builders, or too technical?
2. The flags in beat 5 are red like the breakage in beat 2. Keep them matching 11 and 12, or give flags their
   own color here so "flagged" does not read as "broken"?
3. Title card reads "One small change" while you say the first line over it. Want the word "Propagation" on the
   thumbnail instead?
