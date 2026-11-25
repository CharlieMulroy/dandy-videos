# 16 One Small Change

**Takeaway:** A small change in one part of a project quietly breaks the parts that depend on it. In Dandy, every
piece says what it takes in and puts out, so a change travels down the map: what depends on it is updated or
flagged, and the agent is told what it touched. This is propagation.

**Kind:** informational, about Dandy, narrated plainly with no Dandy Man in the scenes (Charlie asked for this one to
feel unique like video 14, not like the house videos). Dandy Man signs off on the end card only (invariant 4).

**Look (new, proposed): City at Night.** It opens on a project map (cards joined by lines) that rises into a small
city seen from above at night, so the viewer sees that the city is their project. Each piece is a building with its
name on a card-style sign; pieces that depend on each other are joined by power lines, and the column each one
reads hangs as a sign on its line. At the end the city flattens back into the map, now purple: Dandy's map. One camera glides over the city for the
whole film and never cuts. The night is navy and amber; purple appears only once Dandy does. Renderer:
videos/16-one-small-change/city/render_city.py (uses render/stage.py for captions, sound, finish and the end card).
The earlier Void Stage draft (render_change.py) is kept for reference.

**First frame (thumbnail):** the flat project map with "One small change" in large type, held still for half a
second; also exported as out/16-thumbnail.png.

**Length:** about 50 s at placeholder timing (113 narrated words; Charlie's read usually comes in shorter).
Status: draft v2 script (adds Charlie's pick, "Think of your project as a city."), city look v2 rendered Nov 24.

| # | Sec | Visual | Narration |
| --- | --- | --- | --- |
| 0 | 0-2.6 | A project map from above: cards joined by lines, Bookings wired to Reminders, Payments and Reports. Title "One small change". | Think of your project as a city. |
| 1 | 2.6-6.4 | The cards rise into buildings, windows light up, streets and streetlights appear, and the lines become power lines. Each name lifts onto a sign. | Every part is a building, wired to the parts it depends on. |
| 2 | 6.4-13 | The camera glides down to Bookings. A sign at its foot reads "date". The agent (a white light) lands on the roof, the sign flips to "start_time", and the light leaves. | You ask your agent for one small change. Rename a column. Done in ten seconds. |
| 3 | 13-22.8 | Pull back: the power lines to the three buildings, each carrying a "date" sign. One by one their windows go out, quietly. The signs are struck through. Then red beacons blink on their roofs. | What it didn't know: three other parts of your project were reading that column. Nothing errors. They just quietly go wrong, and you find out next week. |
| 4 | 22.8-25.6 | Rewind, like tape: bright bands roll up the frame, the lights come back on, Bookings' sign returns to "date". | That's what propagation fixes. |
| 5 | 25.6-35.4 | The power lines and signs turn Dandy purple, the line signs glow ("takes in"), then Bookings' sign ("puts out"). The agent renames the column again, and a purple pulse runs down each line, flipping each sign to "start_time" as it passes; every building it reaches keeps its lights. | In Dandy, every piece of your project says what it takes in and what it puts out. So when one piece changes, the change travels down the map. |
| 6 | 35.4-42.6 | A purple flag rises on each of the three roofs. Pulses run back up the lines to the agent, and a sign beside Bookings reads "3 touched". | Everything that depends on it gets updated or flagged, and your agent is told exactly what it just touched. |
| 7 | 42.6-47.4 | The flags come down. The rest of the city links up in purple, spreading out from Bookings, and the camera pulls up as the city flattens back into the map, now Dandy's. | One change. Nothing caught off guard. |
| 8 | 47.4-50.4 | End card with Dandy Man. | (nothing) |

## Narration, read straight through

Think of your project as a city.
Every part is a building, wired to the parts it depends on.

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
- "Think of your project as a city" is the only metaphor line; the opening and closing map ties the city to the map in Dandy. The word "propagation" is said once and shown once. Nothing about how it is implemented.
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
