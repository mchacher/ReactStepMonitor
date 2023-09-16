import logging
import time
import signal
import curses
import threading
import rsmaster as rs
import reactstepmonitor_config as rc
import tkinter as tk
from tkinter import font, messagebox, scrolledtext, ttk, filedialog
import queue
import asyncio


# Define constants for file extensions
SESSION_EXTENSION_FILENAME = "*.ses"
WORKOUT_EXTENSION_FILENAME = "*.wkt"

class QueueHandler(logging.Handler):
    """Class to send logging records to a queue

    It can be used from different threads
    """

    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        message = self.format(record)
        self.log_queue.put(message)

class ReactStepToolbox(tk.Tk):
    
    def __init__(self):
        """ constructor """
        super().__init__()
        self.title("ReactStep Toolbox") 
        self.log_queue = queue.Queue()
        self.queue_handler = QueueHandler(self.log_queue)
        formatter = logging.Formatter('%(asctime)s: %(message)s')
        self.queue_handler.setFormatter(formatter)
        logging.getLogger().addHandler(self.queue_handler)
        self.protocol("WM_DELETE_WINDOW", self.__exit_self)
        # # eliminate tear-off menus from the application
        # # as they're not a part of any modern user interface style.
        self.option_add('*tearOff', False)
        self.__create_top_menu()
        self.__create_main_layout()
        self.__layout_widgets()
        self.geometry("1200x1000")
        # self.minsize(1200, 675)
        self.update()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        rw = self.winfo_width()
        rh = self.winfo_height()
        self.geometry(f'{rw}x{rh}+{int((sw-rw)/2)}+{int((sh-rh)/2)-30}')
        # finalize init
        self.__show_welcome_message()
        # launch background worker thread
        self.exit_now = False
        self.worker = threading.Thread(
            target=self.__worker_task, name="ReactStep Toolbox Worker Thread"
        )
        self.worker.daemon = True
        # activate RS Master
        self.rsm = rs.RSMaster()
        self.rsm.connect()
        self.worker.start()
        self.after(10, self.poll_log_queue)
        
    def poll_log_queue(self):
            try:
                record = self.log_queue.get(block=False)
                self.__write_terminal(record)
            except queue.Empty:
                pass
            self.after(10, self.poll_log_queue)  # Schedule the next polling

    def __create_top_menu(self):
        """ create top menu of the toolbox app """
        self.menubar = tk.Menu(self)
        # File menu
        self.menu_file = tk.Menu(self.menubar)
        self.menu_file.add_command(label='Open File', command=self.open_file)  # Add "Open File" option
        self.menu_file.add_command(label='Exit', command=self.__exit_self)
        self.menubar.add_cascade(label='File', menu=self.menu_file)
        self.config(menu=self.menubar)

    def open_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("ReactStep Files", f"{SESSION_EXTENSION_FILENAME} {WORKOUT_EXTENSION_FILENAME} .bin")])
        if file_path:
            self.start_file_transfer(file_path)

    def start_file_transfer(self, file_path):
        """ Start the file transfer and open a progress window """
        self.create_progress_window()
        logging.info("File path: %s", file_path)

        # Start the file transfer in a separate thread
        self.file_transfer_thread = threading.Thread(target=self.perform_file_transfer, args=(file_path,))
        self.file_transfer_thread.start()

    def create_progress_window(self):
        self.progress_window = tk.Toplevel(self)
        self.progress_window.title("File Transfer Progress")
        self.center_window(self.progress_window, 400, 50)

        # Create a progress bar in determinate mode
        self.progress_bar = ttk.Progressbar(self.progress_window, length=300, mode='determinate')
        self.progress_bar.pack(padx=20, pady=20)

    def center_window(self, window, width, height):
        main_frame_x = self.frame_main.winfo_rootx()
        main_frame_y = self.frame_main.winfo_rooty()
        main_frame_width = self.frame_main.winfo_width()
        main_frame_height = self.frame_main.winfo_height()
        window_width = width
        window_height = height
        window_x = main_frame_x + (main_frame_width - window_width) // 2
        window_y = main_frame_y + (main_frame_height - window_height) // 2
        window.geometry(f"{window_width}x{window_height}+{window_x}+{window_y}")

    def perform_file_transfer(self, file_path):
        # Simulate the async file transfer here (replace with your actual logic)
        asyncio.run(self.async_file_transfer(file_path))
        logging.info("File transfer completed.")
        # Close the progress window after the file transfer is complete
        self.progress_window.destroy()

    async def async_file_transfer(self, file_path):
        
        self.rsm.send_workout_file(file_path)
        # Simulate the async file transfer here (replace with your actual logic)
        interval = .05  # Interval for progress update in seconds
        progress_value = 0

        while progress_value < 100:
            progress_value += 10
            self.progress_bar["value"] = progress_value
            await asyncio.sleep(interval)


    
    def __create_main_layout(self):
        """ create main layout with 2 rows, 1 column """
        self.rowconfigure(0, weight=10)
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        self.frame_main = ttk.Frame(self)
        self.frame_main.rowconfigure(0, weight=1)
        self.frame_main.columnconfigure(0, weight=1)

        self.frame_bottom = ttk.Frame(self, borderwidth=15)
        self.frame_bottom.rowconfigure(1, weight=1)
        self.frame_bottom.columnconfigure(0, weight=1)

        self.frame_main.grid(column=0, row=0, rowspan="2", sticky=tk.NSEW)
        self.frame_bottom.grid(column=0, row=1, sticky=tk.NSEW)

    def __layout_widgets(self):
        """ create the HMI (widget creation and layout) of the toolbox app """
        # Main Frame
        self.scrolled_text_rx = scrolledtext.ScrolledText(
            self.frame_main, height=20, state=tk.DISABLED, font=('Courier', 10), wrap=tk.WORD)
        self.scrolled_text_rx.grid(row=0, column=0, sticky=tk.NSEW)
        self.scrolled_text_rx.tag_config('warning', foreground="red")

    def __show_welcome_message(self):
        """ show welcome message """
        welcome_text =\
            """
************************************************************************************
*                                                                                  *
* Welcome to React Tool Box                                                        *
*                                                                                  *
************************************************************************************

"""
        self.__write_terminal(welcome_text)


    def __write_terminal(self, txt, tag=""):
        """ write txt message in the rx text widget """
        self.scrolled_text_rx.configure(state=tk.NORMAL)
        self.scrolled_text_rx.insert(tk.END, txt, tag)
        self.scrolled_text_rx.insert(tk.END, "\n")
        self.scrolled_text_rx.see(tk.END)

    def __worker_task(self):
        while True:
            if not self.rsm.is_connected():
                self.rsm.disconnect()
                self.rsm.connect()
            time.sleep(1)

    def __exit_self(self):
        """ exit application callback """
        self.__exit()

    def __exit_gracefully(self, signum, frame):
        """handle system message CTRL+C to properly stop threads and exit"""
        print("CTRL C")
        self.__exit()

    def __exit(self):
        logging.info("%s is stopped", self.worker.name)
        self.rsm.stop_communication()
        self.destroy()

if __name__ == "__main__":
    if rc.ReactStepMonitorConfig().logging_level == "info":
        logging_level = logging.INFO
    else:
        logging_level = logging.DEBUG
    # print python lib version
    logging.basicConfig(
        level=logging_level, format="%(asctime)s %(message)s", datefmt="%b %d %H:%M:%S"
    )
    logging.info("----------------------------------------------")
    logging.info(
        "React Step Monitor Python Library: %s", rs.RSMaster.get_python_lib_version()
    )
    logging.info("----------------------------------------------")
    rstoolbox = ReactStepToolbox()
    rstoolbox.mainloop()