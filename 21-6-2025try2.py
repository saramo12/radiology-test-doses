import os
import re
import csv
import customtkinter as ctk
from tkinter import filedialog
from datetime import datetime
from collections import defaultdict

CSV_FILE = "radiation_dose.csv"

def extract_dose_info(text):
    name = re.search(r"Patient: (.+?) \(", text)
    date = re.search(r"Content Date/Time:\s+(\d{4}-\d{2}-\d{2})", text)
    dlp = re.search(r"CT Dose Length Product Total:\s*([\d.]+)\s*mGy\.cm", text)
    ctdi = re.search(r"Mean CTDIvol:\s*([\d.]+)\s*mGy", text)

    name = name.group(1).strip() if name else "Unknown"
    date = date.group(1).strip() if date else "0000-00-00"
    dlp = float(dlp.group(1)) if dlp else 0.0
    ctdi = float(ctdi.group(1)) if ctdi else 0.0
    effective_dose = round(dlp * 0.014, 2)  # For chest

    year = date.split("-")[0]
    return name, date, year, ctdi, dlp, effective_dose

def process_folder(folder_path):
    patient_data = defaultdict(lambda: defaultdict(lambda: {"DLP": 0.0, "CTDIvol": 0.0, "EffDose": 0.0}))
    for file in os.listdir(folder_path):
        if file.endswith(".txt"):
            with open(os.path.join(folder_path, file), encoding="utf-8") as f:
                text = f.read()
                name, date, year, ctdi, dlp, eff = extract_dose_info(text)
                patient_data[name][year]["DLP"] += dlp
                patient_data[name][year]["CTDIvol"] += ctdi
                patient_data[name][year]["EffDose"] += eff
    return patient_data

def save_to_csv(data):
    with open(CSV_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Patient Name", "Year", "Total CTDIvol", "Total DLP", "Total Effective Dose (mSv)"])
        for name in data:
            for year in data[name]:
                row = data[name][year]
                writer.writerow([name, year, round(row["CTDIvol"], 2), round(row["DLP"], 2), round(row["EffDose"], 2)])

def display_results(data):
    for widget in result_frame.winfo_children():
        widget.destroy()
    headers = ["Patient Name", "Year", "CTDIvol", "DLP", "Effective Dose (mSv)"]
    for col, head in enumerate(headers):
        ctk.CTkLabel(result_frame, text=head, font=ctk.CTkFont(weight="bold")).grid(row=0, column=col, padx=5, pady=5)

    row_num = 1
    for name in data:
        for year in data[name]:
            row = data[name][year]
            values = [name, year, round(row["CTDIvol"], 2), round(row["DLP"], 2), round(row["EffDose"], 2)]
            for col, val in enumerate(values):
                ctk.CTkLabel(result_frame, text=str(val)).grid(row=row_num, column=col, padx=5, pady=3)
            row_num += 1

def select_folder():
    folder = filedialog.askdirectory()
    if folder:
        data = process_folder(folder)
        save_to_csv(data)
        display_results(data)

# واجهة التطبيق
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")
root = ctk.CTk()
root.title("CT Dose Report Processor")
root.geometry("800x600")

ctk.CTkLabel(root, text="📂 Select Folder with CT Reports", font=ctk.CTkFont(size=18)).pack(pady=20)
ctk.CTkButton(root, text="Select Folder", command=select_folder).pack()

result_frame = ctk.CTkFrame(root)
result_frame.pack(pady=20, fill="both", expand=True)

root.mainloop()
