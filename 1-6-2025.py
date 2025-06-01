import customtkinter as ctk
from tkinter import filedialog, messagebox, simpledialog
from PIL import Image, ImageTk
import pydicom
import os
from datetime import datetime
from datetime import datetime, timedelta

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

    return f"""MSH|^~\\&|CTApp|Hospital|PACS|Hospital|{date}||ORU^R01|MSG00001|P|2.3
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
                    img_pil.thumbnail((400, 400))
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

from datetime import timedelta

def display_text_data():
    for widget in content_frame.winfo_children():
        widget.destroy()

    filtered = []
    name_filter = name_filter_var.get().strip().lower()
    date_filter = date_filter_var.get().strip()

    for data in all_data:
        match_name = name_filter in data["Name"].lower()
        match_date = date_filter in data["Date"].strftime("%Y-%m-%d")
        if match_name and match_date:
            filtered.append(data)

    # جمع بيانات المرضى حسب الاسم
    patient_records = {}
    for data in all_data:
        name = data["Name"]
        dose = data["mSv"]
        date = data["Date"]
        if name not in patient_records:
            patient_records[name] = []
        patient_records[name].append((date, dose))

    # حساب الجرعة التراكمية لكل مريض (تجميع تدريجي)
    accumulated_dose_dict = {}
    for name in patient_records:
        records = patient_records[name]
        records.sort(key=lambda x: x[0])  # ترتيب حسب التاريخ
        total_dose = 0
        for date, dose in records:
            total_dose += dose
            accumulated_dose_dict[(name, date)] = round(total_dose, 2)

    # حساب الجرعة السنوية لكل فترة 365 يوم منفصلة لكل مريض
    dose_per_year_dict = {}

    for name in patient_records:
        records = sorted(patient_records[name], key=lambda x: x[0])
        if not records:
            continue
        
        # لو أول فحص (أول تاريخ) نحط صفر
        first_date = records[0][0]

        for current_date, _ in records:
            # لو الفحص هو الأول نرجع صفر
            if current_date == first_date:
                dose_per_year_dict[(name, current_date)] = 0.0
                continue
            
            # نحسب الفترة 364 يوم قبل التاريخ الحالي (شامل التاريخ)
            start_date = current_date - timedelta(days=364)

            # نجمّع جرعات الأشعات في الفترة (start_date إلى current_date)
            total_dose_year = 0.0
            for date, dose in records:
                if start_date <= date <= current_date:
                    total_dose_year += dose
            
            dose_per_year_dict[(name, current_date)] = round(total_dose_year, 2)

        # ترتيب البيانات حسب اختيار المستخدم
    sort_option = sort_var.get()
    sorted_data = sorted(filtered, key=lambda x: x[sort_option] if sort_option != "Name" else x["Name"].lower())

    scroll_frame = ctk.CTkScrollableFrame(content_frame, corner_radius=10, fg_color="#ffffff")
    scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)

    headers = ["Select", "Patient Name", "Study ID", "Date", "Modality", "Dose (mSv)", "Total Accumulated Dose", "Dose Per Year"]
    for col, header in enumerate(headers):
        lbl = ctk.CTkLabel(scroll_frame, text=header, font=ctk.CTkFont(size=14, weight="bold"))
        lbl.grid(row=0, column=col, padx=10, pady=10, sticky="w")

    check_vars.clear()
    for row, data in enumerate(sorted_data, start=1):
        name = data["Name"]
        date = data["Date"]

        accumulated_dose = accumulated_dose_dict.get((name, date), 0)
        dose_per_year = dose_per_year_dict.get((name, date), 0)

        var = ctk.BooleanVar(value=data in selected_cases)
        check_vars.append((var, data))
        chk = ctk.CTkCheckBox(scroll_frame, variable=var)
        chk.grid(row=row, column=0, padx=10, pady=5, sticky="w")

        ctk.CTkLabel(scroll_frame, text=name).grid(row=row, column=1, padx=10, pady=5, sticky="w")
        ctk.CTkLabel(scroll_frame, text=str(data["StudyID"])).grid(row=row, column=2, padx=10, pady=5, sticky="w")
        ctk.CTkLabel(scroll_frame, text=date.strftime("%Y-%m-%d")).grid(row=row, column=3, padx=10, pady=5, sticky="w")
        ctk.CTkLabel(scroll_frame, text=data["Modality"]).grid(row=row, column=4, padx=10, pady=5, sticky="w")
        ctk.CTkLabel(scroll_frame, text=f"{data['mSv']:.2f}").grid(row=row, column=5, padx=10, pady=5, sticky="w")
        ctk.CTkLabel(scroll_frame, text=f"{accumulated_dose:.2f}").grid(row=row, column=6, padx=10, pady=5, sticky="w")
        ctk.CTkLabel(scroll_frame, text=f"{dose_per_year:.2f}").grid(row=row, column=7, padx=10, pady=5, sticky="w")
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

    rows = 2 if len(selected_cases) == 4 else 1
    cols = 2

    for idx, data in enumerate(selected_cases):
        row = idx // 2
        col = idx % 2

        frame = ctk.CTkFrame(top, fg_color="#f9f9f9", corner_radius=15, border_width=1, border_color="#ccc")
        frame.grid(row=row, column=col, padx=15, pady=15, sticky="nsew")

        # نسمح للـ frame يتمدد عمودياً وأفقياً
        frame.grid_rowconfigure(0, weight=3)
        frame.grid_rowconfigure(1, weight=2)
        frame.grid_columnconfigure(0, weight=1)

        # تحجيم الصورة ديناميكي حسب حجم الـ frame
        if data["Image"]:
            # نستخدم Label بدون تعيين حجم ثابت، عشان الصورة تتغير مع حجم الـ frame تلقائي
            img_label = ctk.CTkLabel(frame, image=data["Image"], text="")
            img_label.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        info = (
            f"👤 Name: {data['Name']}\n"
            f"🆔 ID: {data['StudyID']}\n"
            f"📅 Date: {data['Date'].strftime('%Y-%m-%d')}\n"
            f"🧬 Type: {data['Modality']}\n"
            f"☢ Dose: {data['mSv']:.2f} mSv\n"
            f"🧪 CTDIvol: {data['CTDIvol']} mGy\n"
            f"📏 DLP: {data['DLP']} mGy·cm\n"
            f"⚧ Sex: {data['Sex']}\n"
            f"🎂 DOB: {data['DOB']}"
        )

        info_label = ctk.CTkLabel(frame, text=info, justify="left", anchor="nw", font=ctk.CTkFont(size=14))
        info_label.grid(row=1, column=0, sticky="nsew", padx=20, pady=(5, 20))

    # توزيع الصفوف والأعمدة في الـ Toplevel لتمدد تلقائي
    for r in range(rows):
        top.grid_rowconfigure(r, weight=1)
    for c in range(cols):
        top.grid_columnconfigure(c, weight=1)

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

def resize_bg(event):
    global bg_img_resized, bg_label
    new_width = event.width
    new_height = event.height
    resized = bg_img_orig.resize((new_width, new_height), Image.ANTIALIAS)
    bg_img_resized = ImageTk.PhotoImage(resized)
    bg_label.configure(image=bg_img_resized)

# واجهة المستخدم
root = ctk.CTk()
root.title("DICOM Viewer - Responsive Design")
root.geometry("1300x900")
root.configure(bg="white")  # خلفية بيضاء


bg_img_orig = Image.open("g.jpg")
bg_img_resized = ImageTk.PhotoImage(bg_img_orig)
bg_label = ctk.CTkLabel(root, image=bg_img_resized, text="")
bg_label.place(x=0, y=0, relwidth=1, relheight=1)
root.bind("<Configure>", resize_bg)

# أزرار التحكم
ctk.CTkButton(root, text="Load DICOM Files", command=read_dicom_files, width=150, height=35).place(relx=0.02, rely=0.02)
ctk.CTkButton(root, text="Show HL7 Message", command=show_hl7_message, width=150, height=35).place(relx=0.20, rely=0.02)
ctk.CTkButton(root, text="Show Selected Cases", command=show_selected_cases, width=180, height=35).place(relx=0.37, rely=0.02)
ctk.CTkButton(root, text="Delete Selected", command=delete_selected, width=150, height=35).place(relx=0.55, rely=0.02)

# خيارات الفلترة والترتيب
sort_var = ctk.StringVar(value="Name")
ctk.CTkLabel(root, text="Sort by:").place(relx=0.73, rely=0.015)
ctk.CTkOptionMenu(root, variable=sort_var, values=["Name", "Date"], command=lambda _: display_text_data()).place(relx=0.78, rely=0.015)

# فلتر الاسم
name_filter_label = ctk.CTkLabel(root, text="Name:", fg_color="white", bg_color="white", text_color="black")
name_filter_label.place(relx=0.005, rely=0.07)

name_filter_var = ctk.StringVar()
ctk.CTkEntry(root, placeholder_text="Filter by Name", textvariable=name_filter_var).place(relx=0.05, rely=0.07, relwidth=0.17)
name_filter_var.trace_add("write", lambda *args: display_text_data())

# فلتر التاريخ
date_filter_label = ctk.CTkLabel(root, text="Date:", fg_color="white", bg_color="white", text_color="black")
date_filter_label.place(relx=0.250, rely=0.07)

date_filter_var = ctk.StringVar()
ctk.CTkEntry(root, placeholder_text="Filter by Date (YYYY-MM-DD)", textvariable=date_filter_var).place(relx=0.300, rely=0.07, relwidth=0.18)
date_filter_var.trace_add("write", lambda *args: display_text_data())
# محتوى البيانات
# shadow frame (أسود فاتح كخلفية خفيفة)
shadow_frame = ctk.CTkFrame(root, fg_color="#416dcc", corner_radius=12)
shadow_frame.place(relx=0.10, rely=0.15, relwidth=0.80, relheight=0.70)

# frame الأساسي فوق الـ shadow
content_frame = ctk.CTkFrame(root, fg_color="#ffffff", corner_radius=10)
content_frame.place(relx=0.11, rely=0.16, relwidth=0.78, relheight=0.68)

# رسالة ترحيبية
welcome_label = ctk.CTkLabel(content_frame, text="Click here to select DICOM files",
                              text_color="blue", font=ctk.CTkFont(size=20, weight="bold"), cursor="hand2")
welcome_label.pack(expand=True)
welcome_label.bind("<Button-1>", lambda e: read_dicom_files())

root.mainloop()
