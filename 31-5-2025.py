import customtkinter as ctk
from tkinter import filedialog, messagebox, simpledialog, IntVar
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
selected_vars = []  # to hold IntVars for checkboxes

# Convert DICOM to HL7
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
    selected_vars.clear()
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

            img = None
            if 'PixelData' in ds:
                img = Image.fromarray(ds.pixel_array)
                img.thumbnail((200, 200))
                img = ImageTk.PhotoImage(img)

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
                "Path": path
            }

            all_data.append(data_dict)

            hl7_msg = convert_to_hl7(ds, msv)
            hl7_filename = f"{HL7_DIR}/{name}_{date_obj.strftime('%Y%m%d')}.hl7"
            with open(hl7_filename, "w") as f:
                f.write(hl7_msg)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to process file {path}.\nError: {e}")

    display_table_data()
# زر جديد لعرض HL7 لجميع الحالات المختارة (2 أو 4)
def show_selected_hl7_messages():
    selected = [d for var, d in selected_vars if var.get() == 1]
    if len(selected) not in [2, 4]:
        messagebox.showwarning("Selection Error", "Please select exactly 2 or 4 cases.")
        return

    password = simpledialog.askstring("Password", "Enter password to view HL7 messages:", show='*')
    if password != "admin123":
        messagebox.showerror("Unauthorized", "Incorrect password.")
        return

    hl7_texts = []
    for data in selected:
        filename = f"{HL7_DIR}/{data['Name']}_{data['Date'].strftime('%Y%m%d')}.hl7"
        if os.path.exists(filename):
            with open(filename, "r") as f:
                hl7 = f.read()
            hl7_texts.append(f"--- HL7 for {data['Name']} ({data['Date'].strftime('%Y-%m-%d')}) ---\n{hl7}\n")
        else:
            hl7_texts.append(f"HL7 message not found for {data['Name']}.\n")

    hl7_window = ctk.CTkToplevel()
    hl7_window.title("HL7 Messages Viewer")
    hl7_window.geometry("800x600")
    hl7_window.attributes('-topmost', True)

    text_widget = ctk.CTkTextbox(hl7_window, width=780, height=580)
    text_widget.pack(padx=10, pady=10, fill="both", expand=True)
    text_widget.insert("0.0", "\n\n".join(hl7_texts))
    text_widget.configure(state="disabled")

# ... 

# فوق الجدول، نضيف زر HL7 مع الأزرار الأخرى
hl7_button = ctk.CTkButton(root, text="🗒 View HL7 for Selected", command=show_selected_hl7_messages)
hl7_button.place(relx=0.42, rely=0.03)
def display_table_data():
    for widget in content_frame.winfo_children():
        widget.destroy()

    # headers
    headers = ["Select", "Name", "ID", "Date", "Dose (mSv)", "CTDIvol (mGy)", "DLP (mGy·cm)", "Sex", "DOB", "HL7", "Delete"]

    # Sort data
    sort_option = sort_var.get()
    sorted_data = sorted(all_data, key=lambda x: x[sort_option])

    # Create header labels
    for col, header in enumerate(headers):
        label = ctk.CTkLabel(content_frame, text=header, font=ctk.CTkFont(size=14, weight="bold"))
        label.grid(row=0, column=col, padx=5, pady=5, sticky="nsew")

    # Clear selected_vars and recreate
    selected_vars.clear()

    for row, data in enumerate(sorted_data, start=1):
        var = IntVar()
        selected_vars.append((var, data))
        checkbox = ctk.CTkCheckBox(content_frame, variable=var)
        checkbox.grid(row=row, column=0, padx=5, pady=5, sticky="nsew")

        ctk.CTkLabel(content_frame, text=data["Name"]).grid(row=row, column=1, padx=5, pady=5, sticky="nsew")
        ctk.CTkLabel(content_frame, text=data["StudyID"]).grid(row=row, column=2, padx=5, pady=5, sticky="nsew")
        ctk.CTkLabel(content_frame, text=data["Date"].strftime("%Y-%m-%d")).grid(row=row, column=3, padx=5, pady=5, sticky="nsew")
        ctk.CTkLabel(content_frame, text=f"{data['mSv']:.2f}").grid(row=row, column=4, padx=5, pady=5, sticky="nsew")
        ctk.CTkLabel(content_frame, text=f"{data['CTDIvol']}").grid(row=row, column=5, padx=5, pady=5, sticky="nsew")
        ctk.CTkLabel(content_frame, text=f"{data['DLP']}").grid(row=row, column=6, padx=5, pady=5, sticky="nsew")
        ctk.CTkLabel(content_frame, text=data["Sex"]).grid(row=row, column=7, padx=5, pady=5, sticky="nsew")
        ctk.CTkLabel(content_frame, text=data["DOB"]).grid(row=row, column=8, padx=5, pady=5, sticky="nsew")

        hl7_btn = ctk.CTkButton(content_frame, text="View HL7", width=80,
                                command=lambda d=data: show_hl7_message(d))
        hl7_btn.grid(row=row, column=9, padx=5, pady=5)

        delete_btn = ctk.CTkButton(content_frame, text="Delete", width=80,
                                   command=lambda d=data: delete_case(d))
        delete_btn.grid(row=row, column=10, padx=5, pady=5)

def show_hl7_message(data):
    password = simpledialog.askstring("Password", "Enter password to view HL7 message:", show='*')
    if password != "admin123":
        messagebox.showerror("Unauthorized", "Incorrect password.")
        return

    filename = f"{HL7_DIR}/{data['Name']}_{data['Date'].strftime('%Y%m%d')}.hl7"
    if os.path.exists(filename):
        with open(filename, "r") as f:
            hl7 = f.read()
        messagebox.showinfo("HL7 Message", hl7)
    else:
        messagebox.showerror("Not Found", "HL7 message not found.")

def delete_case(data):
    if data in all_data:
        all_data.remove(data)
    # Also remove from selected_vars any var related to this data
    for var, d in selected_vars[:]:
        if d == data:
            selected_vars.remove((var, d))
    display_table_data()

def show_selected_cases():
    selected = [d for var, d in selected_vars if var.get() == 1]
    if len(selected) not in [2, 4]:
        messagebox.showwarning("Selection Error", "Please select exactly 2 or 4 cases.")
        return

    top = ctk.CTkToplevel()
    top.title("Selected Cases Viewer")
    top.geometry("1100x700")
    top.attributes('-topmost', True)  # Keep window on top

    for idx, data in enumerate(selected):
        row = idx // 2
        col = idx % 2

        frame = ctk.CTkFrame(top, corner_radius=10)
        frame.grid(row=row, column=col, padx=20, pady=20, sticky="nsew")

        if data["Image"]:
            img_label = ctk.CTkLabel(frame, image=data["Image"], text="")
            img_label.image = data["Image"]
            img_label.pack(pady=5)

        info = (
            f"👤 Name: {data['Name']}\n"
            f"🆔 ID: {data['StudyID']}\n"
            f"📅 Date: {data['Date'].strftime('%Y-%m-%d')}\n"
            f"🧬 Type: CT\n"
            f"☢ Dose: {data['mSv']:.2f} mSv\n"
            f"🧪 CTDIvol: {data['CTDIvol']} mGy\n"
            f"📏 DLP: {data['DLP']} mGy·cm\n"
            f"⚧ Sex: {data['Sex']}\n"
            f"🎂 DOB: {data['DOB']}"
        )
        ctk.CTkLabel(frame, text=info, justify="left", font=ctk.CTkFont(size=14)).pack(pady=5, padx=10)

root = ctk.CTk()
root.title("DICOM Viewer - Select & Display")
root.geometry("1300x900")

select_button = ctk.CTkButton(root, text="📂 Select DICOM Files", command=read_dicom_files)
select_button.place(relx=0.02, rely=0.03)

view_button = ctk.CTkButton(root, text="👁 View Selected Cases", command=show_selected_cases)
view_button.place(relx=0.22, rely=0.03)

sort_var = ctk.StringVar(value="Date")
ctk.CTkLabel(root, text="Sort by:").place(relx=0.7, rely=0.03)
sort_optionmenu = ctk.CTkOptionMenu(root, variable=sort_var, values=["Date", "Name"], command=lambda _: display_table_data())
sort_optionmenu.place(relx=0.78, rely=0.03)

content_frame = ctk.CTkScrollableFrame(root)
content_frame.place(relx=0.02, rely=0.1, relwidth=0.96, relheight=0.85)

root.mainloop()
