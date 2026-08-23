# W1 — The Registry Diagramming

## What this lesson was
Fact: no code. Output = a Lucidchart diagram (Registry added onto the
existing canvas) + this note. The diagramming pass turned into a code audit.

## Decisions on the canvas

### D1 — Tool's edge moves off Context onto Registry
Fact: Tool used to point at Context (ctx.register_tool). Now it points at
Registry (register). One relationship = one edge; registry.tool is the
only door, and it calls ctx.register_tool internally.

### D2 — The audit (MONEY SHOT)
Fact: Andrew nearly deleted tools/register_tool from Context as dead code,
stopped, investigated, found them load-bearing — dispatch reads them.
The defect was found by DRAWING, not by building. Third pass, never noticed.

### D3 — dispatch drawn dangling
Fact: dispatch has no caller yet (no agent file). Drawn as an outbound edge
to nothing = a socket, marking a connection the architecture will need next.

### D4 — canvas mirrors the code, not the intent
Fact: tools[] stays on Context because that's what the code says. Andrew
leaves it in place; the ownership fix is a Week 2 job. A diagram that drifts
from the code stops being auditable.

### D5 — the defect goes in a floating note
Fact: not a box, not an edge — a sticky attached to nothing. Boxes/edges say
what the system IS; annotations say what you KNOW about it. Same note mirrored
into README Considerations so it survives outside Lucidchart.

## No box
Fact: UnknownToolError gets no box. Delete test — remove it, architecture
still stands (dispatch just fails rudely). Same reason example.rb is off-canvas.

## Spine
Fact: Registry joins as one box, inbound "register" from Tool, dangling
"dispatch" out, and drawing it exposed that Context still owns the tool table
— recorded as a note, not corrected on the canvas.