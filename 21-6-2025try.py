import os
import pydicom

def is_dicom(file_path):
    """تحقق إذا كان الملف DICOM حقيقي من محتواه الداخلي"""
    try:
        with open(file_path, 'rb') as f:
            f.seek(128)
            return f.read(4) == b'DICM'
    except:
        return False

def load_all_dicoms(folder_path):
    dicom_files = []
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path) and is_dicom(file_path):
            dicom_files.append(file_path)
    return dicom_files

# اختبار
folder = "path_to_your_folder"
dicom_files = load_all_dicoms(folder)
print("DICOM files found:", dicom_files)
