import bt2
import os
import datetime
from termcolor import colored


@bt2.plugin_component_class
class StackView(bt2._UserSinkComponent):
    def __init__(self, params):
        self._indent_level = 0
        self._last_timestamp = None
        self._add_input_port("my_input_port")

    def _print_time(self, notification, color=None):
        event = notification.event
        clock_class_prio_map = notification.clock_class_priority_map
        clock_class = clock_class_prio_map.highest_priority_clock_class
        timestamp_ns = event.clock_value(clock_class).ns_from_epoch

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

    def _on_scope_entry(self, notification):
        self._indent_level += 1
        self._print_time(notification)

    def _on_scope_exit(self):
        if self._indent_level > 0:
            self._indent_level -= 1

        print(end="", flush=True)

    def _on_native_function_entry(self, notification):
        self._on_scope_entry(notification)
        function_name = notification.event["debug_info"]["func"][:-2]

        if function_name == "":
            function_name = "???"

        print(colored(function_name, attrs=["bold"]) + "()")

    def _on_native_function_exit(self):
        if self._last_timestamp is None:
            return

        self._on_scope_exit()

    def _on_python_function_entry(self, notification):
        self._on_scope_entry(notification)
        event = notification.event
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

    def _on_syscall_entry(self, notification):
        self._on_scope_entry(notification)
        event_name = notification.event.name[14:]
        print(colored(event_name, "cyan", attrs=["bold"]) + "(", end="")
        first_field = True

        for name, value in notification.event.payload_field.items():
            if not first_field:
                print(", ", end="")

            print(name + " = " + colored(str(value), attrs=["bold"]), end="")
            first_field = False

        print(")", end="")

    def _on_syscall_exit(self, notification):
        if self._last_timestamp is None:
            return

        ret = notification.event["ret"]

        if ret < 0:
            print(colored(" = {}".format(ret), "red", attrs=["bold"]))
        else:
            print(colored(" = {}".format(ret), attrs=["bold"]))

        self._on_scope_exit()

    def _on_python_logging_statement(self, notification):
        self._on_scope_entry(notification)
        print(colored(notification.event["msg"], "magenta", attrs=["bold"]))
        self._on_scope_exit()

    def _port_connected(self, port, other_port):
        subscribe = [bt2.EventNotification]
        self._iterator = port.connection.create_notification_iterator(subscribe)
        return True

    def _consume(self):
        notification = next(self._iterator)
        event_name = notification.event.name
        is_syscall_getpid = event_name.endswith("getpid")

        if event_name == "lttng_python:event":
            self._on_python_logging_statement(notification)
        elif event_name.startswith("syscall_entry") and not is_syscall_getpid:
            self._on_syscall_entry(notification)
        elif event_name.startswith("syscall_exit") and not is_syscall_getpid:
            self._on_syscall_exit(notification)
        elif event_name == "python:function__entry":
            self._on_python_function_entry(notification)
        elif event_name == "python:function__return":
            self._on_python_function_exit()
        elif event_name == "lttng_ust_cyg_profile_fast:func_entry":
            self._on_native_function_entry(notification)
        elif event_name == "lttng_ust_cyg_profile_fast:func_exit":
            self._on_native_function_exit()


bt2.register_plugin(__name__, "pycon")
