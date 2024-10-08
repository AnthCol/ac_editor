import os
import re
import tkinter as tk

from tkinter         import ttk, PhotoImage, filedialog
from typing          import List
from chlorophyll     import CodeView
from pygments.util   import ClassNotFound
from pygments.lexers import TextLexer, get_lexer_for_filename

from .classes.file           import File
from .classes.database       import Database
from .classes.settings       import Settings
from .classes.vim_controller import VimController

############
# Constants
############
WINDOW_EVENTS = {
    "new"        : lambda event: new(),
    "load"       : lambda event: load(),
    "save"       : lambda event: save(),
    "save_as"    : lambda event: save_as(), 
    "close"      : lambda event: close(), 
    "tab_change" : lambda event: update_display(current_index()),
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
    "([1-9]+[0-9]*)*h" : lambda: h(),
    "([1-9]+[0-9]*)*j" : lambda: j(),
    "([1-9]+[0-9]*)*k" : lambda: k(),
    "([1-9]+[0-9]*)*l" : lambda: l(),
    "i"   : lambda: i(),
    "A"   : lambda: A(),
    "\\^" : lambda: hat(),
    "\\$" : lambda: dollar(), 
    "gg"  : lambda: gg(),
    "G"   : lambda: G()
}

# Pretty brutal, but basically every non-special vim key is being assigned to a function
# that will check which mode the program is in to determine if the keypress is valid
NON_VIM_CHARS = [
    '<a>', '<b>', '<c>', '<d>', '<e>', '<f>', '<g>', '<m>', 
    '<p>', '<r>', '<t>', '<u>', '<v>', '<w>', '<x>', '<y>', '<z>',
    '<B>', '<C>', '<D>', '<E>', '<F>', '<H>', '<I>', '<J>', '<K>', '<L>', '<M>', '<N>', 
    '<O>', '<P>', '<Q>', '<R>', '<S>', '<T>', '<U>', '<V>', '<W>', '<X>', '<Y>', '<Z>',
    '<less>', '<comma>', '<greater>', '<period>', '<question>', '<slash>', '<semicolon>', '<quotedbl>', 
    '<apostrophe>', '<braceleft>', '<bracketleft>', '<bracketright>', '<braceright>', '<equal>', '<plus>', 
    '<minus>', '<underscore>', '<parenleft>', '<parenright>', '<asterisk>', '<ampersand>', '<percent>', 
    '<numbersign>', '<at>', '<asciitilde>', '<grave>'
]

###################################################
# Global GUI State
# Despite general bad practice, seemed 
# to be my best option here. In hindsight, making
# this project in a different language, or maybe
# with a different GUI API would have been better
# but I'm in too deep for that now. 
###################################################
window = tk.Tk()
settings = Settings()
database = Database()
vim_label = ttk.Label(window, anchor="w")
vim_controller = VimController(ttk.Label(window, anchor="w"))
files : List[File] = []
codeviews : List[CodeView] = []
notebook = ttk.Notebook(window)

###################
# Closing function
###################
def end():
    global window, database, files, settings
    update_files()
    database.close([f for f in files], settings)
    window.quit()
    window.destroy()


###################
# Codeview helpers
###################
def bind_codeview(codeview):
    for char in NON_VIM_CHARS: 
        codeview.bind(char, lambda event: normal_key())

    for char in VIM_CHARS: 
        codeview.bind(char, WINDOW_EVENTS["vim"])

    codeview.bind("<Escape>", WINDOW_EVENTS["esc"])
    codeview.bind("<Return>", WINDOW_EVENTS["ret"])
    codeview.bind("<BackSpace>", WINDOW_EVENTS["back"])


def make_codeview(file):
    global notebook, settings
    frame = ttk.Frame(notebook)
    codeview = CodeView(frame,
                        color_scheme=settings.colour,
                        font=(settings.font_type, settings.font_size),
                        lexer=determine_lexer(file))
    # Jank has to be set after constructor for some reason...
    codeview.config(insertwidth=7)
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

###########################
# General helper functions
###########################
def determine_lexer(file):
    lexer = TextLexer
    if not file.is_unsaved:
        try:
            lexer = get_lexer_for_filename(file.name)
        # For whatever reason, this gives an error at program exit, but everything works fine
        # TypeError doesn't inherit from BaseException, but it gets caught and used....
        # Leaving it for now, FIXME in the future. 
        except ClassNotFound:
            lexer = TextLexer  
    return lexer

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

def update_files():
    global files, codeviews
    for rank in range(len(files)):
        f = files[rank]
        if f.is_unsaved:
            f.content = codeview_contents(codeviews[rank])
        f.rank = rank + 1

def codeview_contents(codeview):
    return codeview.get("1.0", "end-1c")

def make_icon(path):
    return PhotoImage(file=path)

####################
# Aesthetic helpers
####################
def show_last():
    global notebook
    notebook.select(notebook.index("end") - 1)

def update_display(index):
    global vim_controller, codeviews
    update_title()
    vim_controller.update_display(index)
    codeviews[index].focus_set()

def update_title():
    global files, window
    index = current_index()
    file = files[index]
    title = file.name if file.is_unsaved else file.path
    window.title("ac_editor - " + title)

##########################
# File handling functions
##########################
def add_file(file):
    global files, codeviews, notebook, vim_controller
    codeview, frame = make_codeview(file)
    fill_codeview(codeview, file)
    bind_codeview(codeview)
    files.append(file)
    codeviews.append(codeview)
    notebook.add(frame, text=file.name)
    vim_controller.new_buffer()
    vim_controller.update_display(current_index())

def new():
    file = File(path=None, 
                name=determine_name(),
                rank=determine_rank(),
                content=None,
                is_unsaved=True) 
    add_file(file)
    show_last()

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
    # This is kind of bad
    # if this is called we ignore the keypress 
    # I think something a bit more low level than tkinter would 
    # have been better in hindsight
    return "break"

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

def close():
    global files, notebook, codeviews
    index = current_index()
    file = files[index]
    content = codeview_contents(codeviews[index])
    ask = (file.is_unsaved and content != "") or (file.has_changed)
    answer = False
    if ask:
        answer = tk.messagebox.askyesnocancel("Save File", "Do you want to save this file?")
    # Returns None if cancel
    if answer == True:
        save()
        remove_file(index)
    elif answer == False:
        remove_file(index)

def remove_file(index):
    global files, codeviews, notebook, vim_controller
    del codeviews[index]
    del files[index]
    del vim_controller.buffers[index]
    notebook.forget(index)
    if len(files) == 0:
        new()

###################################
# Vim command processing functions
###################################
def is_valid_vim(command):
    for regex in VIM_REGEX:
        if re.fullmatch(regex, command):
            return (True, regex)
    return (False, None)

def process_vim(command):
    global vim_controller
    values = is_valid_vim(command)
    valid = values[0]
    regex = values[1] 
    if valid:
        VIM_REGEX[regex]()
        vim_controller.reset_buffers(current_index()) 
    # Returning "break" prevents default behaviour
    return "break" if valid else None

# Called whenever any of the valid vim characters are pressed
# This excludes special ones like enter, backspace and escape.
def vim(event=None):
    global vim_controller, files
    index = current_index()
    if not vim_controller.in_insert(index):
        vim_controller.append_buffer(event.char, index)
        vim_controller.update_display(index)
        process_vim(vim_controller.current_command(index))    
        return "break"
    # If in insert mode, we want to treat the character normally
    # in this case, the file has changed, so we set that 
    files[index].has_changed = True
    return None

#############################################################
# Key handling functions (keys that are not vim-significant)
#############################################################
def normal_key():
    global vim_controller
    normal = vim_controller.in_normal(current_index())
    return "break" if normal else None

def esc():
    global vim_controller
    index = current_index()
    vim_controller.switch_normal(index)

def ret():
    global vim_controller
    index = current_index()
    file_commands = {
        ":w"  : lambda: w(),
        ":q"  : lambda: q(save=True), 
        ":wq" : lambda: wq(), 
        ":q!" : lambda: q(save=False)
    }
    command = vim_controller.current_command(index)
    for c in file_commands:
        if re.fullmatch(c, command):
            file_commands[c]()
            if not c.startswith(":q"):
                vim_controller.reset_buffers(index)
            return "break"

    result = process_vim(vim_controller.current_command(index))
    if vim_controller.in_normal(index):
        return "break"
    else:
        return result


def back(event=None):
    global vim_controller
    index = current_index()
    if vim_controller.in_normal(index):
        vim_controller.delete_char(index)
        return "break"
    return None

#####################################
# Functions for getting current info
#####################################
def current_index():
    global notebook
    return notebook.index(notebook.select())

def current_codeview():
    global codeviews
    return codeviews[current_index()]

def parse_buffer():
    global vim_controller
    index = current_index()
    buffer = vim_controller.current_command(index)
    if len(buffer) == 1:
        return 1
    parts = re.split('h|j|k|l', buffer)
    return str(parts[0])


######################
# VIM_REGEX functions
######################
def h():
    codeview = current_codeview()
    amount = parse_buffer()
    codeview.mark_set("insert", f"insert-{amount} c")
    codeview.see("insert")

def j():
    codeview = current_codeview()
    amount = parse_buffer()
    codeview.mark_set("insert", f"insert +{amount} l")
    codeview.see("insert")

def k():
    codeview = current_codeview()
    amount = parse_buffer()
    codeview.mark_set("insert", f"insert -{amount} l")
    codeview.see("insert")

def l():
    codeview = current_codeview()
    amount = parse_buffer()
    codeview.mark_set("insert", f"insert+{amount} c")
    codeview.see("insert")

def i():
    global vim_controller
    index = current_index()
    vim_controller.switch_insert(index)

def A():
    dollar()
    i()

def hat():
    codeview = current_codeview()
    codeview.mark_set("insert", "insert linestart")
    codeview.see("insert")

def dollar():
    codeview = current_codeview()
    codeview.mark_set("insert", "insert lineend")
    codeview.see("insert")

def gg():
    codeview = current_codeview()
    codeview.mark_set("insert", "1.0")
    codeview.see("insert")

def G():
    codeview = current_codeview()
    codeview.mark_set("insert", "end")
    hat()
    codeview.see("insert")

def w():
    save()
    files[current_index()].has_changed = False

def q(save):
    if save:
        close()
    else:
        remove_file(current_index())

def wq():
    global files
    save()
    files[current_index()].has_changed = False
    close()

#######
# Main
#######
if __name__ == "__main__":
    window.title("ac_editor")
    icon = make_icon("src/assets/logo.png")
    window.wm_iconphoto(False, icon)
    ttk.Style(window).theme_use("clam")

    notebook.grid(row=0, column=0, sticky="nsew")
    vim_controller.label_grid()
    window.grid_rowconfigure(0, weight=1)
    window.grid_columnconfigure(0, weight=1)
    window.protocol("WM_DELETE_WINDOW", lambda: end())

    window.bind("<Control-s>", WINDOW_EVENTS["save"])
    window.bind("<Control-Alt-s>", WINDOW_EVENTS["save_as"])
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
