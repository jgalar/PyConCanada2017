import bt2
import os
import datetime
from termcolor import colored


@bt2.plugin_component_class
class StackView(bt2._UserSinkComponent):
    def __init__(self, config, params, obj):
        self._indent_level = 0
        self._last_timestamp = None
        self._my_input_port = self._add_input_port("my_input_port")

    def _user_graph_is_configured(self):
        self._iterator = self._create_message_iterator(self._my_input_port)

    def _print_time(self, msg, color=None):
        timestamp_ns = msg.default_clock_snapshot.ns_from_origin

        if self._last_timestamp is None:
            disp_time = str(datetime.datetime.fromtimestamp(timestamp_ns / 1e9))
        else:
            color = None
            delta = timestamp_ns - self._last_timestamp

            if delta > 1e9:
                delta /= 1e9
                color = "red"
                unit = "s"
            elif delta > 1e6:
                delta /= 1e6
                color = "yellow"
                unit = "ms"
            elif delta > 1e3:
                delta /= 1e3
                color = "blue"
                unit = "μs"
            else:
                unit = "ns"

            disp_time = "+{} {}".format(delta, unit)
            disp_time = "{:>26}".format(disp_time)

        if color is not None:
            disp_time = colored(disp_time, color, attrs=["bold"])

        print(disp_time + "  " * self._indent_level, end="")
        self._last_timestamp = timestamp_ns

    def _on_scope_entry(self, msg):
        self._indent_level += 1
        self._print_time(msg)

    def _on_scope_exit(self):
        if self._indent_level > 0:
            self._indent_level -= 1

        print(end="", flush=True)

    def _on_native_function_entry(self, msg):
        self._on_scope_entry(msg)
        function_name = msg.event["debug_info"]["func"][:-2]

        if function_name == "":
            function_name = "???"

        print(colored(function_name, attrs=["bold"]) + "()")

    def _on_native_function_exit(self):
        if self._last_timestamp is None:
            return

        self._on_scope_exit()

    def _on_python_function_entry(self, msg):
        self._on_scope_entry(msg)
        event = msg.event
        colored_func_name = colored(event["co_name"], "green", attrs=["bold"])
        print(
            "{}() [{}:{}]".format(
                colored_func_name,
                os.path.basename(str(event["co_filename"])),
                event["line_no"],
            )
        )

    def _on_python_function_exit(self):
        if self._last_timestamp is None:
            return

        self._on_scope_exit()

    def _on_syscall_entry(self, msg):
        self._on_scope_entry(msg)
        event_name = msg.event.name[14:]
        print(colored(event_name, "cyan", attrs=["bold"]) + "(", end="")
        first_field = True

        for name, value in msg.event.payload_field.items():
            if not first_field:
                print(", ", end="")

            print(name + " = " + colored(str(value), attrs=["bold"]), end="")
            first_field = False

        print(")", end="")

    def _on_syscall_exit(self, msg):
        if self._last_timestamp is None:
            return

        ret = msg.event["ret"]

        if ret < 0:
            print(colored(" = {}".format(ret), "red", attrs=["bold"]))
        else:
            print(colored(" = {}".format(ret), attrs=["bold"]))

        self._on_scope_exit()

    def _on_python_logging_statement(self, msg):
        self._on_scope_entry(msg)
        print(colored(msg.event["msg"], "magenta", attrs=["bold"]))
        self._on_scope_exit()

    def _user_consume(self):
        msg = next(self._iterator)

        if type(msg) is not bt2._EventMessageConst:
            return

        event_name = msg.event.name
        is_syscall_getpid = event_name.endswith("getpid")

        if event_name == "lttng_python:event":
            self._on_python_logging_statement(msg)
        elif event_name.startswith("syscall_entry") and not is_syscall_getpid:
            self._on_syscall_entry(msg)
        elif event_name.startswith("syscall_exit") and not is_syscall_getpid:
            self._on_syscall_exit(msg)
        elif event_name == "python:function__entry":
            self._on_python_function_entry(msg)
        elif event_name == "python:function__return":
            self._on_python_function_exit()
        elif event_name == "lttng_ust_cyg_profile_fast:func_entry":
            self._on_native_function_entry(msg)
        elif event_name == "lttng_ust_cyg_profile_fast:func_exit":
            self._on_native_function_exit()


bt2.register_plugin(__name__, "pycon")
