import logging
import time
import signal
import threading
import rsmaster as rs
import reactstepmonitor_config as rc
import os

from prompt_toolkit import PromptSession
from prompt_toolkit import print_formatted_text as print
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit import prompt

command_handlers = [
    ('exit', 'exit React Prompt', 'stop', False),
    ('list workout', 'list the workout in the react sync device', 'send_list_workout', False),
    ('help', 'show this help', 'show_help', False),
    ('clear', 'clear the screen of the terminal', 'clear_screen', False),
    ('del', 'delete a file pass as argument', 'delete_command', True)
]

command_completer = WordCompleter([command[0] for command in command_handlers])

from prompt_toolkit.styles import Style

style = Style.from_dict({
    # User input (default text).
    '': '#000000',
    # Prompt.
    'default': 'bold blue',
})

class ReactPrompt:

    def exit_gracefully(self, signum, frame):
        """handle system message CTRL+C to properly stop threads and exit"""
        self.stop()
        logging.info("Exit")

    def __init__(self):
        self.exit_now = False
        signal.signal(signal.SIGTERM, self.exit_gracefully)
        signal.signal(signal.SIGINT, self.exit_gracefully)
        config = rc.ReactStepMonitorConfig()
        self.worker = threading.Thread(
            target=self.worker_task, name="React Step Monitor worker thread"
        )
        # activate RS Master
        self.rsm = rs.RSMaster()
        self.rsm.connect()

        session = PromptSession()
        self.bindings = KeyBindings()

        # Use a class method to define the 'c-t' binding
        @self.bindings.add('c-c')
        def _(event):
            event.app.exit()
            self.stop()
        print("")
        print("--------------------------------------")
        print("    React Studio - prompt version    ")
        print("--------------------------------------")
        print("Connecting to React Sync ...", end='')
        while (not self.rsm.is_connected()) and (not self.exit_now):
            print(".", end='')
            time.sleep(1)
        print(" ok")
        print("")
        while not self.exit_now:
            message = [('class:default', 'ReactStudioPrompt % ')]
            command = session.prompt(
                message, key_bindings=self.bindings, completer=command_completer, style=style
            )

            # Find the handler and execute it
            for name, description, handler_name, has_argument in command_handlers:
                if command.startswith(name):
                    if has_argument:
                        argument = command[len(name):].strip()
                        handler = getattr(self, handler_name, None)
                        if handler and argument:
                            handler(argument)
                        else:
                            print(f"Invalid usage. Usage: {name} [file_name]")
                    else:
                        handler = getattr(self, handler_name, None)
                        if handler:
                            handler()
                        else:
                            print(f"Handler for '{name}' not found.")
                    break
            else:
                print(f"Unknown command: {command}")

    def stop(self):
        self.rsm.stop_communication()
        self.exit_now = True
        if self.worker.is_alive():
            self.worker.join()
            logging.info("%s is stopped", self.worker.name)

    def worker_task(self):
        while not self.exit_now:
            if not self.rsm.is_connected():
                self.rsm.disconnect()
                self.rsm.connect()
            time.sleep(1)

    def show_help(self):
        print('')
        for name, description, _, _ in command_handlers:
            print(f'{name.ljust(15)} | {description}')
        print("")

    def clear_screen(self):
        os.system('clear')

    def delete_command(self, argument):
        if argument:
            print(f"Deleting file: {argument}")
            self.rsm.send_delete_file(argument)
        else:
            print(f"Invalid usage. Usage: del [file_name]")

    def send_list_workout(self):
        self.rsm.send_list_workout()


if __name__ == "__main__":
    if rc.ReactStepMonitorConfig().logging_level == "info":
        logging_level = logging.INFO
    else:
        logging_level = logging.DEBUG

    log_file = "log.txt"  # Replace with your desired log file name
    logging.basicConfig(
        level=logging_level,
        format="%(asctime)s %(message)s",
        datefmt="%b %d %H:%M:%S",
        filename=log_file,
        filemode="w"
    )
    logging.info("----------------------------------------------")
    logging.info(
        "React Step Monitor Python Library: %s", rs.RSMaster.get_python_lib_version()
    )
    logging.info("----------------------------------------------")
    rsprompt = ReactPrompt()
