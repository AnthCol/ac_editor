import os
import re
import tkinter as tk

from tkinter     import ttk, PhotoImage, filedialog
from typing      import List
from chlorophyll import CodeView

from classes.file           import File
from classes.database       import Database
from classes.settings       import Settings
from classes.vim_controller import VimController

##########
# Globals
##########
WINDOW_EVENTS = {
    "new"        : lambda event: new(),
    "load"       : lambda event: load(),
    "save"       : lambda event: save(),
    "save_as"    : lambda event: save_as(), 
    "close"      : lambda event: close(), 
    "tab_change" : lambda event: update_title(),
    "vim"        : lambda event: vim(event), 
    "esc"        : lambda event: esc(), 
    "ret"        : lambda event: ret(),
    "back"       : lambda event: back()
}

VIM_CHARS = [
    "<i>", 
    "<h>", 
    "<j>", 
    "<k>", 
    "<l>", 
    "<g>",
    "<w>",
    "<q>",
    "<Key-colon>",
    "<Key-exclam>",
    "<Shift-A>", 
    "<Shift-G>",
    "<Shift-asciicircum>", 
    "<Shift-dollar>",
    "0", 
    "1", 
    "2", 
    "3", 
    "4",
    "5", 
    "6", 
    "7", 
    "8", 
    "9"
]

VIM_REGEX = {
    "[0-9]*h" : lambda: h(),
    "[0-9]*j" : lambda: j(),
    "[0-9]*k" : lambda: k(),
    "[0-9]*l" : lambda: l(),
    "i"       : lambda: i(),
    "A"       : lambda: A(),
    "\\^"     : lambda: hat(),
    "\\$"     : lambda: dollar(), 
    ":w"      : lambda: w(),
    ":q"      : lambda: q(save=True), 
    ":wq"     : lambda: wq(), 
    ":q!"     : lambda: q(save=False), 
    "gg"      : lambda: gg(),
    "G"       : lambda: G()
}

# Global GUI state (I don't like it either)
window = tk.Tk()
settings = Settings()
database = Database()
vim_status = VimController(ttk.Label(window, anchor="w"))
files : List[File] = []
codeviews : List[CodeView] = []
notebook = ttk.Notebook(window)


############
# Functions
############
def bind_codeview(codeview):
    for char in VIM_CHARS:
        codeview.bind(char, WINDOW_EVENTS["vim"])
    codeview.bind("<Escape>", WINDOW_EVENTS["esc"])
    codeview.bind("<Return>", WINDOW_EVENTS["ret"])
    codeview.bind("<BackSpace>", WINDOW_EVENTS["back"])

def make_codeview():
    global notebook, settings
    frame = ttk.Frame(notebook)
    codeview = CodeView(frame,
                        insertwidth=10,
                        color_scheme=settings.colour,
                        font=(settings.font_type, settings.font_size))
    codeview.pack(fill="both", expand=True)
    return (codeview, frame)


def fill_codeview(codeview, file):
    failed = False
    content = file.content
    if file.is_unsaved == False:
        try:
            with open(file.path) as f:
                content = f.read()
        except Exception as e:
            tk.messagebox.showerror("Error", "Invalid file type.")
            failed = True
    if not failed:
        codeview.insert(tk.END, content)


def determine_name():
    global files
    values = []
    for f in files:
        if f.is_unsaved:
            values.append(int(f.name.split()[1]))
    values.sort()
    count = 1
    for v in values:
        if v != count: 
            break
        count += 1
    return "New " + str(count)

def determine_rank():
    global files 
    return len(files) + 1

def new():
    file = File(path=None, 
                name=determine_name(),
                rank=determine_rank(),
                content=None,
                is_unsaved=True) 
    add_file(file)
    show_last()

def update_files():
    global files, codeviews
    for rank in range(len(files)):
        f = files[rank]
        if f.is_unsaved:
            f.content = codeview_contents(codeviews[rank])
        f.rank = rank + 1

def add_file(file):
    global files, codeviews, notebook
    codeview, frame = make_codeview()
    fill_codeview(codeview, file)
    bind_codeview(codeview)
    files.append(file)
    codeviews.append(codeview)
    notebook.add(frame, text=file.name)

def end():
    global window, database, files, settings
    update_files()
    database.close([f for f in files], settings)
    window.destroy()

def show_last():
    global notebook
    notebook.select(notebook.index("end") - 1)

def update_title(file):
    global window
    title = file.name if file.is_unsaved else file.path
    window.title("ac_editor - " + title)

def make_icon(path):
    return PhotoImage(file=path)

def load():
    global notebook
    path = filedialog.askopenfilename()
    if path != "":
        name = os.path.basename(path)
        file = File(path=path,
                    name=name,
                    rank=determine_rank(),
                    content=None,
                    is_unsaved=False)        
        add_file(file)
        show_last()

def current_index():
    global notebook
    return notebook.index(notebook.select())

def save():
    global files, codeviews
    index = current_index()
    file = files[index]
    if file.is_unsaved:
        save_as()
    else:
        with open(file.path, "w") as f:
            f.write(codeview_contents(codeviews[index]))

def save_as():
    global files, codeviews, notebook
    path = filedialog.asksaveasfilename()
    if path == "":
        return
    index = current_index()
    old_file = files[index]
    new_file = File(path=path,
                    name=os.path.basename(path),
                    rank=old_file.rank,
                    content="",
                    is_unsaved=False)
    files[index] = new_file
    notebook.tab(index, text=new_file.name)

    with open(path, "w") as f:
        f.write(codeview_contents(codeviews[index]))
    update_title()

def update_title():
    global files, window
    index = current_index()
    file = files[index]
    title = file.name if file.is_unsaved else file.path
    window.title("ac_editor - " + title)

def codeview_contents(codeview):
    return codeview.get("1.0", "end-1c")

def close():
    global files, notebook, codeviews
    index = current_index()
    file = files[index]
    content = codeview_contents(codeviews[index])
    save = False
    if file.is_unsaved and content != "":
        save = tk.messagebox.askyesnocancel("Save File", "Do you want to save this file?")
    # Returns None if cancel
    if save == True:
        save_as()
    elif save == False:
        remove_file(index)

def remove_file(index):
    global files, codeviews, notebook
    del codeviews[index]
    del files[index]
    notebook.forget(index)

def is_valid_vim(command):
    for regex in VIM_REGEX:
        if re.match(regex, command):
            return (True, regex)
    return (False, None)

def process_vim(command):
    global vim_status
    values = is_valid_vim(command)
    valid = values[0]
    regex = values[1] 
    if valid:
        VIM_REGEX[regex]()
        vim_status.reset_buffers()
    
    # Returning "break" prevents default behaviour
    return "break" if valid else None

# Called whenever any of the valid vim characters are pressed
def vim(event=None):
    global vim_status
    vim_status.append_buffer(event.char)
    vim_status.update_display()
    return process_vim(vim_status.command_buffer)

########################
# Vim Related Functions
########################
def esc():
    global vim_status
    vim_status.switch_normal()

def ret():
    global vim_status
    process_vim(vim_status.command_buffer)

def back(event=None):
    global vim_status
    vim_status.delete_char()

def current_codeview():
    global codeviews
    return codeviews[current_index()]

def parse_buffer():
    global vim_status
    if len(vim_status.command_buffer) == 1:
        return 1
    parts = re.split('h|j|k|l', vim_status.command_buffer)
    return str(parts[0])

######################
# VIM_REGEX functions
######################
def h():
    codeview = current_codeview()
    amount = parse_buffer()
    codeview.mark_set("insert", f"insert-{amount} c")

def j():
    codeview = current_codeview()
    amount = parse_buffer()
    codeview.mark_set("insert", f"insert+{amount} l")

def k():
    codeview = current_codeview()
    amount = parse_buffer()
    codeview.mark_set("insert", f"insert-{amount} l")

def l():
    codeview = current_codeview()
    amount = parse_buffer()
    codeview.mark_set("insert", f"insert+{amount} c")

def i():
    global vim_status
    vim_status.switch_insert()

def A():
    dollar()
    i()

def hat():
    codeview = current_codeview()
    codeview.mark_set("insert", "insert linestart")

def dollar():
    codeview = current_codeview()
    codeview.mark_set("insert", "insert lineend")

def gg():
    codeview = current_codeview()
    codeview.mark_set("insert", "1.0")

def G():
    codeview = current_codeview()
    codeview.mark_set("insert", "end")
    hat()

def w():
    save()

def q(save):
    if save:
        close()
    else:
        remove_file()

def wq():
    save()




#######
# Main
#######
if __name__ == "__main__":
    window.title("ac_editor")
    icon = make_icon("src/assets/logo.png")
    window.wm_iconphoto(False, icon)
    ttk.Style(window).theme_use("clam")

    vim_status.update_display()
    notebook.grid(row=0, column=0, sticky="nsew")
    vim_status.label_grid()
    window.grid_rowconfigure(0, weight=1)
    window.grid_columnconfigure(0, weight=1)
    window.protocol("WM_DELETE_WINDOW", lambda: end())

    window.bind("<Control-s>", WINDOW_EVENTS["save"])
    window.bind("<Control-Alt-s>", WINDOW_EVENTS["save_as"])
    window.bind("<Control-q>", WINDOW_EVENTS["close"])
    window.bind("<Control-o>", WINDOW_EVENTS["load"])
    window.bind("<Control-n>", WINDOW_EVENTS["new"])
    notebook.bind("<<NotebookTabChanged>>", WINDOW_EVENTS["tab_change"])

    data = database.load_settings()
    if data:
        colour, font_type, font_size = data
        settings.colour    = colour
        settings.font_type = font_type
        settings.font_size = font_size

    db_files = database.load_files()

    if len(db_files) == 0:
        file = File(path=None, 
                    name="New 1",
                    rank=1,
                    content=None,
                    is_unsaved=True)
        add_file(file)
    else:
        for db_file in db_files:
            add_file(db_file)

    show_last()
    window.mainloop()
