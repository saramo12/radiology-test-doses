import os
import pydicom

def is_dose_report(ds):
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

def process_case_folder(folder_path):
    dose_report = None

    for fname in os.listdir(folder_path):
        path = os.path.join(folder_path, fname)
        if not os.path.isfile(path):
            continue
        try:
            ds = pydicom.dcmread(path)
            if is_dose_report(ds):
                dose_report = ds
                break
        except:
            continue

    if dose_report is None:
        print("❌ Dose report not found.")
        return

    ctdi, dlp, region = extract_dose_info_from_report(dose_report)
    k = get_conversion_factor(region)
    effective_dose = dlp * k

    print("✅ Patient:", getattr(dose_report, "PatientName", "Unknown"))
    print("📅 Date:", getattr(dose_report, "StudyDate", ""))
    print("🧠 Region:", region)
    print("📏 CTDIvol:", ctdi)
    print("📏 DLP:", dlp)
    print("✅ Effective Dose (mSv):", round(effective_dose, 4))
