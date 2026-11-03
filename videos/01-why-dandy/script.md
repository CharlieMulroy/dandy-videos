# 01 Why Dandy Exists

**Takeaway:** Agents forget everything between sessions; Dandy is the state layer that remembers, so plan and code stay one thing.

**Format:** fully animated, Charlie voiceover as Dandy Man. Dandy Man is the teacher: he stands at a blackboard
in front of a small class (the Team figures) and teaches the builder's story. Everything drawn "on the
blackboard" uses chalk-style versions of the motifs (graph, session reset, context rot).

**Target length:** 75 s (about 170 narrated words). Status: draft v1, not yet reviewed by Nick.

| # | Sec | Visual | On-screen text | Narration (Dandy Man) |
| --- | --- | --- | --- | --- |
| 1 | 0-6 | Builder at a desk, late. Agent (the Employee, cape on) beside him, graph growing on screen. No Dandy Man yet. | "11:48 PM" | A builder, his agent, and a very good night. Schema designed. Decisions made. Half the thing built. |
| 2 | 6-13 | Session Reset: black wipe. Morning. Employee reappears with an empty thought bubble. Builder's shoulders drop. | "9:02 AM" | Morning. New session. And the agent remembers none of it. Not the schema. Not the decisions. Not what was half built. |
| 3 | 13-19 | Cut to classroom: Dandy Man walks in from the left, blackboard behind him, three figures seated. He taps the board; a chalk graph appears. | "Lesson one: context rot" | Good morning, class. Lesson one. This is context rot, and every one of you has felt it. |
| 4 | 19-30 | Blackboard: "notes", "markdown files", "planning tools" written and crossed out one by one. Two chalk columns, Plan and Code, drift apart; an edge snaps red. | "Plan ≠ Code" | The builder tried notes. Then markdown files. Then planning tools. They all rot, because a human has to keep them current, and humans have other jobs. So the plan says one thing. The code says another. |
| 5 | 30-38 | Dandy Man turns to the class. Hat tip. Behind him the two columns slide together into one chalk graph. | "One source of truth" | So he built the thing that does not rot. A state layer: one place that knows what your software is, kept current by the agents themselves. That place is me. |
| 6 | 38-47 | Blackboard slide 1: the graph. Nodes labeled Ingest, Clean, Report; typed contracts shown as chips on the edges. | "Typed contracts" | Here is how it works. Your product is a graph of projects. Every project says what it takes in and what it puts out. |
| 7 | 47-56 | Blackboard slide 2: an agent figure reads the graph, then writes back. A small audit log fills in. | "Agents read first, write back" | Every agent reads the graph before it starts, and writes back what it changed. Nothing happens in the dark. |
| 8 | 56-65 | Blackboard slide 3: Dandy Man edits the first node; the change ripples down every edge, each node lighting up in turn. The gold node is the one that changed. | "Changes flow downstream" | Change something upstream, and everything downstream knows. No re-explaining. No drift. |
| 9 | 65-72 | Back to the builder's desk, morning. Employee reads the graph, nods, gets to work. Dandy Man watches from the doorway. | "Live. In production." | We build Dandy with Dandy. It is live, in production, with paying customers. It is early, and we like it that way. |
| 10 | 72-75 | End card. | dandylabs.dev / 14-day free trial | Class dismissed. |

## Narration, read straight through

A builder, his agent, and a very good night. Schema designed. Decisions made. Half the thing built.

Morning. New session. And the agent remembers none of it. Not the schema. Not the decisions. Not what was half built.

Good morning, class. Lesson one. This is context rot, and every one of you has felt it.

The builder tried notes. Then markdown files. Then planning tools. They all rot, because a human has to keep them current, and humans have other jobs. So the plan says one thing. The code says another.

So he built the thing that does not rot. A state layer: one place that knows what your software is, kept current by the agents themselves. That place is me.

Here is how it works. Your product is a graph of projects. Every project says what it takes in and what it puts out.

Every agent reads the graph before it starts, and writes back what it changed. Nothing happens in the dark.

Change something upstream, and everything downstream knows. No re-explaining. No drift.

We build Dandy with Dandy. It is live, in production, with paying customers. It is early, and we like it that way.

Class dismissed.

## Notes

- Beats 6 to 8 are the reusable "how it works" cut; keep them self-contained so they can post alone.
- New assets this script needs: blackboard motif, chalk variants of the graph, Dandy Man walk cycle and hat tip,
  Employee with cape, seated Team figures, builder-at-desk scene. Scene Spec lists them.
- Messaging check: leads with the problem; "state layer" named; no Jira, harness or framework; no promises; no long dashes.
- Open question: beat 5 "That place is me" makes Dandy Man literally the product. If that feels too cute for
  enterprise viewers, swap for "That place is Dandy."
