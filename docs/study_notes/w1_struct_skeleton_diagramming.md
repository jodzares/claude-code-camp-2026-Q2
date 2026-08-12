# Struct Skeleton Diagramming — Study Note

Personal learning note. Not graded documentation. Grader: see `docs/journal/`.

Lesson output: an architecture diagram edit (no Ruby, no Python). Module 01
adds three shapes — Tool, Message, Context — on top of the 00_config diagram.

---

## Assembled picture

```
CONFIG HALF (from 00_config)                         STRUCT HALF (new in 01)

  Boukensha::Config ──resolve_dir──> ./boukensha        Boukensha::Tool
     loads settings.yml + .env         settings.yml         "data class"
                                       .env                     │
  Boukensha::Tasks::Base (Abstract)    prompts/…               ctx.register_tool
     │ extends                            │  tasks:             │
     v                                    ┆  player:            v
  Boukensha::Tasks::Player  ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┘             Boukensha::Context
                                                            messages[]
                                                            tools[]
                                                             ^
                                        Boukensha::Message   │
                                            "data class" ──ctx.add_message──┘

     └──────────── no edge between the halves (deliberate) ────────────┘
```

Two halves, no code path between them yet. The struct half floats on its own —
that gap is a fact about the code, not an omission.

---

## D1 — Carry the canvas forward, one page per lesson

Andrew copies the previous diagram forward onto a new page, then adds this
lesson's shapes on top. Each page is cumulative but self-contained — a full
standalone snapshot of the architecture at that lesson, not just the new bits.

## D2 — Draw only edges that exist in code today

The diagram draws an arrow only where the code actually connects two things
right now. Tool, Message, and Context are new this lesson but stay unconnected
to the config half, because no code links them yet — future connections are
left absent, not drawn as "coming soon".

## D3 — Data-vs-behaviour lives in the description text

Tool and Message are labelled "lightweight data class" — boxes that only hold
values. Context's description names its actions (`register_tool`,
`add_message`) and lists its fields, marking it as a thing that does work. The
data-vs-behaviour split is carried in the words, not in box shape or colour —
all three are the same rectangle.

## D4 — Only externally-called methods earn an arrow

Only methods called from outside the box get drawn as arrows — `register_tool`
and `add_message`. Internal methods like `to_s` and `turn_count` appear nowhere
on the diagram, not even inside the box; the box shows only its fields. The
criterion is who calls it, not what it does.

## D5 — The caller stays off the canvas

The arrows point from Tool and Message into Context, but neither struct is the
caller — a Struct is inert. The real caller is `examples/example.rb`, which
invokes `register_tool` and `add_message` and passes a Tool/Message as the
argument. Andrew draws the data-into-Context relationship but leaves the demo
script off the diagram, because a demo isn't architecture.

## D6 — No week-boundary box

Andrew considers enclosing the week-1 shapes in a boundary, then drops it as
unnecessary. The takeaway: don't add visual grouping until the diagram is
crowded enough to need it.

---

## Glossary

- **Struct** — a Ruby data holder: fields in, fields out, no methods worth
  calling. Inert.
- **class** — has methods (verbs); it acts, not just stores.
- **Abstract class** — a class never used directly, only extended (e.g.
  Tasks::Base).
- **edge / arrow** — a drawn relationship between two boxes. Means
  "related", not always "A calls B" — here it means "A is passed into B".
- **canvas** — the whole Lucidchart page.