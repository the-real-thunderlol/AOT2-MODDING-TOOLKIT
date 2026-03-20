import tkinter as tk
from tkinter import filedialog

tk.Tk().withdraw()


def select_file(filter_str=None):
    filetypes = [("All Files", "*.*")]
    if filter_str:
        filetypes = filter_str + filetypes
    return filedialog.askopenfilename(filetypes=filetypes)


def select_folder():
    return filedialog.askdirectory()
