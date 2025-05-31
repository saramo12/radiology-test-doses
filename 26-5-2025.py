import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import pydicom
import os
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")
CSV_FILE = "rad.csv"
HL7_DIR = "hl7_messages"
os.makedirs(HL7_DIR, exist_ok=True)

all_data = []

def convert_to_hl7(ds, msv):
    name = str(getattr(ds, "PatientName", "Unknown"))
    date = getattr(ds, "StudyDate", "00000000")
    ctdi = float(getattr(ds, "CTDIvol", 0))
    dlp = float(getattr(ds, "DLP", 0))
    gender = getattr(ds, "PatientSex", "")
    dob = getattr(ds, "PatientBirthDate", "")
    study_id = getattr(ds, "StudyID", "")
    accession = getattr(ds, "AccessionNumber", "")

    return f"""MSH|^~\&|CTApp|Hospital|PACS|Hospital|{date}||ORU^R01|MSG00001|P|2.3
PID|||{name}||{dob}|{gender}||
OBR|||{study_id}^{accession}|||CT
OBX|1|NM|CTDIvol||{ctdi}|mGy|||
OBX|2|NM|DLP||{dlp}|mGy*cm|||
OBX|3|NM|EffectiveDose||{msv:.2f}|mSv|||"""

def read_dicom_files():
    files = filedialog.askopenfilenames(filetypes=[("DICOM files", "*.dcm")])
    if not files:
        return

    all_data.clear()
    for widget in content_frame.winfo_children():
        widget.destroy()

    for path in files:
        try:
            ds = pydicom.dcmread(path)
            name = str(getattr(ds, "PatientName", "Unknown"))
            ctdi = float(getattr(ds, "CTDIvol", 0))
            dlp = float(getattr(ds, "DLP", 0))
            date_str = getattr(ds, "StudyDate", "00000000")
            try:
                date_obj = datetime.strptime(date_str, "%Y%m%d")
            except:
                date_obj = datetime.now()

            msv = ctdi * 0.014

            if 'PixelData' in ds:
                img = Image.fromarray(ds.pixel_array)
                img.thumbnail((200, 200))
                photo = ImageTk.PhotoImage(img)
            else:
                photo = None

            data_dict = {
                "Name": name,
                "Date": date_obj,
                "CTDIvol": ctdi,
                "DLP": dlp,
                "mSv": msv,
                "Image": photo,
                "Sex": getattr(ds, "PatientSex", ""),
                "DOB": getattr(ds, "PatientBirthDate", ""),
                "StudyID": getattr(ds, "StudyID", ""),
                "Accession": getattr(ds, "AccessionNumber", "")
            }

            all_data.append(data_dict)

            hl7_msg = convert_to_hl7(ds, msv)
            hl7_filename = f"{HL7_DIR}/{name}_{date_obj.strftime('%Y%m%d')}.hl7"
            with open(hl7_filename, "w") as f:
                f.write(hl7_msg)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to process file {path}.\nError: {e}")

    df = pd.DataFrame(all_data)
    df.drop(columns=["Image"], inplace=True)
    if os.path.exists(CSV_FILE):
        df.to_csv(CSV_FILE, mode='a', index=False, header=False)
    else:
        df.to_csv(CSV_FILE, index=False)

    display_images()

def prompt_select_files(event=None):
    read_dicom_files()

def display_images():
    for widget in content_frame.winfo_children():
        widget.destroy()

def animate_label_color(label, colors, index=0):
    label.configure(text_color=colors[index])
    next_index = (index + 1) % len(colors)
    label.after(500, animate_label_color, label, colors, next_index)

def display_images():
    for widget in content_frame.winfo_children():
        widget.destroy()

    if not all_data:
        label = ctk.CTkLabel(
            content_frame,
            text="\n Click Here To Select DICOM Files",
            font=ctk.CTkFont(size=28, weight="bold"),
            justify="center",
            anchor="center",
            cursor="hand2"
        )
        label.pack(expand=True, fill="both", padx=50, pady=50)
        label.bind("<Button-1>", lambda e: read_dicom_files())

        # ألوان مريحة تتغير تدريجياً
        colors = ["#3a86ff", "#4dabf5", "#71b8ff", "#4dabf5"]
        animate_label_color(label, colors)

        return


    sort_option = sort_var.get()
    sorted_data = sorted(all_data, key=lambda x: x[sort_option])
    dose_summary = defaultdict(lambda: defaultdict(float))
    date_ranges = defaultdict(lambda: defaultdict(list))

    columns = 4
    for index, data in enumerate(sorted_data):
        row = index // columns
        col = index % columns

        frame = ctk.CTkFrame(content_frame)
        frame.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

        if data["Image"]:
            img_label = ctk.CTkLabel(frame, image=data["Image"], text="")
            img_label.image = data["Image"]
            img_label.pack(pady=5)
        else:
            ctk.CTkLabel(frame, text="No Image").pack()

        info = (
            f"👤 Name: {data['Name']}\n"
            f"📅 Date: {data['Date'].date()}\n"
            f"🧪 CTDIvol: {data['CTDIvol']} mGy\n"
            f"📏 DLP: {data['DLP']} mGy·cm\n"
            f"☢ Dose Result (mSv): {data['mSv']:.2f}"
        )
        ctk.CTkLabel(frame, text=info, justify="left").pack(pady=5)

        start_date = data["Date"]
        end_date = start_date + timedelta(days=365)
        patient_name = data["Name"]
        for d in all_data:
            if d["Name"] == patient_name and start_date <= d["Date"] <= end_date:
                year = start_date.year
                dose_summary[patient_name][year] += d["mSv"]
                date_ranges[patient_name][year].append(d["Date"])

    summary_box.delete("1.0", "end")
    summary_box.insert("end", "\n📊 Sum of Dose per Year:\n")
    for name in dose_summary:
        for year, total_dose in dose_summary[name].items():
            dates = sorted(date_ranges[name][year])
            start = dates[0].strftime("%Y-%m-%d") if dates else "N/A"
            end = dates[-1].strftime("%Y-%m-%d") if dates else "N/A"
            summary_box.insert("end", f"{name} - {year}: {total_dose:.2f} mSv (From {start} to {end})\n")

def search_hl7_message():
    name = search_entry.get().strip()
    if not name:
        messagebox.showwarning("Input Error", "Please enter a patient name.")
        return

    for filename in os.listdir(HL7_DIR):
        if name.lower() in filename.lower():
            filepath = os.path.join(HL7_DIR, filename)
            with open(filepath, "r") as f:
                hl7_content = f.read()
            hl7_textbox.delete("1.0", "end")
            hl7_textbox.insert("end", hl7_content)
            return

    messagebox.showinfo("Not Found", f"No HL7 message found for patient: {name}")
    hl7_textbox.delete("1.0", "end")

def clear_images():
    all_data.clear()
    for widget in content_frame.winfo_children():
        widget.destroy()
    summary_box.delete("1.0", "end")
    hl7_textbox.delete("1.0", "end")
    display_images()  # اعادة عرض رسالة رفع الملفات

root = ctk.CTk()
root.title("DICOM Viewer + HL7 + Summary")
root.geometry("1250x850")
root.resizable(True, True)

try:
    bg_image = Image.open("g.jpg").resize((1250, 850))
    bg_photo = ImageTk.PhotoImage(bg_image)
    bg_label = ctk.CTkLabel(root, image=bg_photo, text="")
    bg_label.place(relx=0, rely=0, relwidth=1, relheight=1)
except Exception as e:
    print(f"Background image not loaded: {e}")

select_button = ctk.CTkButton(root, text="📂 Select DICOM Files", command=read_dicom_files)
select_button.place(relx=0.02, rely=0.05)

clear_button = ctk.CTkButton(root, text="🗑 Clear All", command=clear_images)
clear_button.place(relx=0.15, rely=0.05)

ctk.CTkLabel(root, text="🔍 Search HL7 by Name:").place(relx=0.35, rely=0.05)
search_entry = ctk.CTkEntry(root, width=180)
search_entry.place(relx=0.52, rely=0.05)
search_button = ctk.CTkButton(root, text="Search", command=search_hl7_message)
search_button.place(relx=0.68, rely=0.05)

sort_var = ctk.StringVar(value="Date")
ctk.CTkLabel(root, text="Sort by:").place(relx=0.8, rely=0.05)
sort_optionmenu = ctk.CTkOptionMenu(root, variable=sort_var, values=["Date", "Name"], command=lambda _: display_images())
sort_optionmenu.place(relx=0.85, rely=0.05)

content_frame = ctk.CTkScrollableFrame(root)
content_frame.place(relx=0.02, rely=0.12, relwidth=0.96, relheight=0.55)

hl7_textbox = ctk.CTkTextbox(root)
hl7_textbox.place(relx=0.02, rely=0.7, relwidth=0.96, relheight=0.1)

summary_box = ctk.CTkTextbox(root)
summary_box.place(relx=0.02, rely=0.82, relwidth=0.96, relheight=0.1)

display_images()  # عند بداية التشغيل تظهر رسالة رفع الملفات

root.mainloop()
