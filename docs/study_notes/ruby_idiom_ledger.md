# Ruby Idiom Ledger
 
Running list of Ruby idioms met during Ruby lessons, each with its plain meaning
and Python twin. Accumulates across lessons so later line-level walkthroughs arrive
pre-vocabularied. Max one new idiom per receipt.
 
| Ruby idiom | Plain meaning | Python twin | First met |
|------------|---------------|-------------|-----------|
| `@foo` | instance variable — a value one object keeps in its own memory (its state) | `self.foo` | w1 Config Ruby |
| `class Player < Base` | inheritance — Player is built on top of Base and gets all its methods for free | `class Player(Base):` | w1 Config Ruby |
| `Struct.new(:a, :b)` | a lightweight record — fields only, no behaviour | `@dataclass` + typed fields | w1 Struct Skeleton Python Port |
| `def initialize` | the setup method that runs when an object is born | `def __init__` | w1 Struct Skeleton Python Port |
| `def x = @y.size` | a method read like a noun, called with no parens | `@property` + `len()` | w1 Struct Skeleton Python Port |
| `task&.task_name` | safe navigation — call only if `task` isn't nil | `if hasattr(task, "task_name")` | w1 Struct Skeleton Python Port |
| `str[0..40]` | slice, end-inclusive (0..40 = 41 chars) | `str[:41]`, end-exclusive | w1 Struct Skeleton Python Port |
 