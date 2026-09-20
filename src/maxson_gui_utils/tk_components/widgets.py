from __future__ import annotations
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from pathlib import Path

import pyhabitat

#from .functions import browse_entry_filepath, copy_entry_filepath

def create_path_entry(root: tk.Tk,
    control_frame: ttk.Frame, 
    path_var: tk.StringVar,
    path_name_str:str = "Input Path"
)->None:

    # === Row : File Selection ===
    file_selection_frame = ttk.Frame(control_frame)

    # risk of speficity, it should just be 'next avaiable row, expand by one'
    file_selection_frame.grid(row=0, column=0, columnspan=3, padx=0, pady=(2, 4), sticky='ew')

    ttk.Label(file_selection_frame, text=f"{path_name_str}:").pack(side=tk.LEFT, padx=(0, 3))
    entry = ttk.Entry(file_selection_frame, textvariable=path_var)
    entry.pack(side=tk.LEFT, fill='x', expand=True, padx=3)
    ttk.Button(file_selection_frame, text="Browse...", command=lambda: browse_entry_filepath(path_var), width=10).pack(side=tk.LEFT, padx=(3, 3))
    ttk.Button(file_selection_frame, text="Copy Path", command=lambda: copy_entry_filepath(path_var,root), width=10).pack(side=tk.LEFT, padx=(0, 0))

def copy_entry_filpath(path_var: tk.StringVar,root:tk.Tk):
    path_to_copy = path_var.get()
    if path_to_copy:
        try:
            root.clipboard_clear()
            root.clipboard_append(path_to_copy)
            messagebox.showinfo("Copied", "Path copied to clipboard.")
        except tk.TclError as e:
            messagebox.showerror("Copy Error", f"Clipboard access blocked: {e}")
    else:
        messagebox.showwarning("Copy Failed", "Path field is empty.")


def browse_entry_filepath(path_var:tk.StringVar):
    if self.path_var.get():
        initialdir = str(Path(pdf_var.get()).parent)
    elif pyhabitat.is_msix():
        initialdir = str(Path.home())
    else:
        initialdir = str(Path.cwd())

    file_path = filedialog.askopenfilename(
        initialdir=initialdir,
        #defaultextension=".pdf",
        filetypes=[("All files", "*.*")]
    )
    if file_path:
        path_var.set(get_friendly_path(file_path))

def get_friendly_path(full_path: str) -> str:
    """
    
    Returns an absolute path on Windows, or a tilde-shortened path on Linux.
    Ensures system calls don't break on Windows while maintaining Linux UX.
    
    """
    try:
        p = Path(full_path).resolve()
    except Exception:
        # If resolution fails (e.g. permission error), use the raw path
        p = Path(full_path)

    if pyhabitat.on_windows():
        return str(p)
    
    # Linux/macOS: Try to provide the friendly tilde shortcut
    try:
        home = Path.home()
        # is_relative_to was added in Python 3.9
        if hasattr(p, "is_relative_to") and p.is_relative_to(home):
            return f"~{os.sep}{p.relative_to(home)}"
        elif str(p).startswith(str(home)):
            # Fallback for Python < 3.9
            return str(p).replace(str(home), "~", 1)
    except Exception:
        # If home directory can't be determined, return absolute path
        pass
        
    return str(p)
