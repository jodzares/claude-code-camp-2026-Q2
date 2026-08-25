# W1 — Prompt Builder Diagramming

## What this lesson was
Fact: no code, no module folder. Output = Lucidchart tab 03 + this note.
Tab 03 = tab 02 copied forward with the prompt builder added: its abstract
base class plus five backends, and one outbound edge (to_api_payload) into a
dotted API box that doesn't exist yet.

## Decisions on the canvas

### D1 — Copy the tab forward, don't redraw
Fact: duplicate the whole previous tab, then add. Each tab is a full snapshot
of the system, not a spotlight on the new piece.

### D2 — Abstract parent earns a box
Fact: abstract base is the parent for all providers. It declares the five
contract questions every provider must answer (each provider answers
differently). It earns a box even though it never runs alone, because it
states the contract the children satisfy.

### D3 — Only the boundary-crossing edge is drawn (MONEY SHOT)
Fact: the builder has five jobs. Only to_api_payload becomes an edge, because
it's the only one whose output leaves the builder and crosses to another box
(the API). The other four (to_messages, to_tools, headers, url) are internal
steps that build the payload, so they aren't drawn. Rule: draw an edge when
output crosses a boundary, not for internal work.

### D4 — API as a dotted box
Fact: the API is drawn as a dotted box because it doesn't exist in the code
yet — it's where the architecture is heading. Same "coming later" idea as tab
02's dangling dispatch edge, just different notation: a dangling edge marks a
missing connection, a dotted box marks a missing component.

### D5 — Check the code before drawing the arrow
Fact: before drawing the Context → PromptBuilder arrow, Andrew read the source
to confirm the builder holds a backend + context. Drawing forces a claim about
the code, so he checks it (same audit reflex as the Registry lesson).

## No box
Fact: the four internal methods, and the API's real HTTP call, aren't full
boxes. Delete-test: strip them and the architecture still reads. Only
contracts, components, and boundary-crossings earn ink.

## Spine
Fact: tab 03 copies 02 forward and adds the builder (holds backend + context),
an abstract parent with five vendor children, and one outbound edge to a
dotted, not-yet-built API — every choice settled by reading the code, not
guessing.