import customtkinter as ctk
from tkinter import filedialog, messagebox, simpledialog
from PIL import Image, ImageTk
import pydicom
import os
import numpy as np
from datetime import datetime
from datetime import datetime, timedelta
from pydicom.errors import InvalidDicomError
import re
from rapidfuzz import fuzz  # أسرع من fuzzywuzzy ويمكنك استبداله به
import socket
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\tesseract-5.5.1\tesseract.exe"

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
# def convert_to_hl7(data):
#     """
#     data: dict تحتوي على كل معلومات الحالة مثل:
#     'Name', 'Date', 'CTDIvol', 'DLP', 'mSv', 'Sex', 'DOB', 'StudyID', 'Accession',
#     'Modality', 'AccumulatedDose', 'DosePerYear'
#     """
#     date = data.get("Date").strftime("%Y%m%d") if data.get("Date") else "00000000"
#     name = data.get("Name", "Unknown")
#     ctdi = data.get("CTDIvol", 0)
#     dlp = data.get("DLP", 0)
#     msv = data.get("mSv", 0)
#     gender = data.get("Sex", "")
#     dob = data.get("DOB", "")
#     study_id = data.get("StudyID", "")
#     accession = data.get("Accession", "")
#     modality = data.get("Modality", "Unknown")
#     accumulated_dose = data.get("AccumulatedDose", 0)
#     dose_per_year = data.get("DosePerYear", 0)

#     hl7_message = f"""MSH|^~\\&|RadiologySystem|Hospital|PACS|Hospital|{datetime.now().strftime('%Y%m%d%H%M%S')}||ORM^O01|{study_id}|P|2.3
# PID|||{study_id}||{name}||{dob}|{gender}||
# OBR|||{study_id}^{accession}||{modality}|||||{date}
# OBX|1|NM|CTDIvol||{ctdi}|mGy|||
# OBX|2|NM|DLP||{dlp}|mGy*cm|||
# OBX|3|NM|Dose_mSv||{msv:.5f}|mSv|||
# OBX|4|NM|AccumulatedDose||{accumulated_dose:.5f}|mSv|||
# OBX|5|NM|DosePerYear||{dose_per_year:.5f}|mSv|||
# """
#
# return hl7_message

def send_hl7_message(ip, port, message):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((ip, port))
        sock.sendall(message.encode('utf-8'))
        sock.close()
        messagebox.showinfo("Success", f"HL7 message sent to {ip}:{port}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to send HL7 message.\n{e}")

def convert_to_hl7_from_table(data):
    accumulated_dose = data.get("AccumulatedDose", 0)
    dose_per_year = data.get("DosePerYear", 0)
    return f"""MSH|^~\\&|RadiologySystem|Hospital|PACS|Hospital|{datetime.now().strftime('%Y%m%d%H%M%S')}||ORM^O01|{data.get("PatientID", "")}|P|2.3
PID|||{data.get("PatientID", "")}||{data.get("Name", "")}|||{data.get("DOB", "")}|{data.get("Sex", "")}
OBR|||{data.get("PatientID", "")}||{data.get("Modality", "")}|||||{data.get("Date").strftime('%Y%m%d')}
OBX|1|NM|CTDIvol||{data.get("CTDIvol", 0):.5f}|mGy
OBX|2|NM|DLP||{data.get("DLP", 0):.5f}|mGy*cm
OBX|3|NM|Dose_mSv||{data.get("mSv", 0):.5f}|mSv
OBX|4|NM|AccumulatedDose||{accumulated_dose:.5f}|mSv
OBX|5|NM|DosePerYear||{dose_per_year:.5f}|mSv
"""
# def show_hl7_for_selected():
#     selected = [data for var, data in check_vars if var.get()]
    
#     if len(selected) != 1:
#         messagebox.showerror("Error", "Please select exactly one case to view HL7 message.")
#         return

#     data = selected[0]
#     hl7_message = convert_to_hl7_from_table(data)

#     hl7_window = ctk.CTkToplevel()
#     hl7_window.title("HL7 Message")
#     hl7_window.geometry("700x400")

#     textbox = ctk.CTkTextbox(hl7_window, wrap="word")
#     textbox.insert("1.0", hl7_message)
#     textbox.configure(state="disabled")
#     textbox.pack(fill="both", expand=True, padx=10, pady=10)
def show_hl7_for_selected():
    
    selected = [data for var, data in check_vars if var.get()]
    
    if len(selected) != 1:
        messagebox.showerror("Error", "Please select exactly one case to view HL7 message.")
        return

    # طلب الباسوورد
    password = simpledialog.askstring("Password", "Enter password to view HL7 message:", show='*')
    if password != "admin123":
        messagebox.showerror("Unauthorized", "Incorrect password.")
        return

    data = selected[0]
    hl7_message = convert_to_hl7_from_table(data)

    hl7_window = ctk.CTkToplevel()
    hl7_window.title("HL7 Message")
    hl7_window.geometry("700x450")
    hl7_window.attributes("-topmost", True)  # دايمًا فوق

    textbox = ctk.CTkTextbox(hl7_window, wrap="word")
    textbox.insert("1.0", hl7_message)
    textbox.configure(state="disabled")
    textbox.pack(fill="both", expand=True, padx=10, pady=(10,5))

    # مدخلات ال IP و Port
    ip_var = ctk.StringVar()
    port_var = ctk.StringVar()

    frame_send = ctk.CTkFrame(hl7_window)
    frame_send.pack(fill="x", padx=10, pady=5)

    ctk.CTkLabel(frame_send, text="IP Address:").pack(side="left")
    ip_entry = ctk.CTkEntry(frame_send, textvariable=ip_var, width=150)
    ip_entry.pack(side="left", padx=5)

    ctk.CTkLabel(frame_send, text="Port:").pack(side="left")
    port_entry = ctk.CTkEntry(frame_send, textvariable=port_var, width=80)
    port_entry.pack(side="left", padx=5)

    def on_send():
        ip = ip_var.get().strip()
        port_text = port_var.get().strip()
        if not ip or not port_text:
            messagebox.showerror("Input Error", "Please enter both IP address and port.")
            return
        try:
            port = int(port_text)
        except:
            messagebox.showerror("Input Error", "Port must be a number.")
            return
        
        send_hl7_message(ip, port, hl7_message)

    send_btn = ctk.CTkButton(frame_send, text="Send HL7 Message", command=on_send)
    send_btn.pack(side="left", padx=10)
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


# def read_dicom_folder():
#     folders = filedialog.askdirectory()
#     if not folders:
#         return

#     dicom_files = []

#     # البحث داخل المجلد والمجلدات الفرعية فقط عن ملفات DICOM السليمة
#     for root_dir, dirs, files in os.walk(folders):
#         for file in files:
#             if file.lower().endswith(".dcm"):
#                 file_path = os.path.join(root_dir, file)
#                 try:
#                     ds = pydicom.dcmread(file_path, stop_before_pixels=True)  # نقرأ الرأس فقط للتأكد
#                     dicom_files.append(file_path)
#                 except InvalidDicomError:
#                     print(f"Skipped invalid DICOM file: {file_path}")
#                 except Exception as e:
#                     print(f"Error reading file {file_path}: {e}")

#     if not dicom_files:
#         messagebox.showinfo("No DICOM Files", "No valid DICOM files found in the selected folder.")
#         return

#     process_dicom_files(dicom_files)


def is_dicom(file_path):
    """يتأكد إن الملف DICOM من محتواه الداخلي، مش من اسمه"""
    try:
        with open(file_path, 'rb') as f:
            f.seek(128)
            return f.read(4) == b'DICM'
    except:
        return False

def read_dicom_folder():
    folders = filedialog.askdirectory()
    if not folders:
        return
    dicom_files = []
    for root_dir, dirs, files in os.walk(folders):
        for file in files:
            file_path = os.path.join(root_dir, file)
            if not os.path.isfile(file_path):
                continue

            if is_dicom(file_path):  # هنا بنفحصه من جوه مش من الامتداد
                try:
                    ds = pydicom.dcmread(file_path, stop_before_pixels=True)
                    dicom_files.append(file_path)
                except InvalidDicomError:
                    print(f"Skipped invalid DICOM file: {file_path}")
                except Exception as e:
                    print(f"Error reading file {file_path}: {e}")

    if not dicom_files:
        messagebox.showinfo("No DICOM Files", "No valid DICOM files found in the selected folder.")
        return

    process_dicom_files(dicom_files)




















def extract_total_dlp(ds):
    if 'PixelData' not in ds:
        return None

    try:
        arr = ds.pixel_array
        if arr.dtype != 'uint8':
            arr = (arr / arr.max() * 255).astype('uint8')
        img = Image.fromarray(arr).convert("L")
        text = pytesseract.image_to_string(img)

        # تحسين الـ regex لاستخراج Total DLP
        match = re.search(r"Total\s*DLP[:\s]*([0-9]+\.?[0-9]*)", text, re.IGNORECASE)
        if match:
            return float(match.group(1))
    except Exception as e:
        print("OCR error:", e)
    return None

def process_dicom_files(files):
    if not files:
        return

    for widget in content_frame.winfo_children():
        widget.destroy()

    temp_cases = {}
    existing_keys = [
        (d["Name"], d["Date"].date(), d["PatientID"], d.get("Accession", ""))
        for d in all_data
    ]

    for path in files:
        try:
            ds = pydicom.dcmread(path)
            name = str(getattr(ds, "PatientName", "Unknown"))
            date_str = getattr(ds, "StudyDate", "00000000")
            try:
                date_obj = datetime.strptime(date_str, "%Y%m%d")
            except:
                date_obj = datetime.now()

            modality = getattr(ds, "Modality", "")
            series_desc = getattr(ds, "SeriesDescription", "").lower()
            study_desc = getattr(ds, "StudyDescription", "").lower()

            k = 0.015  # default
            dlp = 0
            msv = 0

            if modality == "CT" and "protocol" in series_desc:
                dlp = extract_total_dlp(ds)
                if dlp:
                    if "head" in study_desc or "brain" in study_desc:
                        k = 0.0021
                    elif "neck" in study_desc:
                        k = 0.0059
                    elif "chest" in study_desc:
                        k = 0.014
                    elif "abdomen" in study_desc or "pelvis" in study_desc:
                        k = 0.015
                    msv = dlp * k
            elif modality.startswith("CR") or modality.startswith("DX"):
                kvp = float(getattr(ds, "KVP", 0))
                mas = float(getattr(ds, "Exposure", 0))
                if mas == 0:
                    current = float(getattr(ds, "XRayTubeCurrent", 0))
                    time = float(getattr(ds, "ExposureTime", 0)) / 1000  # ms to sec
                    mas = current * time
                if kvp and mas:
                    k = 0.02  # assumed for x-ray
                    msv = kvp * mas * k
            else:
                continue  # تجاهل أي فحوصات مش مطابقة

            key = (
                name, date_obj.date(),
                getattr(ds, "PatientID", ""),
                getattr(ds, "AccessionNumber", "")
            )

            img = None
            if 'PixelData' in ds:
                arr = ds.pixel_array
                if arr.dtype != 'uint8':
                    arr = (arr / arr.max() * 255).astype('uint8')
                img_pil = Image.fromarray(arr).convert("L")
                img_pil.thumbnail((400, 400))
                img = ImageTk.PhotoImage(img_pil)

            if key not in temp_cases:
                temp_cases[key] = {
                    "Name": name,
                    "Date": date_obj,
                    "CTDIvol": 0,
                    "DLP": dlp or 0,
                    "mSv": msv,
                    "kFactor": k,
                    "Sex": getattr(ds, "PatientSex", ""),
                    "DOB": getattr(ds, "PatientBirthDate", ""),
                    "PatientID": getattr(ds, "PatientID", ""),
                    "Accession": getattr(ds, "AccessionNumber", ""),
                    "Images": [],
                    "Path": path,
                    "Modality": modality,
                    "Dataset": ds
                }

            if img:
                temp_cases[key]["Images"].append(img)

            hl7_msg = convert_to_hl7_from_table(temp_cases[key])
            hl7_filename = f"{HL7_DIR}/{name}_{date_obj.strftime('%Y%m%d')}_{temp_cases[key]['PatientID']}.hl7"
            with open(hl7_filename, "w") as f:
                f.write(hl7_msg)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to process file {path}.\nError: {e}")

    all_data.extend(temp_cases.values())

    # ✅ الحساب التراكمي والسنوي
    patient_records = {}
    for d in all_data:
        pid = d["PatientID"]
        patient_records.setdefault(pid, []).append((d["Date"], d["mSv"]))

    accumulated_dose_dict = {}
    dose_per_year_dict = {}

    for pid, records in patient_records.items():
        records.sort()
        total = 0
        for date, dose in records:
            total += dose
            accumulated_dose_dict[(pid, date)] = total

        for current_date, _ in records:
            year_start = current_date - timedelta(days=364)
            total_year = sum(d for date, d in records if year_start <= date <= current_date)
            dose_per_year_dict[(pid, current_date)] = total_year

    for d in all_data:
        pid = d["PatientID"]
        dt = d["Date"]
        d["AccumulatedDose"] = accumulated_dose_dict.get((pid, dt), 0)
        d["DosePerYear"] = dose_per_year_dict.get((pid, dt), 0)

    display_text_data()



# ================================================================
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
    start_date_str = start_date_var.get().strip()
    end_date_str = end_date_var.get().strip()

    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d") if start_date_str else None
    except ValueError:
        start_date = None

    try:
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d") if end_date_str else None
    except ValueError:
        end_date = None

    for data in all_data:
        match_name = name_filter in data["Name"].lower()
        date = data["Date"]

        match_date = True
        if start_date and date < start_date:
            match_date = False
        if end_date and date > end_date:
            match_date = False

        if match_name and match_date:
            filtered.append(data)
    # جمع بيانات المرضى حسب الاسم
    # جمع بيانات الدراسة حسب StudyID
    patient_records = {}
    for data in all_data:
        patient_id = data["PatientID"]
        dose = data["mSv"]
        date = data["Date"]
        if patient_id not in patient_records:
            patient_records[patient_id] = []
        patient_records[patient_id].append((date, dose))

    # حساب الجرعة التراكمية لكل مريض (تجميع تدريجي)
    accumulated_dose_dict = {}
    for patient_id in patient_records:
        records = patient_records[patient_id]
        records.sort(key=lambda x: x[0])  # ترتيب حسب التاريخ
        total_dose = 0
        for date, dose in records:
            total_dose += dose
            accumulated_dose_dict[(patient_id, date)] = round(total_dose, 2)

        # حساب الجرعة السنوية لكل فترة 365 يوم منفصلة لكل مريض
    dose_per_year_dict = {}

    for patient_id in patient_records:
        records = sorted(patient_records[patient_id], key=lambda x: x[0])
        if not records:
            continue

        first_date = records[0][0]

        for current_date, _ in records:
            if current_date == first_date:
                dose_per_year_dict[(patient_id, current_date)] = 0.0
                continue

            start_date = current_date - timedelta(days=364)
            total_dose_year = 0.0
            for date, dose in records:
                if start_date <= date <= current_date:
                    total_dose_year += dose

            dose_per_year_dict[(patient_id, current_date)] = round(total_dose_year, 2)

    # تحديد ترتيب الأعمدة حسب اختيار المستخدم
    sort_option = sort_var.get()

    # تعيين ترتيب الأعمدة حسب الفرز (Name أو Date)
    if sort_option == "Date":
        headers = ["Select", "Date", "Patient Name", "Patient ID", "Modality", "Dose (mSv)", "Total Accumulated Dose", "Dose Per Year"]
        def sort_key(x): return x["Date"]
        col_indices = {
            "select": 0,
            "date": 1,
            "name": 2,
            "patientid": 3,
            "modality": 4,
            "dose": 5,
            "accumulated": 6,
            "per_year": 7
        }
    else:
        # Default or "Name"
        headers = ["Select", "Patient Name", "Date", "Patient ID", "Modality", "Dose (mSv)", "Total Accumulated Dose", "Dose Per Year"]
        def sort_key(x): return x["Name"].lower()
        col_indices = {
            "select": 0,
            "name": 1,
            "date": 2,
            "patientid": 3,
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

        patient_id = data["PatientID"]
        accumulated_dose = accumulated_dose_dict.get((patient_id, date), 0)
        dose_per_year = dose_per_year_dict.get((patient_id, date), 0)

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

        add_label(row, col_indices["patientid"], str(data["PatientID"]))
        add_label(row, col_indices["modality"], data["Modality"])
        add_label(row, col_indices["dose"], f"{data['mSv']:.5f}")

        add_label(row, col_indices["accumulated"], f"{accumulated_dose:.5f}")
        add_label(row, col_indices["per_year"], f"{dose_per_year:.5f}")

    # ضبط أوزان الأعمدة لجعلها ريسبونسف
    for col in range(len(headers)):
        scroll_frame.grid_columnconfigure(col, weight=1)

    # ضبط عمود select ليكون ضيق جدا
    scroll_frame.grid_columnconfigure(col_indices["select"], weight=0, minsize=40)



def show_selected_cases_images():
    for var, case in check_vars:
        if var.get():
            show_case_images(case)





# def show_selected_cases_images():
#     selected = [data for var, data in check_vars if var.get()]
#     if len(selected) not in [2, 4]:
#         messagebox.showwarning("Selection Error", "Please select exactly 2 or 4 cases to display.")
#         return

#     new_win = ctk.CTkToplevel()
#     new_win.title("Selected Cases Images and Info")
#     new_win.geometry("1000x700")

#     container = ctk.CTkScrollableFrame(new_win, corner_radius=10)
#     container.pack(fill="both", expand=True, padx=10, pady=10)

#     for i, case in enumerate(selected):
#         frame = ctk.CTkFrame(container, corner_radius=10, border_width=1)
#         frame.grid(row=0, column=i, padx=10, pady=10, sticky="n")

#         images = case.get("Images", [])
#         if not images and "Dataset" in case:
#             ds = case["Dataset"]
#             if 'PixelData' in ds:
#                 img_pil = Image.fromarray(ds.pixel_array)
#                 img_pil.thumbnail((300, 300))
#                 img_tk = ImageTk.PhotoImage(img_pil)
#                 label_img = ctk.CTkLabel(frame, image=img_tk)
#                 label_img.image = img_tk
#                 label_img.pack(pady=5)
#         else:
#             for img_tk in images:
#                 label_img = ctk.CTkLabel(frame, image=img_tk)
#                 label_img.image = img_tk
#                 label_img.pack(pady=5)

#         info_text = (
#             f"Name: {case['Name']}\n"
#             f"Date: {case['Date'].strftime('%Y-%m-%d')}\n"
#             f"Study ID: {case['StudyID']}\n"
#             f"Modality: {case['Modality']}\n"
#             f"Dose (mSv): {case['mSv']:.5f}\n"
#             f"Accumulated Dose: {case.get('AccumulatedDose', 0):.5f}\n"
#             f"Dose Per Year: {case.get('DosePerYear', 0):.5f}"
#         )
#         label_info = ctk.CTkLabel(frame, text=info_text, justify="left")
#         label_info.pack(pady=5)

#     for i in range(len(selected)):
#         container.grid_columnconfigure(i, weight=1)












def show_case_images(case):
    window = ctk.CTkToplevel()
    window.title(f"Images for {case['Name']} - {case['Date'].strftime('%Y-%m-%d')}")
    window.geometry("900x700")

    index = 0
    images = case.get("Images", [])

    img_label = ctk.CTkLabel(window, text="No Image")
    img_label.pack(pady=10)

    # ===== معلومات الحالة =====
    info_text = (
        f"👤 Name: {case['Name']}\n"
        f"🆔 Patient ID: {case['PatientID']}\n"
        f"📷 Modality: {case['Modality']}\n"
        f"📅 Date: {case['Date'].strftime('%Y-%m-%d')}\n"
        f"💉 Dose (mSv): {case['mSv']:.5f}\n"
        f"📊 Accumulated Dose: {case.get('AccumulatedDose', 0):.5f}"
    )
    info_label = ctk.CTkLabel(window, text=info_text, justify="left", anchor="w")
    info_label.pack(pady=5)

    counter_label = ctk.CTkLabel(window, text="")
    counter_label.pack()

    def update_image():
        nonlocal index
        if 0 <= index < len(images):
            img = images[index]
            img_label.configure(image=img, text="")
            img_label.image = img
            counter_label.configure(text=f"Image {index + 1} of {len(images)}")
        else:
            img_label.configure(image=None, text="No Image")
            counter_label.configure(text="")

    def next_img():
        nonlocal index
        if index < len(images) - 1:
            index += 1
            update_image()

    def prev_img():
        nonlocal index
        if index > 0:
            index -= 1
            update_image()

    btn_frame = ctk.CTkFrame(window)
    btn_frame.pack(pady=10)

    prev_btn = ctk.CTkButton(btn_frame, text="⏮ Previous", command=prev_img)
    prev_btn.pack(side="left", padx=20)

    next_btn = ctk.CTkButton(btn_frame, text="Next ⏭", command=next_img)
    next_btn.pack(side="right", padx=20)

    update_image()















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
    hl7_filename = f"{HL7_DIR}/{data['Name']}_{data['Date'].strftime('%Y%m%d')}_{data['PatientID']}.hl7"
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
            f"🆔 ID: {data['PatientID']}\n"
            f"📅 Date: {data['Date'].strftime('%Y-%m-%d')}\n"
            f"🧬 Type: {data['Modality']}\n"
            f"☢ Dose: {data['mSv']:.5f} mSv\n"
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
# ctk.CTkButton(root, text="DICOM Files", command=read_dicom_files, width=120, height=35).place(relx=0.01, rely=0.22)
# ctk.CTkButton(root, text="DICOM Folder", command=read_dicom_folder, width=120, height=35).place(relx=0.01, rely=0.27)
# ctk.CTkButton(root, text="HL7 Message", command=show_hl7_for_selected, width=120, height=35).place(relx=0.01, rely=0.32)
# ctk.CTkButton(root, text="Selected Cases", command=show_selected_cases, width=120, height=35).place(relx=0.01, rely=0.37)
# ctk.CTkButton(root, text="Delete Cases", command=delete_selected, width=120, height=35).place(relx=0.01, rely=0.42)
# ألوان موحدة للأزرار – Flat modern look
BUTTON_COLOR = "#2563eb"        # أزرق هادئ
BUTTON_HOVER = "#1e40af"        # أزرق داكن
DELETE_COLOR = "#dc2626"        # أحمر خفيف
DELETE_HOVER = "#991b1b"        # أحمر داكن

ctk.CTkButton(root, text="📂 DICOM Files", command=read_dicom_files,
              width=140, height=40, fg_color=BUTTON_COLOR, hover_color=BUTTON_HOVER,
              corner_radius=10, font=("Arial", 13, "bold")).place(relx=0.01, rely=0.22)

ctk.CTkButton(root, text="📁 DICOM Folder", command=read_dicom_folder,
              width=140, height=40, fg_color=BUTTON_COLOR, hover_color=BUTTON_HOVER,
              corner_radius=10, font=("Arial", 13, "bold")).place(relx=0.01, rely=0.28)

ctk.CTkButton(root, text="💬 HL7 Message", command=show_hl7_for_selected,
              width=140, height=40, fg_color="#059669", hover_color="#047857",
              corner_radius=10, font=("Arial", 13, "bold")).place(relx=0.01, rely=0.34)

ctk.CTkButton(root, text="🧾 Selected Cases", command=show_selected_cases,
              width=140, height=40, fg_color="#64748b", hover_color="#475569",
              corner_radius=10, font=("Arial", 13, "bold")).place(relx=0.01, rely=0.40)

ctk.CTkButton(root, text="❌ Delete Cases", command=delete_selected,
              width=140, height=40, fg_color=DELETE_COLOR, hover_color=DELETE_HOVER,
              corner_radius=10, font=("Arial", 13, "bold")).place(relx=0.01, rely=0.46)
ctk.CTkButton(root, text="❌ Show Cases", command=show_selected_cases_images,
              width=140, height=40, fg_color=DELETE_COLOR, hover_color=DELETE_HOVER,
              corner_radius=10, font=("Arial", 13, "bold")).place(relx=0.01, rely=0.52)              
# خيارات الفلترة والترتيب بجانب الأزرار
sort_var = ctk.StringVar(value="Name")
ctk.CTkLabel(root, text="Sort by:",fg_color="white", text_color="black").place(relx=0.78, rely=0.08)
ctk.CTkOptionMenu(root, variable=sort_var, values=["Name", "Date"], command=lambda _: display_text_data()).place(relx=0.82, rely=0.08)

# إطار لصف الفلاتر الثلاثة (في منتصف الواجهة)
filters_frame = ctk.CTkFrame(root, fg_color="white")
filters_frame.place(relx=0.5, rely=0.08, anchor="n")  # في منتصف العرض

# فلتر الاسم
name_filter_var = ctk.StringVar()
ctk.CTkLabel(filters_frame, text="Name:", text_color="black").pack(side="left", padx=(0, 5))
ctk.CTkEntry(filters_frame, placeholder_text="Filter by Name", textvariable=name_filter_var, width=140).pack(side="left", padx=(0, 20))
name_filter_var.trace_add("write", lambda *args: display_text_data())

# فلتر من تاريخ
start_date_var = ctk.StringVar()
ctk.CTkLabel(filters_frame, text="From Date:", text_color="black").pack(side="left", padx=(0, 5))
ctk.CTkEntry(filters_frame, placeholder_text="YYYY-MM-DD", textvariable=start_date_var, width=130).pack(side="left", padx=(0, 20))
start_date_var.trace_add("write", lambda *args: display_text_data())
# فلتر إلى تاريخ
end_date_var = ctk.StringVar()
ctk.CTkLabel(filters_frame, text="To Date:", text_color="black").pack(side="left", padx=(0, 5))
ctk.CTkEntry(filters_frame, placeholder_text="YYYY-MM-DD", textvariable=end_date_var, width=130).pack(side="left")
end_date_var.trace_add("write", lambda *args: display_text_data())
# محتوى البيانات
# shadow frame (أسود فاتح كخلفية خفيفة)
shadow_frame = ctk.CTkFrame(root, fg_color="#416dcc", corner_radius=12)
shadow_frame.place(relx=0.14, rely=0.15, relwidth=0.80, relheight=0.70)
# frame الأساسي فوق الـ shadow
content_frame = ctk.CTkFrame(root, fg_color="#ffffff", corner_radius=10)

content_frame.place(relx=0.15, rely=0.16, relwidth=0.78, relheight=0.68)
# رسالة ترحيبية
welcome_label = ctk.CTkLabel(content_frame, text="Click here to select DICOM files",
text_color="blue", font=ctk.CTkFont(size=20, weight="bold"), cursor="hand2")
welcome_label.pack(expand=True)
welcome_label.bind("<Button-1>", lambda e: read_dicom_files())
root.mainloop()

