#!/bin/sh

if [ $# -eq 0 ]
  then
    echo "Usage: `basename "$0"` PID"
    exit 1
fi

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
