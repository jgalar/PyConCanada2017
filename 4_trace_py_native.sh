#!/bin/sh

if [ $# -eq 0 ]
  then
    echo "Usage: `basename "$0"` PID"
    exit 1
fi

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
