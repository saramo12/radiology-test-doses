import customtkinter as ctk
from tkinter import filedialog, messagebox, simpledialog
from PIL import Image, ImageTk
import pydicom
import os
from datetime import datetime

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")
CSV_FILE = "rad.csv"
HL7_DIR = "hl7_messages"
os.makedirs(HL7_DIR, exist_ok=True)

all_data = []
selected_cases = []
image_refs = []  # مهم جداً لتخزين الصور حتى لا يتم جمعها من الذاكرة


def convert_to_hl7(ds, msv):
    name = str(getattr(ds, "PatientName", "Unknown"))
    date = getattr(ds, "StudyDate", "00000000")
    ctdi = float(getattr(ds, "CTDIvol", 0))
    dlp = float(getattr(ds, "DLP", 0))
    gender = getattr(ds, "PatientSex", "")
    dob = getattr(ds, "PatientBirthDate", "")
    study_id = getattr(ds, "StudyID", "")
    accession = getattr(ds, "AccessionNumber", "")
    modality = getattr(ds, "Modality", "Unknown")

    return f"""MSH|^~\\&|CTApp|Hospital|PACS|Hospital|{date}||ORU^R01|MSG00001|P|2.3
PID|||{name}||{dob}|{gender}||
OBR|||{study_id}^{accession}|||{modality}
OBX|1|NM|CTDIvol||{ctdi}|mGy|||
OBX|2|NM|DLP||{dlp}|mGy*cm|||
OBX|3|NM|EffectiveDose||{msv:.2f}|mSv|||"""


def read_dicom_files():
    global image_refs
    files = filedialog.askopenfilenames(filetypes=[("DICOM files", "*.dcm")])
    if not files:
        return

    all_data.clear()
    selected_cases.clear()
    image_refs.clear()

    unique_cases = {}
    for path in files:
        try:
            ds = pydicom.dcmread(path)
            name = str(getattr(ds, "PatientName", "Unknown"))
            ctdi = float(getattr(ds, "CTDIvol", 0))
            dlp = float(getattr(ds, "DLP", 0))
            date_str = getattr(ds, "StudyDate", "00000000")
            modality = getattr(ds, "Modality", "Unknown")

            try:
                date_obj = datetime.strptime(date_str, "%Y%m%d")
            except:
                date_obj = datetime.now()

            msv = ctdi * 0.014

            img = None
            if 'PixelData' in ds:
                try:
                    arr = ds.pixel_array
                    if len(arr.shape) == 3 and arr.shape[0] == 3:
                        arr = arr.transpose(1, 2, 0)
                    pil_img = Image.fromarray(arr)
                    pil_img.thumbnail((120, 120))
                    img = ImageTk.PhotoImage(pil_img)
                    image_refs.append(img)
                except:
                    img = None

            key = (name, date_obj.date(), modality, getattr(ds, "StudyID", ""), getattr(ds, "AccessionNumber", ""))
            if key not in unique_cases:
                unique_cases[key] = {
                    "Name": name,
                    "Date": date_obj,
                    "CTDIvol": ctdi,
                    "DLP": dlp,
                    "mSv": msv,
                    "Sex": getattr(ds, "PatientSex", ""),
                    "DOB": getattr(ds, "PatientBirthDate", ""),
                    "StudyID": getattr(ds, "StudyID", ""),
                    "Accession": getattr(ds, "AccessionNumber", ""),
                    "Modality": modality,
                    "Image": img,
                    "Path": path,
                    "Ds": ds
                }

                hl7_msg = convert_to_hl7(ds, msv)
                hl7_filename = f"{HL7_DIR}/{name}_{date_obj.strftime('%Y%m%d')}_{modality}.hl7"
                with open(hl7_filename, "w") as f:
                    f.write(hl7_msg)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to process file {path}.\nError: {e}")

    all_data.extend(unique_cases.values())
    display_text_data()


def display_text_data():
    for widget in content_frame.winfo_children():
        widget.destroy()

    sort_option = sort_var.get()
    sorted_data = sorted(all_data, key=lambda x: x[sort_option])

    # إنشاء إطار لكل عمود عموديًا
    columns = {
        "Select": [],
        "Image": [],
        "Name": [],
        "Date": [],
        "Modality": [],
        "CTDIvol (mGy)": [],
        "DLP (mGy·cm)": [],
        "Dose (mSv)": [],
        "Sex": [],
        "DOB": []
    }

    # رؤوس الأعمدة
    header_font = ctk.CTkFont(size=14, weight="bold")
    for col_idx, col_name in enumerate(columns.keys()):
        lbl = ctk.CTkLabel(content_frame, text=col_name, font=header_font, anchor="center")
        lbl.grid(row=0, column=col_idx, padx=8, pady=5)

    # ملء البيانات لكل عمود في عموده الخاص
    for row_idx, data in enumerate(sorted_data, start=1):
        var = ctk.BooleanVar(value=(data in selected_cases))

        # خانة الاختيار
        chk = ctk.CTkCheckBox(content_frame, variable=var,
                              command=lambda d=data, v=var: on_check(d, v))
        chk.grid(row=row_idx, column=0, padx=8, pady=6)

        # صورة صغيرة إن وجدت
        if data["Image"]:
            img_lbl = ctk.CTkLabel(content_frame, image=data["Image"], text="")
            img_lbl.image = data["Image"]
            img_lbl.grid(row=row_idx, column=1, padx=8, pady=6)
        else:
            img_lbl = ctk.CTkLabel(content_frame, text="No Image", fg_color="#ddd", width=120, height=120)
            img_lbl.grid(row=row_idx, column=1, padx=8, pady=6)

        ctk.CTkLabel(content_frame, text=data["Name"], anchor="w").grid(row=row_idx, column=2, padx=8, pady=6)
        ctk.CTkLabel(content_frame, text=data["Date"].strftime("%Y-%m-%d")).grid(row=row_idx, column=3, padx=8, pady=6)
        ctk.CTkLabel(content_frame, text=data["Modality"]).grid(row=row_idx, column=4, padx=8, pady=6)
        ctk.CTkLabel(content_frame, text=f"{data['CTDIvol']:.2f}").grid(row=row_idx, column=5, padx=8, pady=6)
        ctk.CTkLabel(content_frame, text=f"{data['DLP']:.2f}").grid(row=row_idx, column=6, padx=8, pady=6)
        ctk.CTkLabel(content_frame, text=f"{data['mSv']:.2f}").grid(row=row_idx, column=7, padx=8, pady=6)
        ctk.CTkLabel(content_frame, text=data["Sex"]).grid(row=row_idx, column=8, padx=8, pady=6)
        ctk.CTkLabel(content_frame, text=data["DOB"]).grid(row=row_idx, column=9, padx=8, pady=6)


def on_check(data, var):
    if var.get():
        if data in selected_cases:
            return
        if len(selected_cases) >= 4:
            messagebox.showwarning("Limit Reached", "You can only select up to 4 cases.")
            var.set(False)
            return
        selected_cases.append(data)
    else:
        if data in selected_cases:
            selected_cases.remove(data)


def delete_selected_cases():
    if not selected_cases:
        messagebox.showinfo("Info", "No cases selected to delete.")
        return
    for case in selected_cases[:]:
        if case in all_data:
            all_data.remove(case)
        selected_cases.remove(case)
    display_text_data()


def show_hl7_messages():
    if not selected_cases:
        messagebox.showinfo("Info", "No cases selected to view HL7 message.")
        return

    password = simpledialog.askstring("Password", "Enter password to view HL7 messages:", show='*')
    if password != "admin123":
        messagebox.showerror("Unauthorized", "Incorrect password.")
        return

    combined_msg = ""
    for data in selected_cases:
        filename = f"{HL7_DIR}/{data['Name']}_{data['Date'].strftime('%Y%m%d')}_{data['Modality']}.hl7"
        if os.path.exists(filename):
            with open(filename, "r") as f:
                hl7 = f.read()
            combined_msg += f"--- HL7 Message for {data['Name']} on {data['Date'].strftime('%Y-%m-%d')} ({data['Modality']}) ---\n"
            combined_msg += hl7 + "\n\n"
        else:
            combined_msg += f"HL7 message not found for {data['Name']} on {data['Date'].strftime('%Y-%m-%d')} ({data['Modality']})\n\n"

    top = ctk.CTkToplevel()
    top.title("HL7 Messages")
    top.geometry("700x500")

    textbox = ctk.CTkTextbox(top, wrap="word")
    textbox.pack(expand=True, fill="both", padx=10, pady=10)
    textbox.insert("0.0", combined_msg)
    textbox.configure(state="disabled")


def show_selected_cases():
    if len(selected_cases) not in [2, 4]:
        messagebox.showwarning("Selection Error", "Please select exactly 2 or 4 cases.")
        return

    top = ctk.CTkToplevel()
    top.title("Selected Cases Viewer")
    top.geometry("1100x700")
    top.lift()  # النافذة تظهر قدام النوافذ الأخرى

    for idx, data in enumerate(selected_cases):
        row = idx // 2
        col = idx % 2

        frame = ctk.CTkFrame(top)
        frame.grid(row=row, column=col, padx=15, pady=15)

        if data["Image"]:
            img_label = ctk.CTkLabel(frame, image=data["Image"], text="")
            img_label.image = data["Image"]
            img_label.pack(pady=10)

        info = (
            f"👤 Name: {data['Name']}\n"
            f"🆔 ID: {data['StudyID']}\n"
            f"📅 Date: {data['Date'].date()}\n"
            f"🧬 Modality: {data['Modality']}\n"
            f"☢ Dose: {data['mSv']:.2f} mSv\n"
            f"🧪 CTDIvol: {data['CTDIvol']:.2f} mGy\n"
            f"📏 DLP: {data['DLP']:.2f} mGy·cm\n"
            f"⚧ Sex: {data['Sex']}\n"
            f"🎂 DOB: {data['DOB']}"
        )
        ctk.CTkLabel(frame, text=info, justify="left", font=ctk.CTkFont(size=13)).pack(pady=5)


root = ctk.CTk()
root.title("DICOM Viewer - Elegant Display")
root.geometry("1300x900")

# إضافة صورة الخلفية
bg_img = Image.open("g.jpg").resize((1300, 900))
bg_img_tk = ImageTk.PhotoImage(bg_img)
background_label = ctk.CTkLabel(root, image=bg_img_tk)
background_label.place(x=0, y=0, relwidth=1, relheight=1)

select_button = ctk.CTkButton(root, text="📂 Select DICOM Files", command=read_dicom_files,
                              font=ctk.CTkFont(size=16, weight="bold"))
select_button.pack(pady=12)

sort_var = ctk.StringVar(value="Name")
sort_frame = ctk.CTkFrame(root)
sort_frame.pack(pady=6)
ctk.CTkLabel(sort_frame, text="Sort by:", font=ctk.CTkFont(size=14)).pack(side="left", padx=8)
ctk.CTkOptionMenu(sort_frame, variable=sort_var, values=["Name", "Date"], command=lambda e: display_text_data()).pack(side="left")

hl7_btn = ctk.CTkButton(root, text="Show HL7 Messages", command=show_hl7_messages,
                        font=ctk.CTkFont(size=14, weight="bold"))
hl7_btn.pack(pady=6)

content_frame = ctk.CTkFrame(root, fg_color="#f8f9fa", corner_radius=15)
content_frame.pack(expand=True, fill="both", padx=12, pady=12)

btn_frame = ctk.CTkFrame(root)
btn_frame.pack(pady=10)
ctk.CTkButton(btn_frame, text="Delete Selected", command=delete_selected_cases).pack(side="left", padx=12)
ctk.CTkButton(btn_frame, text="View Selected Cases", command=show_selected_cases).pack(side="left", padx=12)

root.mainloop()
