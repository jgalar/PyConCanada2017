# PyCon Canada 2017

Here is the content of my presentation at PyCon Canada 2017.

Aside from the presentation, you will find an example demonstrating
an example of a Babeltrace 2 component implemented in Python. The
component is imaginatively named `sink.pycon.StackView` (see
[`bt_plugin_pycon.py`](https://github.com/jgalar/PyConCanada2017/blob/master/bt_plugin_pycon.py)).

## Demos

All the demos presented were based on the tracing of Python's [`SimpleHTTPRequestHandler`](https://docs.python.org/3.6/library/http.server.html?highlight=http#http.server.SimpleHTTPRequestHandler)
serving a local copy of the [LTTng](https://lttng.org) home page.

Note that the only LTTng-specific line in `httpserver.py` is

```import lttngust```

This sets up all we need to redirect logging statements to LTTng.

See [tracing Python applications](https://lttng.org/docs/v2.10/#doc-python-application)
for more information on the `lttngust` package.

### 1) Tracing Python logging statements

Using [`1_trace_py_logging.sh`](https://raw.githubusercontent.com/jgalar/PyConCanada2017/master/1_trace_py_logging.sh),
we can setup a tracing session that will trace all events originating from
the Python logger for a given PID; the script's first parameter.

In essence, the script sets up the session as such:
```
# Create a live session named "py_logging"
lttng create py_logging --live

# Enable all Python agent (logger) events
lttng enable-event --python --all

# Only trace userspace events from the PID received as the first argument
lttng track --userspace --pid $1

lttng start
```

We can then use the `lttng view` command to see the events as they are produced
using Babeltrace.
[![asciicast](https://asciinema.org/a/nR0CX0ZqqC2ueLVV909lUTLtj.png)](https://asciinema.org/a/nR0CX0ZqqC2ueLVV909lUTLtj)

However, we can also use the `sink.pycon.StackView` to get a prettier version
of the same output.
[![asciicast](https://asciinema.org/a/6nQI8Qs6KJDNAzwlsPjIF6rel.png)](https://asciinema.org/a/6nQI8Qs6KJDNAzwlsPjIF6rel)


### 2) Tracing Python logging statements + syscalls

Where LTTng really shines is when we blend multiple sources of information. In
this example, we will setup a new session which traces the same Python `logging`
events. However, we will also trace the syscalls that are invoked by our
server.

Again, we can use a new script, `2_trace_py_syscalls.sh` to put that session in
place. This script executes the following commands.

```
# Create a live session
lttng create py_syscalls --live

# Enable all Python agent (logger) events
lttng track --userspace --pid $1
lttng enable-event --python --all

# So far, everything is the same as the previous example. However, let's also
# enable the tracing of all syscalls invoked by that same process.
lttng track --kernel --pid $1
lttng enable-event --kernel --syscall --all

lttng start
```

Using our `sink.pycon.StackView` component, we then get the following output
which shows both the Python logging statements _and_ the syscalls performed on
the same timeline.

[![asciicast](https://asciinema.org/a/zssVwVix7FBzZ3o0Mfwe196SM.png)](https://asciinema.org/a/zssVwVix7FBzZ3o0Mfwe196SM)


### 3) Tracing Python logging statements + syscalls + Python functions

Building on top of the previous example, we can go one level deeper: trace
all python functions as they are invoked.

To this end, we need to apply [three patches](https://bugs.python.org/issue28909)
which are under review by the upstream CPython project.

These patches add, amongst others, the following events which can be enabled
 sing LTTng:

```
python:function__entry
python:function__return
```

These new events allow our component to track whenever the Python interpreter
enters and exits a Python function.

We can use `3_trace_py_functions.sh` to setup a session similar to the previous
example. However, we will also enable those two new events.

```
# Create a live session
lttng create py_functions --live

# Enable Python function tracing
lttng enable-event --userspace python:function__entry
lttng enable-event --userspace python:function__return

# Enable all Python agent (logger) events
lttng track --userspace --pid $1
lttng enable-event --python --all

# Enable all syscalls invoked by python
lttng track --kernel --pid $1
lttng enable-event --kernel --syscall --all

lttng start
```

Now, let's see how Python logging statements, Python functions, and system calls
all interact with each other using our component.

[![asciicast](https://asciinema.org/a/v20Hxnoh3lpzzz3FPmF86fNDS.png)](https://asciinema.org/a/v20Hxnoh3lpzzz3FPmF86fNDS)


### 4) Tracing Python logging statements + syscalls + Python functions + CPython functions

Finally, we can go one level deeper. Let's see how we can trace C
functions being invoked _inside_ the CPython interpreter.

This requires a bit more work since we must build our own Python interpreter.

#### Building the interpreter

In order to retrieve the function names from the addresses recorded in the
LTTng trace, the binary must contain DWARF debug information and the
compiler must instrument the various functions' entry and exit points.

Make sure to build your interpreter with the following `CFLAGS`:

`CFLAGS="-finstrument-functions -g"`

While the component will work even if the binary has no DWARF information, it
will only be able to display function names which are exported (public symbols).
Unknown function names will be shown as `???()`.

#### Tracing the software

Our component depends on two events produced by an LTTng-ust helper library:
* `lttng_ust_cyg_profile_fast:func_entry`
* `lttng_ust_cyg_profile_fast:func_exit`

LTTng provides the `liblttng-ust-cygprofile-fast.so` shared object utility
in order to trace these events on the functions' entry and exit.
For more information, see the LTTng official documentation which has a
[dedicated section](https://lttng.org/docs/v2.10/#doc-liblttng-ust-cyg-profile)
on this mechanism.

#### Setup a tracing session

```
# Create a live session
lttng create py_native --live

# Explicitly create a userspace channel in order to enable context tracing
lttng enable-channel --userspace uchannel

# Trace the vpid (virtual PID) and ip (instruction pointer) contexts
lttng add-context --userspace --channel uchannel --type vpid
lttng add-context --userspace --channel uchannel --type ip

# Enable Python function tracing (Python code)
lttng enable-event --userspace --channel uchannel python:function__entry
lttng enable-event --userspace --channel uchannel python:function__return

# Enable Python interpreter function tracing (C code)
lttng enable-event --userspace --channel uchannel lttng_ust_cyg_profile_fast:func_entry
lttng enable-event --userspace --channel uchannel lttng_ust_cyg_profile_fast:func_exit

# Enable statedump events which allow the reader to map back instruction
# pointer addresses to the various libraries and binaries
lttng enable-event --userspace --channel uchannel 'lttng_ust_lib:*'
lttng enable-event --userspace --channel uchannel 'lttng_ust_statedump:*'

# Enable all Python agent (logger) events
lttng track --userspace --pid $1
lttng enable-event --python --all

# Enable all syscalls invoked by python
lttng track --kernel --pid $1
lttng enable-event --kernel --syscall --all

lttng start
```

#### Launching the web server with LD_PRELOAD

```
LD_PRELOAD=/usr/lib/liblttng-ust-cyg-profile-fast.so python httpserver.py
```

#### Tying it all together!

As you can see in the demo below, we now see all the syscalls and C functions
that go into the execution of our Python web server!

Of course, this is way too much information if you are not debugging a very
precise problem within CPython. However, it shows how easily LTTng can be used
to collect pretty much any information you need to understand what is going on
at any layer of your system.

[![asciicast](https://asciinema.org/a/zhmsHbufyn1HiWXWhlB1HGL3U.png)](https://asciinema.org/a/zhmsHbufyn1HiWXWhlB1HGL3U)

You may notice that all C functions initially show up as `???()`. This is
because our viewer is hooking up at a random point in the trace and can't
translate the instruction pointer into function names.

The `lttng regenerate statedump` command is used in another terminal to force
LTTng to emit the events which will provide Babeltrace with the information
it needs to map all instruction addresses to human-readable function names.

_Note that this demo seems to be giving Asciinema a run for its money, [click here](https://asciinema.org/a/zhmsHbufyn1HiWXWhlB1HGL3U) if the preview does
not show up! :-)_