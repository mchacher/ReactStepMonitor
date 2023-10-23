import logging
import time
import signal
import threading
import rsmaster as rs
import reactstepmonitor_config as rc
import os

from prompt_toolkit import PromptSession, prompt
from prompt_toolkit import print_formatted_text as print
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.completion import WordCompleter

commands = {
    'exit': 'exit React Prompt',
    'list workout': 'list the workout in the react sync device', 
    'help': 'show this help',
    'clear': 'clear the screen of the terminal'
}

command_completer = WordCompleter(commands.keys())


from prompt_toolkit.styles import Style

style = Style.from_dict({
    # User input (default text).
    '': '#000000',
    # Prompt.
    'default': 'bold blue',
})

class ReactPrompt:


    def __init__(self):
        self.exit_now = False
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
        print("")
        while not self.rsm.is_connected():
            print(".")
            time.sleep(1)
        while not self.exit_now:

            message = [('class:default', 'ReactStudioPrompt % ')]
            command = session.prompt(message, key_bindings=self.bindings, completer=command_completer,style=style)
            if command == "exit":
                self.stop()
            elif command == "list workout":
                self.rsm.send_list_workout()
            elif command == "help":
                print("")
                sorted_commands = sorted(commands.items())
                max_command_length = max(len(command) for command, _ in sorted_commands)
                for command, description in sorted_commands:
                    print(f'{command.ljust(max_command_length)} | {description}')
                print("")
            elif command == "clear":
                os.system('clear')

    def worker_task(self):
        while not self.exit_now:
            if not self.rsm.is_connected():
                self.rsm.disconnect()
                self.rsm.connect()
            time.sleep(1)


    def start(self):
        if not (self.worker.is_alive()):
            self.worker.start()

    def stop(self):
        self.rsm.stop_communication()
        self.exit_now = True
        if self.worker.is_alive():
            self.worker.join()
            logging.info("%s is stopped", self.worker.name)

if __name__ == "__main__":
    if rc.ReactStepMonitorConfig().logging_level == "info":
        logging_level = logging.INFO
    else:
        logging_level = logging.DEBUG
    # # print python lib version
    # logging.basicConfig(
    #     level=logging_level, format="%(asctime)s %(message)s", datefmt="%b %d %H:%M:%S"
    # )
    log_file = "log.txt"  # Replace with your desired log file name
    logging.basicConfig(
    level=logging.INFO,  # Set the desired log level
    format="%(asctime)s %(message)s",  # Define log message format
    datefmt="%b %d %H:%M:%S",  # Define date format
    filename=log_file,  # Set the log file name
    filemode="w"  # Set the file mode (overwrite if it exists)
    )
    logging.info("----------------------------------------------")
    logging.info(
        "React Step Monitor Python Library: %s", rs.RSMaster.get_python_lib_version()
    )
    logging.info("----------------------------------------------")
    rsprompt = ReactPrompt()
    rsprompt.start()