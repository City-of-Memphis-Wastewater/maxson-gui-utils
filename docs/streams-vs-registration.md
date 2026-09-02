Stream wrapper and console registration operate at two different layers of the Python runtime stack, forming a two-tier capture model.

```
+-----------------------------------------------------------------------+
| LAYER 1: Explicit Opt-In (Console)                                   |
| - Custom RichConsole factory                                          |
| - Attaches a GuiStream to route Rich formatted output to dispatch     |
+-----------------------------------------------------------------------+
                                   |
                                   v
+-----------------------------------------------------------------------+
| LAYER 2: Process-Wide Catch-All (install_stream_wrappers)             |
| - Replaces sys.stdout / sys.stderr process-wide                       |
| - Intercepts standard print(), sys.stdout.write(), raw logging, etc.  |
+-----------------------------------------------------------------------+
                                   |
                                   v
+-----------------------------------------------------------------------+
| DISPATCH ENGINE (registration.py / dispatch_write)                     |
| - In-Process: Notifies subscribers registered via register_listener() |
| - Cross-Process: Sends payload over IPC (Named Pipe / UDS / UDP)      |
+-----------------------------------------------------------------------+
                                   |
                                   v
+-----------------------------------------------------------------------+
| RECEIVER (blindwindow.py / BlindWindow)                              |
| - Displays captured stream chunks in TextPane                         |
+-----------------------------------------------------------------------+

```

---

### Key Differences Between the Two Approaches

| Feature | `Console()` Factory (`console.py`) | Stream Wrappers (`streams.py`) |
| --- | --- | --- |
| **Scope** | **Scoped / Explicit.** Only captures output sent through that specific Rich `Console` instance. | **Global / Broad.** Intercepts all standard Python output at the OS/interpreter level. |
| **Target Audience** | Your own CLI tools using Rich for styled output, tables, and trees. | Third-party libraries, plain `print()` calls, `sys.stdout.write()`, or unconfigured standard loggers. |
| **Rich Formatting** | Full Rich markup, ANSI colors, panel borders, and theme rendering preserved. | Raw strings only (unless ANSI strip/parse routines process them down the pipe). |
| **Mechanics** | Constructs a `RichConsole` whose output target (`file=...`) points to a `TeeStream` containing a `GuiStream`. | Wraps `sys.stdout` and `sys.stderr` globally via `SystemStreamWrapper`. |

---

### How They Work Together Without Circular Loops

Because both `Console()` and `install_stream_wrappers()` route back into `dispatch_write()`, keeping them distinct prevents double-printing:

1. **`Console(tee_sys=True)`:** Passes its output to `sys.stdout` (via `TeeStream`).
2. **If `install_stream_wrappers()` is also active:** `sys.stdout` is now a `SystemStreamWrapper`.
3. If `Console()` were to call `dispatch_write()` directly **and** write to a wrapped `sys.stdout`, the text would get sent to `dispatch_write()` twice.

By keeping `streams.py` as the catch-all global standard stream interceptor and `console.py` as the explicit structured output creator, you maintain clean control over how CLI apps broadcast to `BlindWindow`.
