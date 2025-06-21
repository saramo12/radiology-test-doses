import os
import pydicom
import tkinter as tk
from tkinter import filedialog, messagebox

def is_examination_report(ds):
    return (
        getattr(ds, "Modality", "") == "SR" and
        "DOSE" in str(getattr(ds, "SeriesDescription", "")).upper()
    )

def extract_dose_info_from_report(ds):
    ctdi_vol = 0
    dlp = 0
    region = "Unknown"
    
    for item in ds.get("ContentSequence", []):
        text = str(getattr(item, "TextValue", "")).upper()
        if "CTDI" in text:
            try:
                ctdi_vol = float(item.MeasuredValueSequence[0].NumericValue)
            except:
                pass
        if "DLP" in text:
            try:
                dlp = float(item.MeasuredValueSequence[0].NumericValue)
            except:
                pass
        if "HEAD" in text or "CHEST" in text or "ABDOMEN" in text or "PELVIS" in text:
            region = text

    return ctdi_vol, dlp, region

def get_conversion_factor(region_text):
    region_text = region_text.lower()
    if "head" in region_text:
        return 0.0021
    elif "neck" in region_text:
        return 0.0059
    elif "chest" in region_text:
        return 0.014
    elif "abdomen" in region_text or "pelvis" in region_text:
        return 0.015
    else:
        return 0.015  # default

def process_case_folder_gui():
    folder_path = filedialog.askdirectory(title="اختاري فولدر الحالة")
    if not folder_path:
        return

    examination_report = None
    for fname in os.listdir(folder_path):
        path = os.path.join(folder_path, fname)
        if not os.path.isfile(path):
            continue
        try:
            ds = pydicom.dcmread(path)
            if is_examination_report(ds):
                examination_report = ds
                break
        except:
            continue

    if examination_report is None:
        messagebox.showerror("خطأ", "لم يتم العثور على تقرير الجرعة (Dose Report).")
        return

    ctdi, dlp, region = extract_dose_info_from_report(examination_report)
    k = get_conversion_factor(region)
    effective_dose = dlp * k
    patient = getattr(examination_report, "PatientName", "Unknown")
    date = getattr(examination_report, "StudyDate", "")

    result = (
        f"✅ Patient: {patient}\n"
        f"📅 Date: {date}\n"
        f"🧠 Region: {region}\n"
        f"📏 CTDIvol: {ctdi:.4f}\n"
        f"📏 DLP: {dlp:.4f}\n"
        f"🧮 k-factor: {k}\n"
        f"✅ Effective Dose (mSv): {effective_dose:.5f}"
    )
    messagebox.showinfo("نتيجة الحساب", result)


# واجهة المستخدم
root = tk.Tk()
root.title("حساب Effective Dose من Dose Report")
root.geometry("400x200")

label = tk.Label(root, text="اضغطي الزر لاختيار فولدر الحالة:", font=("Arial", 14))
label.pack(pady=20)

btn = tk.Button(root, text="اختيار فولدر", font=("Arial", 12), command=process_case_folder_gui)
btn.pack(pady=10)

root.mainloop()
