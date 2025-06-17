import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox

selected_folders = []

def select_folders():
    global selected_folders
    parent_folder = filedialog.askdirectory(title="Select Parent Folder")
    if not parent_folder:
        return
    selected_folders = [
        os.path.join(parent_folder, folder)
        for folder in os.listdir(parent_folder)
        if os.path.isdir(os.path.join(parent_folder, folder))
    ]
    messagebox.showinfo("Folders Selected", f"{len(selected_folders)} folders selected.")

def convert_to_dcm():
    if not selected_folders:
        messagebox.showerror("No Folders", "Please select folders first.")
        return

    output_dir = filedialog.askdirectory(title="Select Output Directory")
    if not output_dir:
        return

    total = 0
    for folder in selected_folders:
        folder_name = os.path.basename(folder)
        output_folder = os.path.join(output_dir, folder_name)
        os.makedirs(output_folder, exist_ok=True)

        for file in os.listdir(folder):
            file_path = os.path.join(folder, file)
            if os.path.isfile(file_path):
                new_name = os.path.splitext(file)[0] + ".dcm"
                new_path = os.path.join(output_folder, new_name)
                shutil.copy2(file_path, new_path)
                total += 1

    messagebox.showinfo("Done", f"✅ Converted {total} files from {len(selected_folders)} folders.")

# GUI Setup
root = tk.Tk()
root.title("DICOM File Converter")
root.geometry("400x200")
root.resizable(False, False)

tk.Label(root, text="DICOM Extension Converter", font=("Arial", 16, "bold")).pack(pady=10)

btn_select = tk.Button(root, text="1️⃣ Select Folders", font=("Arial", 12), command=select_folders)
btn_select.pack(pady=10)

btn_convert = tk.Button(root, text="2️⃣ Convert to .dcm", font=("Arial", 12), command=convert_to_dcm)
btn_convert.pack(pady=10)

root.mainloop()
