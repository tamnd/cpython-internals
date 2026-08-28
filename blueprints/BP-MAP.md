# BP-MAP: the shape of the whole interpreter

**Covers:** `Modules/main.c`, `Python/pylifecycle.c`, `Python/pystate.c`, and the four long lived structures every other blueprint refers to
**Lesson:** T10, the napkin
**Status:** complete
**Compatibility tier:** B

## 1. Purpose and scope

This blueprint specifies the top level structure of a CPython process: which long lived objects exist, what contains what, in which order they are created and destroyed, and where every other blueprint attaches. It is the only blueprint that is allowed to describe the system as a whole. Every other one specifies a single subsystem and assumes the structure defined here.

In scope: the runtime state, the interpreter state, the thread state and the interpreter frame; the process lifecycle from entry to exit; the ownership rule that assigns each CPython source file to exactly one blueprint.

Out of scope: the behaviour of any individual subsystem. This blueprint says that `Python/gc.c` belongs to `BP-GC` and that the collector runs inside an interpreter rather than inside the runtime. It does not say what the collector does.

The boundary between this blueprint and `BP-PIPELINE` is that `BP-PIPELINE` starts at a byte buffer holding source text and ends at a frame that is ready to execute. Everything that has to exist before that buffer can be handed to anything is here.

### 1.1 Ownership

Two blueprints may not specify the same code. Where a file is large enough to hold more than one subsystem the split is by function and is recorded here.

| Area | Files | Blueprint |
|---|---|---|
| Process lifecycle and state | `Modules/main.c`, `Python/pylifecycle.c`, `Python/pystate.c` | BP-MAP |
| Tokenizer | `Parser/lexer/`, `Parser/tokenizer/` | BP-TOKENIZER |
| Parser | `Parser/parser.c`, `Parser/pegen.c`, `Grammar/python.gram` | BP-PARSER |
| Abstract syntax tree | `Parser/Python.asdl`, `Python/Python-ast.c` | BP-AST |
| Symbol table | `Python/symtable.c` | BP-SYMTABLE |
| Code generation | `Python/compile.c`, `Python/codegen.c` | BP-CODEGEN |
| Control flow graph and optimizer | `Python/flowgraph.c` | BP-CFG |
| Assembler | `Python/assemble.c` | BP-ASSEMBLE |
| Code objects | `Objects/codeobject.c`, `Include/cpython/code.h` | BP-CODEOBJECT |
| Eval loop | `Python/ceval.c`, `Python/bytecodes.c`, `Python/generated_cases.c.h` | BP-EVAL |
| Frames | `Python/frame.c`, `Objects/frameobject.c` | BP-FRAME |
| Object protocol | `Include/object.h`, `Objects/object.c`, `Objects/abstract.c` | BP-OBJECT |
| Reference counting | `Include/refcount.h` | BP-REFCOUNT |
| Cycle collector | `Python/gc.c`, `Python/gc_free_threading.c` | BP-GC |
| Allocator | `Objects/obmalloc.c` | BP-OBMALLOC |

The rest of the inventory is in the milestone issues. A file that is not in the table has no blueprint yet, and a claim about it may not be made in any blueprint until it does.

## 2. Data structures

### 2.1 `_PyRuntimeState`

`Include/internal/pycore_runtime_structs.h:134-170@v3.15.0rc1#pyruntimestate` for the header and the flags, `Include/internal/pycore_runtime_structs.h:184-205@v3.15.0rc1#pyinterpreters` for the interpreter list

One per process. It is a static object rather than an allocation, which matters because it has to be readable before anything can allocate.

| Field | C type | Meaning |
|---|---|---|
| `debug_offsets` | `_Py_DebugOffsets` | Field offsets of the other structures, written out so an out of process debugger can walk them without knowing the layout. Must be the first field. |
| `_initialized` | `int` | The structure has been zeroed into a safe state. |
| `preinitialized` | `int` | Encoding, allocator and memory settings are fixed. |
| `core_initialized` | `int` | Built in types and the first interpreter exist. |
| `initialized` | `int` | The import system and `__main__` exist. |
| `interpreters.head` | `*PyInterpreterState` | The linked list of interpreter states, newest first. |
| `interpreters.main` | `*PyInterpreterState` | The first interpreter, which has a special role in shutdown and is often the only one. |
| `interpreters.next_id` | `int64_t` | The id counter. The main interpreter is always 0, and overflow raises `RuntimeError` rather than wrapping. |
| `main_thread` | `unsigned long` | The OS thread that called `Py_Initialize`. |

The four separate initialization flags are not redundant. Each one names a point at which a different set of operations becomes legal, and section 6 lists what is legal at each.

### 2.2 `PyInterpreterState`

`Include/internal/pycore_interp_structs.h:842-880@v3.15.0rc1#_is`

One per interpreter. A process has at least one and may have many. Interpreters share the process and the allocator; they do not share modules, built in singletons beyond the immortal ones, or the import lock.

| Field | C type | Meaning |
|---|---|---|
| `ceval` | `struct _ceval_state` | The eval breaker and the per interpreter scheduling state. Placed first because the eval loop reads it constantly. |
| `next` | `*PyInterpreterState` | The next interpreter in the runtime's list. |
| `id` | `int64_t` | Identity, unique within the process for the life of the process. |
| `_initialized`, `_ready`, `finalizing` | `int` | Lifecycle flags, with the same meaning as the runtime's but scoped to this interpreter. |
| `threads.head` | `*PyThreadState` | The thread states belonging to this interpreter, newest first. |
| `threads.main` | `*PyThreadState` | The thread running `__main__`, if one is. |
| `threads.count` | `ssize` | How many thread states are in the list. |

### 2.3 `PyThreadState`

`Include/cpython/pystate.h:66-101@v3.15.0rc1#_ts` for the header and the status flags, `Include/cpython/pystate.h:121-140@v3.15.0rc1#current_frame` for the recursion counters and the frame pointer, `Include/cpython/pystate.h:196-205@v3.15.0rc1#datastack_chunk` for the data stack

One per Python level thread. It is the structure the eval loop is holding a pointer to at all times.

| Field | C type | Meaning |
|---|---|---|
| `prev`, `next` | `*PyThreadState` | Position in the owning interpreter's list. |
| `interp` | `*PyInterpreterState` | The owning interpreter. Never `NULL` on a live thread state. |
| `eval_breaker` | `uintptr_t` | Instrumentation version in the high bits, and in the low bits the flags that make the eval loop leave its fast path. |
| `_status.initialized` | bitfield | The structure is in a safe state. |
| `_status.bound` | bitfield | An OS thread has claimed this thread state. |
| `_status.active` | bitfield | This thread state is currently the one executing. |
| `_status.finalizing`, `cleared`, `finalized` | bitfield | The three stages of teardown, which are distinct because objects can run Python code during the first of them. |
| `py_recursion_remaining` | `int` | How many more Python frames this thread may push before `RecursionError`. |
| `py_recursion_limit` | `int` | The value `sys.setrecursionlimit` writes. |
| `recursion_headroom` | `int` | Extra calls allowed past the limit so that raising the error is itself possible. The comment in the header puts it at 50. |
| `current_frame` | `*_PyInterpreterFrame` | The top of this thread's frame stack. |
| `datastack_chunk`, `datastack_top`, `datastack_limit` | pointers | The chunked stack that frames are carved out of. |
| `datastack_cached_chunk` | `*_PyStackChunk` | One freed chunk kept back, so that a call depth oscillating across a chunk boundary does not allocate on every crossing. |

### 2.4 `_PyInterpreterFrame`

`Include/internal/pycore_interpframe_structs.h:29-53@v3.15.0rc1#_PyInterpreterFrame`

One per active call. It is not a Python object and it is not allocated individually; it is a region of the thread's data stack.

| Field | C type | Meaning |
|---|---|---|
| `f_executable` | `_PyStackRef` | The code object being run, or `None`. |
| `previous` | `*_PyInterpreterFrame` | The caller's frame. `NULL` at the bottom of the stack. |
| `f_funcobj` | `_PyStackRef` | The function object, when there is one. |
| `f_globals`, `f_builtins` | `*PyObject` | Borrowed. The two outer namespaces for name lookup. |
| `f_locals` | `*PyObject` | Strong, may be `NULL`. Present only where the frame has a real locals mapping, such as a class body or `exec`. |
| `frame_obj` | `*PyFrameObject` | Strong, may be `NULL`. The Python visible `frame` object, created on demand. |
| `instr_ptr` | `*_Py_CODEUNIT` | The instruction executing or about to execute. |
| `stackpointer` | `*_PyStackRef` | One past the top of the value stack. |
| `return_offset` | `uint16` | Where to resume in the caller. |
| `owner` | `char` | Which of the several frame owners carved this region out, which decides who pops it. |
| `localsplus` | `[_PyStackRef]` | Locals, then cells, then free variables, then the value stack, in one contiguous run. |

The last field is the reason a frame is not a fixed size. `co_framesize` on the code object says how many words this run needs, and section 3.3 shows the frame being carved out.

### 2.5 The two universal currencies

Two structures appear in every other blueprint and are specified elsewhere, but the boundary is worth stating here.

`PyObject` (`Include/object.h:127-150@v3.15.0rc1#_object`) is the header every value carries. Nothing in the system passes a value by any other means. Specified by `BP-OBJECT`.

`PyCodeObject` (`Include/cpython/code.h:45-84@v3.15.0rc1#_PyCode_DEF`) is the single artifact that crosses from the compile side to the run side. Specified by `BP-CODEOBJECT`, with its production specified by `BP-PIPELINE`.

## 3. Algorithms

### 3.1 `run_process`

**CPython:** `Modules/main.c:830-852@v3.15.0rc1#Py_RunMain`
**Precondition:** the runtime has been preinitialized and configured
**Postcondition:** the process exit code
**Complexity:** unbounded, this is the program
**Fails:** cannot fail, it reports failure as an exit code

```
func run_process() -> int:
    let exitcode: int = 0
    runtime->signals.unhandled_keyboard_interrupt = 0
    run_python(&exitcode)          # BP-PIPELINE takes over here
    if finalize() < 0:
        exitcode = 120             # chosen not to collide with a real status
    free_main_state()
    if runtime->signals.unhandled_keyboard_interrupt:
        exitcode = sigint_exit_code()
    return exitcode
```

The interesting part is that finalization failure is reported as an exit code and never as an exception. By the time this runs there may be no thread state to hold an exception, which is the constraint that shapes all of section 6.

### 3.2 `initialize`

**CPython:** `Python/pylifecycle.c:1609-1639@v3.15.0rc1#Py_InitializeFromConfig`
**Precondition:** `config` is a fully filled configuration, or the call fails
**Postcondition:** a runtime, one interpreter, one bound thread state, and if `_init_main` was set, an import system and `__main__`
**Complexity:** O(number of built in types plus frozen modules)
**Fails:** returns a failing status, does not set an exception, because there may be no thread state to set it on

```
func initialize(config: *PyConfig) -> Status:
    if config == NULL:
        return error("initialization config is NULL")
    let status: Status = runtime_initialize()
    if is_error(status):
        return status
    let runtime: *PyRuntimeState = &the_runtime
    let tstate: *PyThreadState = NULL
    status = init_core(runtime, config, &tstate)   # types, first interpreter, first thread
    if is_error(status):
        return status
    config = tstate->interp->config
    if config->_init_main:
        status = init_main(tstate)                 # sys.path, import machinery, __main__
        if is_error(status):
            return status
    return ok()
```

The two phase split is what allows an embedder to stop after `init_core`, adjust the configuration using the interpreter it now has, and only then build the import system. Section 6.1 lists what is legal between the two phases.

### 3.3 `push_frame`

**CPython:** `Python/pystate.c:3133-3143@v3.15.0rc1#_PyThreadState_PushFrame`
**Precondition:** `tstate` is the current thread state, `size` is `co_framesize` in words
**Postcondition:** returns a region of at least `size` words, uninitialized
**Complexity:** O(1) amortized, O(chunk size) when a new chunk is needed
**Fails:** returns NULL, sets an error

```
func push_frame(tstate: *PyThreadState, size: ssize) -> *InterpreterFrame:
    if tstate->datastack_top + size <= tstate->datastack_limit:
        let res: *InterpreterFrame = cast(*InterpreterFrame, tstate->datastack_top)
        tstate->datastack_top = tstate->datastack_top + size
        return res
    return push_chunk(tstate, size)   # allocate a fresh chunk, link it, carve from it
```

A Python call is a pointer bump in the common case. This is the single most important fact about the shape of the system, and it is why `BP-FRAME` and `BP-EVAL` are separate blueprints from `BP-OBJECT`: frames deliberately do not go through the object allocator.

## 4. Invariants

**INV-MAP-001.** There is exactly one `_PyRuntimeState` per process, and it is statically allocated. Nothing may allocate before it is readable.

**INV-MAP-002.** Containment is strict: a runtime holds interpreters, an interpreter holds thread states, a thread state holds a stack of frames. No structure at one level points sideways into a peer's private state.

**INV-MAP-003.** Every live `PyThreadState` has a non `NULL` `interp`, and that interpreter's thread list contains it.

**INV-MAP-004.** At most one thread state per OS thread has `_status.active` set.

**INV-MAP-005.** `frame->previous` forms a chain with no cycles, ending in `NULL`.

**INV-MAP-006.** A frame occupies `co_framesize` words of the thread's data stack, and frames are popped in exactly the reverse of the order they were pushed.

**INV-MAP-007.** Every value that Python level code can name is a `*PyObject`. There is no second representation and no unboxed value that can escape into a local, a container or an argument.

**INV-MAP-008.** A code object is the only artifact that crosses from the compile side to the run side. Nothing on the run side reads a token, a parse tree or a symbol table.

**INV-MAP-009.** The four runtime initialization flags only ever move forwards during startup and only ever backwards during shutdown. No operation observes them out of order.

**INV-MAP-010.** Every file listed in the ownership table in section 1.1 is claimed by exactly one blueprint.

## 5. Observable behaviour

The structure in section 2 is mostly not observable, which is what makes this a tier B document rather than a tier A one. A reimplementation may lay these structures out any way it likes. What it may not change is the following list, because Python level code reads all of it.

`sys._getframe(n)` returns a frame object for the frame `n` levels up, and raises `ValueError` when `n` exceeds the depth. That the frames form a chain, and that walking `f_back` reaches the bottom, is therefore tier A.

`sys.setrecursionlimit` and `sys.getrecursionlimit` expose a per interpreter integer, and exceeding it raises `RecursionError`. The limit counts Python frames rather than C stack bytes, and a reimplementation that counts anything else changes which programs run.

`threading.current_thread`, `sys._current_frames` and `threading.enumerate` expose the fact that thread states are per interpreter and are enumerable.

The `interpreters` module exposes interpreter creation, and with it the fact that two interpreters do not share module objects. A program that creates one and observes that `sys.modules` is empty in it is depending on INV-MAP-002.

`sys.is_finalizing` exposes the difference between the runtime being initialized and being torn down, which is the only one of the four flags in 2.1 that Python code can read.

Timing and memory use expose the pointer bump in 3.3, but no program can read the data stack directly, so that is tier C.

## 6. Edge cases and error paths

### 6.1 Between the two initialization phases

After `init_core` and before `init_main` there is a runtime, an interpreter, a thread state and every built in type, but there is no import system, no `sys.path` and no `__main__`. Code that runs here may create objects and call built in functions. It may not import anything, and it may not raise an exception that expects a traceback module to be importable during handling.

### 6.2 Before any thread state exists

Configuration parsing and preinitialization run with no thread state. Nothing there may set an exception, because there is nowhere to store one. This is why 3.2 returns a status structure rather than an error indicator, and why a failure at this stage prints to standard error and exits rather than propagating.

### 6.3 During finalization

Finalization has three stages per thread state, recorded in `_status.finalizing`, `cleared` and `finalized`, because the first stage can run arbitrary Python code. An object's `__del__` can create new objects, start threads and raise exceptions during the stage that is supposed to be destroying it. A reimplementation that treats teardown as a single atomic step will deadlock or crash on ordinary code.

`Py_FinalizeEx` returning a negative value is a real outcome and not just a defensive branch. It happens when a thread other than the main one is still running Python code.

### 6.4 Data stack exhaustion

`push_frame` failing to get a new chunk is an allocation failure, and it happens while the caller has a half built call in progress. The caller must unwind without the frame it asked for. This is distinct from `RecursionError`, which is a limit the interpreter enforces before it gets here.

### 6.5 Recursion inside the recursion handler

Raising `RecursionError` requires building an exception object, which requires a frame's worth of work. CPython reserves `recursion_headroom` calls above the limit for this, and the header puts the number at 50. A reimplementation that does not reserve anything will crash exactly when it is trying to report the problem cleanly.

### 6.6 Accidental behaviour

The exit code 120 in 3.1 is a value chosen because it is unlikely to collide with anything meaningful, not one specified anywhere. Depending on it is depending on an accident.

The order of `interp->threads.head` is newest first. Nothing documents this, and `threading.enumerate` sorts nothing, so the observable enumeration order of threads is an accident of the list insertion. A reimplementation is free to differ, and portable code was already not allowed to depend on it.

## 7. Interactions

Every other blueprint depends on this one for the meaning of "the current thread state" and "the current frame", which are the two arguments almost every internal function takes.

`BP-PIPELINE` depends on 3.2 having run, because compilation needs the built in types and, for anything but a single expression, the import system.

`BP-EVAL` depends on INV-MAP-004, INV-MAP-005 and 3.3. The eval loop's fast path for a Python to Python call is exactly the pointer bump in 3.3 with no C stack frame added.

`BP-GC` depends on INV-MAP-002, because a collection is per interpreter and must not walk another interpreter's objects.

`BP-OBMALLOC` sits below all of it and is per process rather than per interpreter, which is the one place where the containment in INV-MAP-002 does not describe the memory.

`BP-REFCOUNT` depends on INV-MAP-007. If some values were not objects, the counting would have a hole in it.

## 8. Conformance

| Claim | Held up by |
|---|---|
| The stage list and the compile/run boundary, INV-MAP-008 | `lessons/t10-the-napkin`, the single cell that runs all eight stages |
| Frames form a chain, INV-MAP-005 | `sys._getframe` walked to the bottom in `lessons/t07-the-machine-runs` |
| Every value is an object, INV-MAP-007 | `lessons/t08-everything-is-an-object` |
| The citations in sections 2 and 3 still point at the code they claim | `just citations`, on every change |
| The nine sections and the header block of this document | `just blueprints` |

The conformance gap this blueprint has, stated rather than hidden: nothing in the repository currently tests the initialization phase boundary in 6.1 or the three stage teardown in 6.3, because both need an embedder rather than a Python program. `test_embed` in CPython covers them, and porting a reduced version of it is tracked in the milestone issues.

## 9. Port notes

The containment in INV-MAP-002 maps cleanly onto any language. The thing that does not map is that CPython's thread state is reachable from a thread local and is passed explicitly at the same time. Go will want it in a context or an explicit receiver, and Rust will want it as a `&mut` that everything borrows from, which changes almost every function signature in the system. Deciding this early is worth more than any other early decision, because retrofitting it means touching every file.

The data stack in 3.3 is worth keeping. It is not an optimization detail, it is the reason a Python call does not consume host stack, and a port that allocates a frame per call on the host heap will be slower and will hit a different recursion limit than the one INV-MAP-005 and section 5 describe.

Go's goroutines do not map onto `PyThreadState` one for one, since a thread state assumes an OS thread it can be bound to and unbound from. The bound and unbound flags in 2.3 exist for exactly this, so a port has a hook, but the mapping needs designing rather than assuming.

The debug offsets block in 2.1 can be generated rather than typed. It is a table of field offsets, and any port that wants out of process debugging can produce the equivalent from its own struct definitions at build time.

Nothing in this blueprint needs to be bit compatible. That is the whole reason it is tier B, and it makes the top level the easiest part of the system to port and the hardest part to get the shape of right.
