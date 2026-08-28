# Notation

Every blueprint writes its algorithms in the same dialect. This page defines it. It is not a language, nothing executes it, and there is no compiler for it. It exists so that thirty eight documents written over a long time do not each invent their own way of saying "free this".

The dialect is deliberately lower level than Python and slightly higher level than C. Lower than Python because a blueprint that says `for item in items` has hidden an iterator protocol, a refcount and an exception path, which is exactly the material somebody porting the subsystem needs. Higher than C because the macro layer, the `#ifdef` layer and the goto layer are CPython's problems rather than the subsystem's.

## Types

Locals are declared with their type. There is no inference.

```
let n: int = 0
let ob: *PyObject = NULL
let items: *[*PyObject] = NULL
```

`*T` is a pointer to `T`. `[T]` is a contiguous array of `T`. `*[T]` is therefore a pointer to a contiguous array, which is what most of CPython's storage actually is.

The scalar types are `int` for a C `int`, `ssize` for `Py_ssize_t`, `uint32` and friends where the width matters, `bool`, `char` and `byte`. Anything else is a struct named in section 2 of the blueprint using it.

`NULL` is the null pointer and nothing else. A blueprint never writes `None` for a C level absent value, because in CPython `Py_None` is a real object with a real address and confusing the two is a porting bug that takes a day to find.

## Dereferencing

Pointer dereference is explicit and there is no `.` shorthand for it.

```
ob->ob_refcnt = 1
let t: *PyTypeObject = ob->ob_type
let first: *PyObject = items[0]
```

Taking an address is `&x`. Casting is `cast(*PyTypeObject, ob)` rather than C's prefix form, because the C form is unreadable once the type has a star in it.

## Allocation

Allocation and release are always written out. A blueprint never lets an object appear.

```
let mem: *byte = allocate(size)
if mem == NULL:
    return NULL
free(mem)
```

`allocate(n)` returns `n` bytes or `NULL`. `free(p)` releases them. Where the subsystem specifically uses the object allocator rather than raw memory the blueprint writes `allocate_object(type, nitems)` and says which one it means in section 2.

## Reference counting

Refcount changes are statements, one per line, never bundled into another operation.

```
incref ob
decref ob
xdecref maybe_null
```

`incref` adds one. `decref` subtracts one and, if the result is zero, calls the type's deallocator. `xdecref` does nothing when its argument is `NULL` and otherwise behaves as `decref`.

Every function's contract says what it does to the refcount of each argument and what the caller owns on return. The three words are the ones CPython uses: a **new reference** is one the caller must release, a **borrowed reference** is one the caller must not release and must not keep past a stated point, and a **stolen reference** is one the callee took over.

## Errors

There are no exceptions in the notation. A function that can fail says so in its contract and returns a sentinel, and the caller checks it. This matches the C and it keeps the error paths visible, which is where the refcount bugs live.

```
fails: returns NULL, sets an error
fails: returns -1, sets an error
cannot fail
```

"Sets an error" means the thread's current error state now holds an exception. A blueprint spells out which exception when a Python program can see it, since that is tier A behaviour, and leaves it as "sets an error" when it cannot.

## Control flow

Indentation, like Python. `if`, `elif`, `else`, `while`, `for i in 0 .. n` for a half open integer range, `break`, `continue`, `return`. There is no `goto` and there are no labels, because the one thing C's `goto error` buys is a shared cleanup block, and a blueprint writes the cleanup out at each exit instead so that no reader has to jump.

`for each x in seq` iterates a structure defined in section 2 of the same blueprint, and the blueprint says what the iteration order is. Where the order is not specified in CPython the blueprint says that too, since a port is then free to choose.

## Function headers

Each algorithm carries the same block above it.

```
### build_frame

**CPython:** `Python/ceval.c:1212-1218@v3.15.0rc1#_PyEval_EvalFrameDefault`
**Precondition:** `code` is a valid code object, `globals` is a dict
**Postcondition:** returns a new reference, or NULL with an error set
**Complexity:** O(1) in the size of the code object
**Fails:** returns NULL, sets an error
```

The `CPython` line is a citation in the project format and is resolved against the pinned tree by `just citations` like every other claim in the repository. The name above it is the blueprint's name for the algorithm, which is usually but not always CPython's name, since CPython's is sometimes an implementation detail like a `_impl` suffix or a static helper that only exists because of a macro.

## Comments

`#` to end of line. Comments explain why a step is there and never restate what it does.

## What is deliberately missing

There is no type system, no generics, no modules, no strings beyond byte arrays, and no standard library. Every blueprint that needs a hash table, a growable array or a string builder specifies it in its own section 2 or names the blueprint that does. A port in Go or Rust will use its own, and the point of the notation is to make the boundary of what CPython actually guarantees clear enough to know when that substitution is safe.
