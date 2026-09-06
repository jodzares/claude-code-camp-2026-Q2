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
| `class X < StandardError; end` | define a custom error type built on the base error | `class X(Exception): pass` | w1 The Registry Ruby |
| `raise X, "msg"` | stop and throw a named error | `raise X("msg")` | w1 The Registry Ruby |
| `begin / rescue X => e / end` | try this; if error X is thrown, catch it as `e` | `try: / except X as e:` | w1 The Registry Ruby |
| `hash.transform_keys(&:to_sym)` | turn every string key into a symbol key | (n/a — Python dict keys stay strings; `**args` unpacks to keyword params) | w1 The Registry Ruby |
| `block.call(**args)` | run a stored code block, unpacking a hash into its args | `fn(**args)` | w1 The Registry Ruby |
| `method(...) do |x:| ... end` | trailing block — attach a chunk of code to a call, to be run later | `@decorator` line directly above a `def` | w1 The Registry Python Port |
| `hash[key]` | look up a key; returns `nil` if absent | `dict.get(key)` — returns `None` if absent | w1 The Registry Python Port |
| `def f(parameters: {})` | keyword arg defaulting to an empty hash | `def f(parameters=None)` then `parameters or {}` — avoids one shared mutable default | w1 The Registry Python Port |
| `hash.each_value { |t| ... }` | loop over the values, ignoring the keys | `for t in dict.values():` | w1 The Registry Python Port |
| `require_relative "errors"` | pull in a sibling file from this folder | `from .errors import UnknownToolError` | w1 The Registry Python Port |
| `def self.foo(x)` | a method that belongs to the type itself, not to one object | `@classmethod def foo(cls, x)` | w1 Prompt Builder Ruby |
| `MODELS = {...}.freeze` | a named table fixed at load time and locked against edits | `MODELS: Final = {...}` (Python can't truly lock a dict) | w1 Prompt Builder Ruby |
| `const_get(:MODELS)` | look up a constant by name on whichever type is asking | `getattr(cls, "MODELS")` | w1 Prompt Builder Ruby |
| `raise NotImplementedError` | "any type built on me must define this itself" | `raise NotImplementedError` | w1 Prompt Builder Ruby |
| `ENV.fetch("K")` | read an environment variable; blow up if it isn't set | `os.environ["K"]` | w1 Prompt Builder Ruby |
| `ENV["K"] \|\|= value` | set it only if it isn't already set | `os.environ.setdefault("K", value)` | w1 Prompt Builder Ruby |
| `hash.fetch(:key)` | read a key; blow up if absent (vs `hash[key]` → `nil`) | `d["key"]` | w1 Prompt Builder Ruby |
| `x = case y when "a" then ... else ... end` | a branch that *produces* a value, assigned in one go | `if/elif/else` assigning to `x`, or a dict lookup | w1 Prompt Builder Ruby |
| `list.map { \|x\| ... }` | build a new list by transforming every item | `[... for x in list]` | w1 Prompt Builder Ruby |
| `hash.values` | just the values, keys discarded | `dict.values()` | w1 Prompt Builder Ruby |
| `hash.keys.sort.join(", ")` | names, alphabetised, glued into one readable string | `", ".join(sorted(d))` | w1 Prompt Builder Ruby |
| `:tokens` | a symbol used as a fixed label/value, not text to show a user | `"tokens"`, or an `Enum` member | w1 Prompt Builder Ruby |
| `200_000` / `1_000_000.0` | underscores are digit separators, ignored by the language | identical in Python | w1 Prompt Builder Ruby |
| `"#{a} #{b}"` | string interpolation — drop values into a string | `f"{a} {b}"` | w1 Prompt Builder Ruby |
| `value.inspect` | render a value with its quotes/type visible, for error messages | `repr(value)` | w1 Prompt Builder Ruby |
| `JSON.pretty_generate(x)` | turn data into indented JSON text | `json.dumps(x, indent=2)` | w1 Prompt Builder Ruby |
| `Net::HTTP.new(host, port)` + `http.request(req)` | send an HTTP request using only what ships with the language | `urllib.request.urlopen(Request(...))` | w1 API Client Python Port |
| `http.request` hands back a response for every status code | the sender treats "server said 500" as a normal answer | `urlopen` **raises** `HTTPError` for non-2xx — the status only exists inside a catcher | w1 API Client Python Port |
| `rescue *TRANSIENT_ERRORS => e` | catch any error from a named list, splatted in | `except TRANSIENT_ERRORS as e` (a tuple, no splat needed) | w1 API Client Python Port |
| `[408, 429, 500].freeze` | a fixed list used only for membership checks | `{408, 429, 500}` — a set literal | w1 API Client Python Port |
| `response.is_a?(Net::HTTPSuccess)` | ask whether the status means success | `200 <= status < 300` | w1 API Client Python Port |
| `JSON.parse(str)` | turn JSON text into navigable data | `json.loads(str)` | w1 API Client Python Port |
| `hash.to_json` | turn data into JSON text ready to send | `json.dumps(data).encode("utf-8")` — bytes, not text, for the request body | w1 API Client Python Port |
| `sleep 0.5` | pause this thread | `time.sleep(0.5)` | w1 API Client Python Port |
| `loop do ... break ... end` | repeat until something breaks out | `while True: ... break` | w1 API Client Python Port |
| `URI(url_string)` | parse a URL into its parts before sending | not needed — `urllib.request.Request` takes the URL string directly | w1 API Client Python Port |
| `Errno::ECONNRESET`, `Errno::ECONNREFUSED` | OS-level connection faults, one name per error code | `ConnectionError` — one parent covering reset, refused, aborted, broken pipe | w1 API Client Python Port |
| `Net::OpenTimeout`, `Net::ReadTimeout`, `Timeout::Error` | connect timeout, read timeout, generic timeout | `TimeoutError` — Python doesn't split connect from read at the type level | w1 API Client Python Port |
| `SocketError` | broad socket/address failure, in practice DNS | `socket.gaierror` — the exact DNS-lookup failure | w1 API Client Python Port |
| `OpenSSL::SSL::SSLError` | TLS handshake or negotiation failure | `ssl.SSLError` | w1 API Client Python Port |
| (no equivalent) | chain a new error to the one that caused it, preserving context | `raise ApiError(...) from e` | w1 API Client Python Port |