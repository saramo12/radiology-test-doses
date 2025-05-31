import customtkinter as ctk
from tkinter import filedialog, messagebox, simpledialog
from PIL import Image, ImageTk
import pydicom
import os
from datetime import datetime

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("dark-blue")

CSV_FILE = "rad.csv"
HL7_DIR = "hl7_messages"
os.makedirs(HL7_DIR, exist_ok=True)

all_data = []
selected_cases = []
check_vars = []

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
    selected_cases.clear()
    for widget in content_frame.winfo_children():
        widget.destroy()

    temp_cases = {}
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

            key = (name, date_obj.date(), getattr(ds, "StudyID", ""), getattr(ds, "AccessionNumber", ""))
            if key not in temp_cases:
                img = None
                if 'PixelData' in ds:
                    img_pil = Image.fromarray(ds.pixel_array)
                    img_pil.thumbnail((400, 400))  # تم زيادة الحجم هنا
                    img = ImageTk.PhotoImage(img_pil)

                data_dict = {
                    "Name": name,
                    "Date": date_obj,
                    "CTDIvol": ctdi,
                    "DLP": dlp,
                    "mSv": msv,
                    "Sex": getattr(ds, "PatientSex", ""),
                    "DOB": getattr(ds, "PatientBirthDate", ""),
                    "StudyID": getattr(ds, "StudyID", ""),
                    "Accession": getattr(ds, "AccessionNumber", ""),
                    "Image": img,
                    "Path": path,
                    "Modality": getattr(ds, "Modality", "Unknown"),
                    "Dataset": ds
                }
                temp_cases[key] = data_dict

                hl7_msg = convert_to_hl7(ds, msv)
                hl7_filename = f"{HL7_DIR}/{name}_{date_obj.strftime('%Y%m%d')}_{data_dict['StudyID']}.hl7"
                with open(hl7_filename, "w") as f:
                    f.write(hl7_msg)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to process file {path}.\nError: {e}")

    all_data.extend(temp_cases.values())
    display_text_data()

def display_text_data():
    for widget in content_frame.winfo_children():
        widget.destroy()

    # حساب المجموع الكلي والجرعة السنوية لكل مريض
    dose_accumulated = {}  # {patient_name: total_dose}
    doses_per_year = {}    # {(patient_name, year): total_dose}

    for data in all_data:
        name = data["Name"]
        dose = data["mSv"]
        year = data["Date"].year

        # مجموع الجرعات الكلي لكل مريض
        dose_accumulated[name] = dose_accumulated.get(name, 0) + dose
        # مجموع الجرعة للسنة لكل مريض
        doses_per_year[(name, year)] = doses_per_year.get((name, year), 0) + dose

    # حساب الجرعة السنوية المتوسطة لكل مريض = مجموع الجرعات الكلية / عدد السنوات التي حصل فيها على جرعات
    dose_per_year_avg = {}
    for name in dose_accumulated:
        years = [y for (n, y) in doses_per_year.keys() if n == name]
        if years:
            dose_per_year_avg[name] = dose_accumulated[name] / len(set(years))
        else:
            dose_per_year_avg[name] = 0

    # ترتيب البيانات
    sort_option = sort_var.get()
    sorted_data = sorted(all_data, key=lambda x: x[sort_option] if sort_option != "Name" else x["Name"].lower())

    scroll_frame = ctk.CTkScrollableFrame(content_frame, corner_radius=10, fg_color="#ffffff")
    scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)

    headers = ["Select", "Patient Name", "Study ID", "Date", "Modality", "Dose (mSv)", "Total Accumulated Dose (mSv)", "Dose Per Year (mSv)"]
    for col, header in enumerate(headers):
        lbl = ctk.CTkLabel(scroll_frame, text=header, font=ctk.CTkFont(size=14, weight="bold"))
        lbl.grid(row=0, column=col, padx=10, pady=10, sticky="w")

    check_vars.clear()
    for row, data in enumerate(sorted_data, start=1):
        var = ctk.BooleanVar(value=data in selected_cases)
        check_vars.append((var, data))
        chk = ctk.CTkCheckBox(scroll_frame, variable=var)
        chk.grid(row=row, column=0, padx=10, pady=5, sticky="w")

        ctk.CTkLabel(scroll_frame, text=data["Name"]).grid(row=row, column=1, padx=10, pady=5, sticky="w")
        ctk.CTkLabel(scroll_frame, text=str(data["StudyID"])).grid(row=row, column=2, padx=10, pady=5, sticky="w")
        ctk.CTkLabel(scroll_frame, text=data["Date"].strftime("%Y-%m-%d")).grid(row=row, column=3, padx=10, pady=5, sticky="w")
        ctk.CTkLabel(scroll_frame, text=data["Modality"]).grid(row=row, column=4, padx=10, pady=5, sticky="w")
        ctk.CTkLabel(scroll_frame, text=f"{data['mSv']:.2f}").grid(row=row, column=5, padx=10, pady=5, sticky="w")
        ctk.CTkLabel(scroll_frame, text=f"{dose_accumulated.get(data['Name'], 0):.2f}").grid(row=row, column=6, padx=10, pady=5, sticky="w")
        ctk.CTkLabel(scroll_frame, text=f"{dose_per_year_avg.get(data['Name'], 0):.2f}").grid(row=row, column=7, padx=10, pady=5, sticky="w")

def update_selected_cases():
    selected_cases.clear()
    for var, data in check_vars:
        if var.get():
            selected_cases.append(data)

def show_hl7_message():
    update_selected_cases()
    if not selected_cases:
        messagebox.showwarning("No Selection", "Please select at least one case to view HL7 message.")
        return

    password = simpledialog.askstring("Password", "Enter password to view HL7 message:", show='*')
    if password != "admin123":
        messagebox.showerror("Unauthorized", "Incorrect password.")
        return

    data = selected_cases[-1]
    hl7_filename = f"{HL7_DIR}/{data['Name']}_{data['Date'].strftime('%Y%m%d')}_{data['StudyID']}.hl7"
    if os.path.exists(hl7_filename):
        with open(hl7_filename, "r") as f:
            hl7 = f.read()
        messagebox.showinfo("HL7 Message", hl7)
    else:
        messagebox.showerror("Not Found", "HL7 message not found.")

def show_selected_cases():
    update_selected_cases()
    if len(selected_cases) not in [2, 4]:
        messagebox.showwarning("Selection Error", "Please select 2 or 4 cases.")
        return

    top = ctk.CTkToplevel(root)
    top.title("Selected Cases Viewer")
    top.geometry("1100x700")
    top.lift()

    for idx, data in enumerate(selected_cases):
        row = idx // 2
        col = idx % 2

        frame = ctk.CTkFrame(top, fg_color="#f0f0f0", corner_radius=10)
        frame.grid(row=row, column=col, padx=20, pady=20, sticky="nsew")

        if data["Image"]:
            img_label = ctk.CTkLabel(frame, image=data["Image"], text="")
            img_label.image = data["Image"]
            img_label.pack(pady=10)

        info = (
            f"👤 Name: {data['Name']}\n"
            f"🆔 ID: {data['StudyID']}\n"
            f"📅 Date: {data['Date'].date()}\n"
            f"🧬 Type: {data['Modality']}\n"
            f"☢ Dose: {data['mSv']:.2f} mSv\n"
            f"🧪 CTDIvol: {data['CTDIvol']} mGy\n"
            f"📏 DLP: {data['DLP']} mGy·cm\n"
            f"⚧ Sex: {data['Sex']}\n"
            f"🎂 DOB: {data['DOB']}"
        )
        ctk.CTkLabel(frame, text=info, justify="left").pack(pady=10)

    for i in range(2):
        top.grid_columnconfigure(i, weight=1)
        top.grid_rowconfigure(i, weight=1)

def resize_bg(event):
    global bg_img_resized, bg_label
    new_width = event.width
    new_height = event.height
    resized = bg_img_orig.resize((new_width, new_height), Image.ANTIALIAS)
    bg_img_resized = ImageTk.PhotoImage(resized)
    bg_label.configure(image=bg_img_resized)

root = ctk.CTk()
root.title("DICOM Viewer - Responsive Design")
root.geometry("1300x900")

# تحميل صورة الخلفية
bg_img_orig = Image.open("g.jpg")  # ضع مسار صورتك هنا
bg_img_resized = ImageTk.PhotoImage(bg_img_orig)
bg_label = ctk.CTkLabel(root, image=bg_img_resized, text="")
bg_label.place(x=0, y=0, relwidth=1, relheight=1)
root.bind("<Configure>", resize_bg)

# زر اختيار ملفات DICOM
load_button = ctk.CTkButton(root, text="Load DICOM Files", command=read_dicom_files, width=150, height=35)
load_button.place(relx=0.02, rely=0.02)

# زر عرض HL7
hl7_button = ctk.CTkButton(root, text="Show HL7 Message", command=show_hl7_message, width=150, height=35)
hl7_button.place(relx=0.20, rely=0.02)

# اختيار الترتيب
sort_var = ctk.StringVar(value="Name")
sort_label = ctk.CTkLabel(root, text="Sort by:")
sort_label.place(relx=0.4, rely=0.02)
sort_option_menu = ctk.CTkOptionMenu(root, variable=sort_var, values=["Name", "Date"])
sort_option_menu.place(relx=0.47, rely=0.02)

# زر عرض الحالات المحددة (2 أو 4)
show_button = ctk.CTkButton(root, text="Show Selected Cases", command=show_selected_cases, width=180, height=35)
show_button.place(relx=0.62, rely=0.02)

# زر حذف الحالات المحددة
def delete_selected():
    update_selected_cases()
    if not selected_cases:
        messagebox.showwarning("No Selection", "Please select cases to delete.")
        return
    for sel in selected_cases:
        if sel in all_data:
            all_data.remove(sel)
    selected_cases.clear()
    display_text_data()

delete_button = ctk.CTkButton(root, text="Delete Selected", command=delete_selected, width=150, height=35)
delete_button.place(relx=0.83, rely=0.02)

# محتوى النصوص والبيانات
content_frame = ctk.CTkFrame(root, fg_color="#ffffff", corner_radius=15)
content_frame.place(relx=0.02, rely=0.08, relwidth=0.96, relheight=0.9)

# رسالة الترحيب (تختفي بعد التحميل)
welcome_label = ctk.CTkLabel(content_frame, text="Click here to select DICOM files",
                            text_color="blue", font=ctk.CTkFont(size=20, weight="bold"), cursor="hand2")
welcome_label.pack(expand=True)
def on_welcome_click(event):
    read_dicom_files()
welcome_label.bind("<Button-1>", on_welcome_click)

root.mainloop()
