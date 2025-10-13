import os
import csv
import pydicom
import pandas as pd

# Paths
base = "./01_MRI_Data"
notes_file = "./Radiologists Notes for Lumbar Spine MRI Dataset/radiologists_report.csv"
output_csv = "./mri_export/Patient.csv"

# Load radiologist notes into dict {PatientID: Notes}
notes_df = pd.read_csv(notes_file)
notes_dict = dict(zip(notes_df["Patient ID"].astype(str), notes_df["Clinician's Notes"]))

# Prepare output
os.makedirs(os.path.dirname(output_csv), exist_ok=True)
with open(output_csv, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["PatientID", "Sex", "Age", "Weight", "Size", "ClinicalNotes"])

    # Loop over patient folders
    for patient_folder in sorted(os.listdir(base)):
        if not patient_folder.isdigit():
            continue  # skip non-patient folders

        patient_id = str(int(patient_folder))  # "0001" -> "1"

        patient_path = os.path.join(base, patient_folder)

        # Find first .ima file under this patient
        dcm_file = None
        for root, _, files in os.walk(patient_path):
            for file in files:
                if file.lower().endswith(".ima"):
                    dcm_file = os.path.join(root, file)
                    break
            if dcm_file:
                break

        # Extract attributes
        sex, age, weight, size = "", "", "", ""
        if dcm_file:
            try:
                dcm = pydicom.dcmread(dcm_file, stop_before_pixels=True)

                sex = getattr(dcm, "PatientSex", "")
                age = getattr(dcm, "PatientAge", "")
                weight = getattr(dcm, "PatientWeight", "")
                size = getattr(dcm, "PatientSize", "")

            except Exception as e:
                print(f"Warning: Could not read {dcm_file} for patient {patient_id}: {e}")

        # Lookup clinical notes
        notes = notes_dict.get(patient_id, "")

        # Write row
        writer.writerow([patient_id, sex, age, weight, size, notes])

print(f"✅ Patient.csv written to {output_csv}")
