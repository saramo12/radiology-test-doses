import customtkinter as ctk
from tkinter import filedialog, messagebox, simpledialog
from PIL import Image, ImageTk
import pydicom
import os
from datetime import datetime
from datetime import datetime, timedelta
from pydicom.errors import InvalidDicomError
import re
from rapidfuzz import fuzz  # أسرع من fuzzywuzzy ويمكنك استبداله به

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("dark-blue")

CSV_FILE = "rad.csv"
HL7_DIR = "hl7_messages"
os.makedirs(HL7_DIR, exist_ok=True)

all_data = []
selected_cases = []
check_vars = []
# أسماء شائعة لتطبيع التهجئة
COMMON_VARIANTS = {
    "sara": "sarah",
    "mena": "mina",
    "meena": "mina",
    "shawkia": "shawkya",
    "usama": "osama",
    "latif": "lateef",
    "allateef": "lateef",
    "awaad": "awad"
}



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
def normalize_name(name):
    name = re.sub(r"[^a-zA-Z ]", " ", name)
    name = re.sub(r"\s+", " ", name).strip().lower()
    return name

def is_same_person(name1, name2, threshold=85):
    n1 = normalize_name(name1)
    n2 = normalize_name(name2)

    # تطابق شامل سريع
    if fuzz.token_set_ratio(n1, n2) >= threshold:
        return True

    # مقارنة كل مقطع اسمي على حدة (ذكية)
    n1_parts = n1.split()
    n2_parts = n2.split()

    shorter, longer = (n1_parts, n2_parts) if len(n1_parts) <= len(n2_parts) else (n2_parts, n1_parts)

    matches = 0
    for part in shorter:
        # نحاول نلاقي أي تطابق مقبول في الاسم الأطول
        if any(fuzz.partial_ratio(part, lp) >= threshold for lp in longer):
            matches += 1

    # نعتبرهم متشابهين لو تطابق كافي
    return matches >= len(shorter) - 1  # يسمح باختلاف بسيط


def read_dicom_folder():
    folders = filedialog.askdirectory()
    if not folders:
        return

    dicom_files = []

    # البحث داخل المجلد والمجلدات الفرعية فقط عن ملفات DICOM السليمة
    for root_dir, dirs, files in os.walk(folders):
        for file in files:
            if file.lower().endswith(".dcm"):
                file_path = os.path.join(root_dir, file)
                try:
                    ds = pydicom.dcmread(file_path, stop_before_pixels=True)  # نقرأ الرأس فقط للتأكد
                    dicom_files.append(file_path)
                except InvalidDicomError:
                    print(f"Skipped invalid DICOM file: {file_path}")
                except Exception as e:
                    print(f"Error reading file {file_path}: {e}")

    if not dicom_files:
        messagebox.showinfo("No DICOM Files", "No valid DICOM files found in the selected folder.")
        return

    process_dicom_files(dicom_files)
def process_dicom_files(files):
    if not files:
        return

    for widget in content_frame.winfo_children():
        widget.destroy()

    temp_cases = {}
    existing_keys = [
        (d["Name"], d["Date"].date(), d["StudyID"], d.get("Accession", ""))
        for d in all_data
    ]

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

            # نحاول نطابق الأسماء الذكية
            matched_key = None
            for existing in existing_keys:
                if is_same_person(name, existing[0]) and existing[1] == date_obj.date():
                    matched_key = existing
                    break

            key = matched_key if matched_key else (name, date_obj.date(), getattr(ds, "StudyID", ""), getattr(ds, "AccessionNumber", ""))

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
# عدل دالة read_dicom_files الحالية لتستخدم process_dicom_files:
def read_dicom_files():
    files = filedialog.askopenfilenames(filetypes=[("DICOM files", "*.dcm")])
    process_dicom_files(files)
def display_text_data():
    global check_vars
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
        
        first_date = records[0][0]

        for current_date, _ in records:
            if current_date == first_date:
                dose_per_year_dict[(name, current_date)] = 0.0
                continue
            
            start_date = current_date - timedelta(days=364)
            total_dose_year = 0.0
            for date, dose in records:
                if start_date <= date <= current_date:
                    total_dose_year += dose
            
            dose_per_year_dict[(name, current_date)] = round(total_dose_year, 2)

    # تحديد ترتيب الأعمدة حسب اختيار المستخدم
    sort_option = sort_var.get()

    # تعيين ترتيب الأعمدة حسب الفرز (Name أو Date)
    if sort_option == "Date":
        headers = ["Select", "Date", "Patient Name", "Study ID", "Modality", "Dose (mSv)", "Total Accumulated Dose", "Dose Per Year"]
        def sort_key(x): return x["Date"]
        col_indices = {
            "select": 0,
            "date": 1,
            "name": 2,
            "studyid": 3,
            "modality": 4,
            "dose": 5,
            "accumulated": 6,
            "per_year": 7
        }
    else:
        # Default or "Name"
        headers = ["Select", "Patient Name", "Date", "Study ID", "Modality", "Dose (mSv)", "Total Accumulated Dose", "Dose Per Year"]
        def sort_key(x): return x["Name"].lower()
        col_indices = {
            "select": 0,
            "name": 1,
            "date": 2,
            "studyid": 3,
            "modality": 4,
            "dose": 5,
            "accumulated": 6,
            "per_year": 7
        }

    sorted_data = sorted(filtered, key=sort_key)

    scroll_frame = ctk.CTkScrollableFrame(content_frame, corner_radius=10, fg_color="#ffffff")
    scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)

    # عرض رؤوس الأعمدة مع محاذاة وسطية
    for col, header in enumerate(headers):
        lbl = ctk.CTkLabel(scroll_frame, text=header, font=ctk.CTkFont(size=14, weight="bold"), anchor="center")
        lbl.grid(row=0, column=col, padx=5, pady=10, sticky="nsew")

    check_vars.clear()

    for row, data in enumerate(sorted_data, start=1):
        name = data["Name"]
        date = data["Date"]

        accumulated_dose = accumulated_dose_dict.get((name, date), 0)
        dose_per_year = dose_per_year_dict.get((name, date), 0)

        var = ctk.BooleanVar(value=data in selected_cases)
        check_vars.append((var, data))
        chk = ctk.CTkCheckBox(scroll_frame, variable=var)
        # عمود select ضيق جدا، محاذاة وسط
        chk.grid(row=row, column=col_indices["select"], padx=5, pady=5, sticky="nsew")

        # دالة مساعدة للعرض في كل عمود مع محاذاة وسطية
        def add_label(row, col, text):
            lbl = ctk.CTkLabel(scroll_frame, text=text, anchor="center")
            lbl.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

        # عرض البيانات حسب ترتيب الأعمدة
        if sort_option == "Date":
            add_label(row, col_indices["date"], date.strftime("%Y-%m-%d"))
            add_label(row, col_indices["name"], name)
        else:
            add_label(row, col_indices["name"], name)
            add_label(row, col_indices["date"], date.strftime("%Y-%m-%d"))

        add_label(row, col_indices["studyid"], str(data["StudyID"]))
        add_label(row, col_indices["modality"], data["Modality"])
        add_label(row, col_indices["dose"], f"{data['mSv']:.2f}")
        add_label(row, col_indices["accumulated"], f"{accumulated_dose:.2f}")
        add_label(row, col_indices["per_year"], f"{dose_per_year:.2f}")

    # ضبط أوزان الأعمدة لجعلها ريسبونسف
    for col in range(len(headers)):
        scroll_frame.grid_columnconfigure(col, weight=1)

    # ضبط عمود select ليكون ضيق جدا
    scroll_frame.grid_columnconfigure(col_indices["select"], weight=0, minsize=40)

def update_selected_cases():
    selected_cases.clear()
    for var, data in check_vars:
        if var.get():
            selected_cases.append(data)

def show_hl7_message():
    update_selected_cases()
    if len(selected_cases) != 1:
        messagebox.showwarning("Selection Error", "Please select exactly ONE case to view its HL7 message.")
        return

    password = simpledialog.askstring("Password", "Enter password to view HL7 message:", show='*')
    if password != "admin123":
        messagebox.showerror("Unauthorized", "Incorrect password.")
        return

    data = selected_cases[0]  # لأن في حالة واحدة فقط
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

        frame.grid_rowconfigure(0, weight=3)
        frame.grid_rowconfigure(1, weight=2)
        frame.grid_columnconfigure(0, weight=1)

        images = data.get("Images", [])
        current_index = [0]  # استخدم قائمة لتكون قابلة للتعديل داخل الوظائف الداخلية

        def update_image(label, img_list, index_list, container):
            if not img_list:
                return
            pil_image = img_list[index_list[0]].copy()
            # تحجيم الصورة حسب حجم الفريم
            container_width = container.winfo_width()
            container_height = int(container.winfo_height() * 0.7)
            pil_image = pil_image.resize((container_width, container_height), Image.ANTIALIAS)
            tk_img = ImageTk.PhotoImage(pil_image)
            label.configure(image=tk_img)
            label.image = tk_img

        img_label = ctk.CTkLabel(frame, text="")
        img_label.grid(row=0, column=0, columnspan=3, sticky="nsew", padx=10, pady=10)

        # أزرار تنقّل
        def next_image():
            current_index[0] = (current_index[0] + 1) % len(images)
            update_image(img_label, images, current_index, frame)

        def prev_image():
            current_index[0] = (current_index[0] - 1) % len(images)
            update_image(img_label, images, current_index, frame)

        btn_prev = ctk.CTkButton(frame, text="⏪", width=40, command=prev_image)
        btn_next = ctk.CTkButton(frame, text="⏩", width=40, command=next_image)
        btn_prev.grid(row=1, column=0, sticky="w", padx=15)
        btn_next.grid(row=1, column=2, sticky="e", padx=15)

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
        info_label.grid(row=2, column=0, columnspan=3, sticky="nsew", padx=20, pady=(5, 20))

        frame.bind("<Configure>", lambda event, lbl=img_label, imgs=images, idx=current_index, fr=frame: update_image(lbl, imgs, idx, fr))

    for r in range(rows):
        top.grid_rowconfigure(r, weight=1)
    for c in range(cols):
        top.grid_columnconfigure(c, weight=1)
def delete_selected():
    update_selected_cases()
    if not selected_cases:
        messagebox.showwarning("No Selection", "Please select cases to delete.")
        return

    # طلب كلمة المرور الأولى
    password = simpledialog.askstring("Password", "Enter password to delete selected cases:", show='*')
    if password != "admin123":
        messagebox.showerror("Unauthorized", "Incorrect password.")
        return

    # طلب التأكيد بكتابة كلمة المرور مجددًا
    confirm_pass = simpledialog.askstring("Confirm Delete", "To confirm deletion, please type password again:", show='*', parent=root)
    if confirm_pass != "admin123":
        messagebox.showerror("Unauthorized", "Password confirmation failed.", parent=root)
        return  # <== فقط لو غلط

    # رسالة تأكيد نهائية
    confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete {len(selected_cases)} selected case(s)? This action cannot be undone.")
    if not confirm:
        return

    # تنفيذ الحذف
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
# الأزرار بخطوة relx = 0.14 لتوزيعهم بالتساوي تقريبًا
ctk.CTkButton(root, text="Load DICOM Files", command=read_dicom_files, width=150, height=35).place(relx=0.02, rely=0.02)
ctk.CTkButton(root, text="Load DICOM Folder", command=read_dicom_folder, width=150, height=35).place(relx=0.17, rely=0.02)
ctk.CTkButton(root, text="Show HL7 Message", command=show_hl7_message, width=150, height=35).place(relx=0.32, rely=0.02)
ctk.CTkButton(root, text="Show Selected Cases", command=show_selected_cases, width=180, height=35).place(relx=0.47, rely=0.02)
ctk.CTkButton(root, text="Delete Selected", command=delete_selected, width=150, height=35).place(relx=0.66, rely=0.02)

# خيارات الفلترة والترتيب بجانب الأزرار
sort_var = ctk.StringVar(value="Name")
ctk.CTkLabel(root, text="Sort by:").place(relx=0.82, rely=0.015)
ctk.CTkOptionMenu(root, variable=sort_var, values=["Name", "Date"], command=lambda _: display_text_data()).place(relx=0.88, rely=0.015)

# فلتر الاسم
name_filter_var = ctk.StringVar()
name_filter_label = ctk.CTkLabel(root, text="Name:", fg_color="white", bg_color="white", text_color="black")
name_filter_label.place(relx=0.28, rely=0.08)

ctk.CTkEntry(root, placeholder_text="Filter by Name", textvariable=name_filter_var).place(relx=0.33, rely=0.08, relwidth=0.17)
name_filter_var.trace_add("write", lambda *args: display_text_data())

# فلتر التاريخ
date_filter_var = ctk.StringVar()
date_filter_label = ctk.CTkLabel(root, text="Date:", fg_color="white", bg_color="white", text_color="black")
date_filter_label.place(relx=0.52, rely=0.08)

ctk.CTkEntry(root, placeholder_text="Filter by Date (YYYY-MM-DD)", textvariable=date_filter_var).place(relx=0.57, rely=0.08, relwidth=0.18)
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
