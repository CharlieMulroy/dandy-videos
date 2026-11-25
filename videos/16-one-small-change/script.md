# 16 One Small Change

**Takeaway:** A small change in one part of a project quietly breaks the parts that depend on it. In Dandy, every
piece says what it takes in and puts out, so a change travels down the map: what depends on it is updated or
flagged, and the agent is told what it touched. This is propagation.

**Kind:** informational, about Dandy, narrated plainly with no Dandy Man in the scenes (Charlie asked for this one to
feel unique like video 14, not like the house videos). Dandy Man signs off on the end card only (invariant 4).

**Look (new, proposed): City at Night.** The project is a small city seen from above at night; each piece is a
building, and pieces that depend on each other are joined by power lines. One camera glides over the city for the
whole film and never cuts. The night is navy and amber; purple appears only once Dandy does. Renderer:
videos/16-one-small-change/city/render_city.py (uses render/stage.py for captions, sound, finish and the end card).
The earlier Void Stage draft (render_change.py) is kept for reference.

**First frame (thumbnail):** the city from high above with "One small change" in large type, held still for half
a second; also exported as out/16-thumbnail.png.

**Length:** about 44 s at placeholder timing (98 narrated words; Charlie's read usually comes in shorter).
Status: draft v1 script, second look (city) rendered Nov 24.

| # | Sec | Visual | Narration |
| --- | --- | --- | --- |
| 0 | 0-2.8 | High over the city at night, title "One small change". The camera starts to sink. | You ask your agent for one small change. |
| 1 | 2.8-7.6 | The camera glides down to one building, Bookings, with a sign below it: "date". The agent (a white light) lands on the roof, the sign flips to "start_time", and the light leaves. | Rename a column. Done in ten seconds. |
| 2 | 7.6-17.4 | Pull back: grey power lines run from Bookings to three buildings across town, each with a "date" sign. One by one their windows go out, quietly. The signs are struck through. Then red beacons blink on their roofs. | What it didn't know: three other parts of your project were reading that column. Nothing errors. They just quietly go wrong, and you find out next week. |
| 3 | 17.4-20.2 | Rewind, like tape: bright bands roll up the frame, the lights come back on, Bookings' sign returns to "date". | That's what propagation fixes. |
| 4 | 20.2-30 | The power lines turn Dandy purple, the three signs below glow ("takes in"), then Bookings' sign ("puts out"). The camera eases in, the agent renames the column again, and a purple pulse runs down each line; every building it reaches keeps its lights and its sign flips to "start_time". | In Dandy, every piece of your project says what it takes in and what it puts out. So when one piece changes, the change travels down the map. |
| 5 | 30-37.2 | A purple flag rises on each of the three roofs. Pulses run back up the lines to the agent, and a sign beside Bookings reads "3 touched". | Everything that depends on it gets updated or flagged, and your agent is told exactly what it just touched. |
| 6 | 37.2-41 | The flags come down. The camera pulls up high and the rest of the city links up in purple, spreading out from Bookings. | One change. Nothing caught off guard. |
| 7 | 41-44 | End card with Dandy Man. | (nothing) |

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
- No Dandy Man in the scenes; he appears on the end card, as invariant 4 requires for informational videos about Dandy.
- Red is only the breakage in beat 2 (beacons, struck signs). Dandy's flags in beat 5 are purple, so "flagged" does not read as "broken".

## Open questions for Charlie

1. "Column" and the tag names "date" and "start_time": right level for individual builders, or too technical?
2. Title card reads "One small change" while you say the first line over it. Want the word "Propagation" on the
   thumbnail instead?
3. No Dandy Man in the scenes. If you want him, he could walk into frame at the rewind.
