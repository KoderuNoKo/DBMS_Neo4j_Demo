#!/usr/bin/env python3
"""
export_mri_csvs.py

Traverse dataset folder structure and generate:
 - Study.csv
 - Series.csv
 - Image.csv

Schemas implemented:
Study.csv:
    StudyID,Region,Protocol,Timestamp,
    StudyDescription,StudyInstanceUID,BodyPartExamined,ScanningSequence,SequenceVariant,ScanOptions

Series.csv:
    SeriesID,SeriesDescription,SeriesNumber,
    SeriesTime,AcquisitionTime,ContentTime,SequenceName,StudyID

Image.csv:
    ImageID,Filename,SeriesID,<all DICOM keywords as columns...>

Usage:
    python export_mri_csvs.py
"""

import os
import csv
import re
from datetime import datetime
from collections import OrderedDict
import pydicom

# ---------- CONFIG ----------

BASE_DIR = "./01_MRI_Data"                  # top-level dataset folder
OUT_DIR = "./mri_export"                    # output CSV folder
os.makedirs(OUT_DIR, exist_ok=True)
BASE_URL = f"http://localhost:{PORT}/"          # for serving image over http

STUDY_CSV = os.path.join(OUT_DIR, "Study.csv")
SERIES_CSV = os.path.join(OUT_DIR, "Series.csv")
IMAGE_CSV = os.path.join(OUT_DIR, "Image.csv")

# DICOM attributes to extract (by attribute name) for Study and Series
STUDY_DICOM_ATTRS = [
    "StudyDescription",
    "StudyInstanceUID",
    "BodyPartExamined",
    "ScanningSequence",
    "SequenceVariant",
    "ScanOptions",
]

SERIES_DICOM_ATTRS = [
    "SeriesTime",
    "AcquisitionTime",
    "ContentTime",
    "SequenceName",
]

# ---------- HELPERS ----------

def find_first_ima(root_path):
    """Recursively find the first file with .ima extension under root_path."""
    for dirpath, _, files in os.walk(root_path):
        for f in files:
            if f.lower().endswith(".ima"):
                return os.path.join(dirpath, f)
    return None

def parse_study_folder_name(folder_name):
    """
    Parse study folder name like:
      L-SPINE_LSS_20160309_091629_240000
    into Region, Protocol, Timestamp (ISO format with microseconds if available)

    Algorithm:
      - split on '_'
      - Region = first token
      - find first token that matches 8-digit date (YYYYMMDD)
      - protocol = tokens between region and date, joined by '_'
      - time token is next token (expect 6 digits HHMMSS)
      - uid token (microseconds) may be next (6 digits)
      - combine date+time+uid -> parse with %Y%m%d%H%M%S%f, fallback to smaller precisions
    """
    parts = folder_name.split("_")
    region = parts[0] if parts else ""
    date_idx = None
    for i, p in enumerate(parts):
        if re.fullmatch(r"\d{8}", p):
            date_idx = i
            break

    protocol = ""
    timestamp_iso = ""

    if date_idx is not None:
        if date_idx > 1:
            protocol = "_".join(parts[1:date_idx])
        raw_date = parts[date_idx]
        raw_time = parts[date_idx + 1] if date_idx + 1 < len(parts) else ""
        raw_uid = parts[date_idx + 2] if date_idx + 2 < len(parts) else ""

        # form candidates
        cand1 = raw_date + raw_time + raw_uid  # yyyyMMddHHmmssffffff
        cand2 = raw_date + raw_time            # yyyyMMddHHmmss
        cand3 = raw_date                        # yyyyMMdd

        # try parsing progressively
        for fmt, cand in [
            ("%Y%m%d%H%M%S%f", cand1),
            ("%Y%m%d%H%M%S", cand2),
            ("%Y%m%d", cand3),
        ]:
            try:
                dt = datetime.strptime(cand, fmt)
                # produce ISO with microseconds if available
                timestamp_iso = dt.isoformat()
                break
            except Exception:
                continue
    else:
        # No date token found: attempt to see if last token looks like timestamp
        timestamp_iso = ""

    return region, protocol, timestamp_iso

def parse_series_folder_name(folder_name):
    """
    Parse series folder like: T2_TSE_TRA_384_0004 -> description: T2_TSE_TRA_384, number: 4
    If last underscore component is numeric, that's SeriesNumber.
    """
    if "_" in folder_name:
        head, tail = folder_name.rsplit("_", 1)
        if re.fullmatch(r"\d+", tail):
            return head, int(tail.lstrip("0") or "0")
        else:
            return folder_name, ""
    else:
        return folder_name, ""

def parse_image_index_from_filename(filename):
    """
    Extract last numeric group from filename (without extension).
    Example: "LOCALIZER_0_0570_008.ima" -> 8
    """
    base = os.path.splitext(filename)[0]
    groups = re.findall(r"(\d+)", base)
    if groups:
        return int(groups[-1].lstrip("0") or "0")
    return None

def get_attr(ds, keyword, default=""):
    """Safely get attribute value as string."""
    try:
        val = getattr(ds, keyword, default)
        if hasattr(val, "value"):  # DataElement
            val = val.value
        return str(val)
    except Exception:
        return default

def read_dicom_attributes(ima_path, attr_names=None):
    """
    Read a dicom (.ima) file and return a dict of requested attributes (attr_names list),
    or if attr_names is None: return a dict of all dataset element keywords -> str(value).
    Uses stop_before_pixels=True for speed.
    """
    try:
        dcm = pydicom.dcmread(ima_path, stop_before_pixels=True, force=True)
    except Exception as e:
        print(f"Warning: could not read DICOM {ima_path}: {e}")
        return {}

    result = {}
    if attr_names:
        for a in attr_names:
            # some attributes may be nested or not present
            val = get_attr(dcm, a)
            # ensure stringable
            try:
                result[a] = str(val) if val is not None else ""
            except Exception:
                result[a] = ""
    else:
        # collect all keyword attributes
        for elem in dcm:
            key = get_attr(elem, "keyword", None)
            if not key:
                # skip elements without keyword
                continue
            # convert to string safely
            try:
                val = elem.value
                if "(0008,1155)" in str(val):
                    continue
                # avoid huge binary blobs; stop_before_pixels True should prevent PixelData presence
                result[key] = str(val)
            except Exception:
                result[key] = ""
    return result

# ---------- MAIN PROCESS ----------

def main():
    study_rows = []
    series_rows = []
    image_rows = []    # will be list of dicts to allow dynamic columns for image attributes

    study_counter = 1
    series_counter = 1
    image_id_counter = 1

    # iterate patients (top-level folders)
    for patient_folder in sorted(os.listdir(BASE_DIR)):
        patient_path = os.path.join(BASE_DIR, patient_folder)
        if not os.path.isdir(patient_path):
            continue
        # only keep numeric top-level patient folders (skip other files)
        if not re.fullmatch(r"\d+", patient_folder):
            continue
        
        print(f"Processing... Patient {patient_folder}/0575.")

        # iterate studies under patient
        for study_folder in sorted(os.listdir(patient_path)):
            study_path = os.path.join(patient_path, study_folder)
            if not os.path.isdir(study_path):
                continue
            
            # parse study folder name into region/protocol/timestamp
            region, protocol, timestamp_iso = parse_study_folder_name(study_folder)

            # find a representative .ima under the study to read study-level DICOM attrs
            rep_ima = find_first_ima(study_path)
            study_dcm_vals = {}
            if rep_ima:
                study_dcm_vals = read_dicom_attributes(rep_ima, STUDY_DICOM_ATTRS)

            # build study row
            study_row = {
                "StudyID": study_counter,
                "Region": region,
                "Protocol": protocol,
                "Timestamp": timestamp_iso,
            }
            # attach configured study dicom attributes
            for a in STUDY_DICOM_ATTRS:
                study_row[a] = study_dcm_vals.get(a, "")

            study_rows.append(study_row)
            this_study_id = study_counter
            study_counter += 1

            # iterate series under study (direct child folders)
            for series_folder in sorted(os.listdir(study_path)):
                series_path = os.path.join(study_path, series_folder)
                if not os.path.isdir(series_path):
                    continue

                # parse series folder name
                series_desc, series_num = parse_series_folder_name(series_folder)

                # find a representative .ima under the series to read series-level DICOM attrs
                series_rep_ima = find_first_ima(series_path)
                series_dcm_vals = {}
                if series_rep_ima:
                    series_dcm_vals = read_dicom_attributes(series_rep_ima, SERIES_DICOM_ATTRS)

                # build series row
                series_row = {
                    "SeriesID": series_counter,
                    "SeriesDescription": series_desc,
                    "SeriesNumber": series_num,
                    "StudyID": this_study_id,
                }
                for a in SERIES_DICOM_ATTRS:
                    series_row[a] = series_dcm_vals.get(a, "")
                series_rows.append(series_row)
                this_series_id = series_counter
                series_counter += 1

                # iterate image files (.ima) inside series_path
                # (only files in that folder, but find_first_ima finds recursively; here we read all .ima files directly under that folder and subfolders)
                for dirpath, _, files in os.walk(series_path):
                    for fname in sorted(files):
                        if not fname.lower().endswith(".ima"):
                            continue
                        fullpath = os.path.join(dirpath, fname)
                        
                        # global ID
                        image_id_counter += 1
                        # index within series
                        image_index = parse_image_index_from_filename(fname)

                        # read all dicom attributes for this image
                        img_attrs = read_dicom_attributes(fullpath, attr_names=None)

                        # build image row dict: fixed keys + dynamic dicom keys
                        img_row = OrderedDict()
                        img_row["ImageID"] = image_id_counter
                        img_row["ImageIndex"] = image_index
                        img_row["Filename"] = fname
                        img_row["SeriesID"] = this_series_id
                        img_row["FilePath"] = BASE_URL + os.path.relpath(fullpath, BASE_DIR).replace(os.sep, "/")
                        # merge dicom attributes
                        for k, v in img_attrs.items():
                            # avoid key collisions with fixed keys (should not happen)
                            if k in img_row:
                                k = f"DICOM_{k}"
                            img_row[k] = v

                        image_rows.append(img_row)

    # ---------- WRITE CSVs ----------
    print("Processing finished! Writing...")

    # Study CSV header (ordered)
    study_header = ["StudyID", "Region", "Protocol", "Timestamp"] + STUDY_DICOM_ATTRS
    with open(STUDY_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=study_header)
        writer.writeheader()
        for r in study_rows:
            # ensure all keys exist
            writer.writerow({k: r.get(k, "") for k in study_header})

    # Series CSV header
    series_header = ["SeriesID", "SeriesDescription", "SeriesNumber"] + SERIES_DICOM_ATTRS + ["StudyID"]
    with open(SERIES_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=series_header)
        writer.writeheader()
        for r in series_rows:
            writer.writerow({k: r.get(k, "") for k in series_header})

    # Image CSV header: dynamic union of all keys across image_rows (preserve order: fixed keys first)
    fixed_keys = ["ImageID", "Filename", "SeriesID", "FilePath"]
    dyn_keys = []
    dyn_key_set = set()
    for r in image_rows:
        for k in r.keys():
            if k in fixed_keys:
                continue
            if k not in dyn_key_set:
                dyn_keys.append(k)
                dyn_key_set.add(k)

    image_header = fixed_keys + dyn_keys
    with open(IMAGE_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=image_header)
        writer.writeheader()
        for r in image_rows:
            # fill missing dynamic keys with empty string
            row = {k: r.get(k, "") for k in image_header}
            writer.writerow(row)

    print("✅ Export complete:")
    print(f"   - {STUDY_CSV}")
    print(f"   - {SERIES_CSV}")
    print(f"   - {IMAGE_CSV}")

if __name__ == "__main__":
    main()
