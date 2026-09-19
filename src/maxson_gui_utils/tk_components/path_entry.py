from __future__ import annotations
from tkinter import filedialog, ttk, messagebox
def create_path_entry(control_frame:ttk.Frame, path_name_str:str = "Path")->None:
    ## --- Control Frame (Top) ---
    #control_frame = ttk.Frame(self.root, padding=(4, 2, 4, 2))
    #control_frame.pack(fill='x', pady=(2, 2))

    # === Row : File Selection ===
    file_selection_frame = ttk.Frame(control_frame)

    # risk of speficity, it should just be 'next avaiable row, expand by one'
    file_selection_frame.grid(row=0, column=0, columnspan=3, padx=0, pady=(2, 4), sticky='ew')

    ttk.Label(file_selection_frame, text=f"{path_name_str}:").pack(side=tk.LEFT, padx=(0, 3))
    entry = ttk.Entry(file_selection_frame, textvariable=self.pdf_path)
    entry.pack(side=tk.LEFT, fill='x', expand=True, padx=3)
    ttk.Button(file_selection_frame, text="Browse...", command=self._select_pdf, width=10).pack(side=tk.LEFT, padx=(3, 3))
    ttk.Button(file_selection_frame, text="Copy Path", command=self._copy_pdf_path, width=10).pack(side=tk.LEFT, padx=(0, 0))

