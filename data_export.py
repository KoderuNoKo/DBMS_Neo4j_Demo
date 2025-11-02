#!/usr/bin/env python3
"""
Neo4j MRI Data Exporter

Exports Lumbar Spine MRI dataset to CSV files matching the Neo4j schema:
- Patient.csv
- Study.csv
- Series.csv
- Image.csv
- Equipment.csv
- ImagingParameters.csv
- Relationships CSVs

Usage:
    python mri_exporter.py
"""

import os
import csv
import re
import hashlib
from datetime import datetime
from collections import OrderedDict
from typing import Dict, List, Tuple, Optional, Any
import pydicom
import pandas as pd


# ==================== CONFIGURATION ====================

class Config:
    """Configuration settings for the export process."""
    BASE_DIR = "./01_MRI_Data"
    NOTES_FILE = "./Radiologists Notes for Lumbar Spine MRI Dataset/radiologists_report.csv"
    OUT_DIR = "./mri_export"
    BASE_URL = "http://localhost:8000/"  # Base URL for serving images
    
    # Output CSV files
    PATIENT_CSV = "Patient.csv"
    STUDY_CSV = "Study.csv"
    SERIES_CSV = "Series.csv"
    IMAGE_CSV = "Image.csv"
    EQUIPMENT_CSV = "Equipment.csv"
    IMAGING_PARAMS_CSV = "ImagingParameters.csv"
    
    # Relationship CSVs
    REL_HAS_STUDY_CSV = "rel_HAS_STUDY.csv"
    REL_CONTAINS_SERIES_CSV = "rel_CONTAINS_SERIES.csv"
    REL_CONTAINS_IMAGE_CSV = "rel_CONTAINS_IMAGE.csv"
    REL_HAS_PARAMETERS_CSV = "rel_HAS_PARAMETERS.csv"
    REL_PERFORMED_ON_CSV = "rel_PERFORMED_ON.csv"


# ==================== DICOM ATTRIBUTE MAPPINGS ====================

class DicomMappings:
    """Defines which DICOM attributes map to which Neo4j nodes."""
    
    # Patient attributes (from DICOM)
    PATIENT_ATTRS = [
        "PatientID", "PatientSex", "PatientAge", "PatientWeight", "PatientSize",
        "PatientBirthDate", "PatientIdentityRemoved", "DeidentificationMethod"
    ]
    
    # Study attributes
    STUDY_ATTRS = [
        "StudyInstanceUID", "StudyDate", "StudyTime", "StudyDescription",
        "AccessionNumber", "InstitutionName", "ReferringPhysicianName"
    ]
    
    # Series attributes
    SERIES_ATTRS = [
        "SeriesInstanceUID", "SeriesNumber", "SeriesDate", "SeriesTime",
        "SeriesDescription", "Modality", "BodyPartExamined"
    ]
    
    # Equipment attributes
    EQUIPMENT_ATTRS = [
        "Manufacturer", "ManufacturerModelName", "SoftwareVersions",
        "MagneticFieldStrength", "InstitutionName"
    ]
    
    # Imaging Parameters attributes
    IMAGING_PARAM_ATTRS = [
        "ScanningSequence", "SequenceVariant", "SequenceName",
        "MRAcquisitionType", "SliceThickness", "RepetitionTime",
        "EchoTime", "FlipAngle", "MagneticFieldStrength", "ImagingFrequency"
    ]
    
    # Attributes to exclude from Image node (already in other nodes)
    EXCLUDED_FROM_IMAGE = set(
        PATIENT_ATTRS + STUDY_ATTRS + SERIES_ATTRS + 
        EQUIPMENT_ATTRS + IMAGING_PARAM_ATTRS
    )


# ==================== UTILITY FUNCTIONS ====================

class Utils:
    """Utility functions for parsing and processing."""
    
    @staticmethod
    def parse_study_folder_name(folder_name: str) -> Tuple[str, str, str]:
        """
        Parse study folder name: L-SPINE_LSS_20160309_091629_240000
        Returns: (region, protocol, timestamp_iso)
        """
        parts = folder_name.split("_")
        region = parts[0] if parts else ""
        
        # Find date token (8 digits)
        date_idx = None
        for i, p in enumerate(parts):
            if re.fullmatch(r"\d{8}", p):
                date_idx = i
                break
        
        protocol = ""
        timestamp_iso = ""
        
        if date_idx is not None:
            # Protocol is between region and date
            if date_idx > 1:
                protocol = "_".join(parts[1:date_idx])
            
            raw_date = parts[date_idx]
            raw_time = parts[date_idx + 1] if date_idx + 1 < len(parts) else ""
            raw_uid = parts[date_idx + 2] if date_idx + 2 < len(parts) else ""
            
            # Try parsing with microseconds, then without
            for fmt, cand in [
                ("%Y%m%d%H%M%S%f", raw_date + raw_time + raw_uid),
                ("%Y%m%d%H%M%S", raw_date + raw_time),
                ("%Y%m%d", raw_date),
            ]:
                try:
                    dt = datetime.strptime(cand, fmt)
                    timestamp_iso = dt.isoformat()
                    break
                except Exception:
                    continue
        
        return region, protocol, timestamp_iso
    
    @staticmethod
    def parse_series_folder_name(folder_name: str) -> Tuple[str, int]:
        """
        Parse series folder: T2_TSE_TRA_384_0004
        Returns: (description, series_number)
        """
        if "_" in folder_name:
            head, tail = folder_name.rsplit("_", 1)
            if re.fullmatch(r"\d+", tail):
                return head, int(tail.lstrip("0") or "0")
        return folder_name, 0
    
    @staticmethod
    def parse_image_instance_number(filename: str) -> Optional[int]:
        """
        Extract instance number from filename: LOCALIZER_0_0570_008.ima -> 8
        """
        base = os.path.splitext(filename)[0]
        groups = re.findall(r"(\d+)", base)
        if groups:
            return int(groups[-1].lstrip("0") or "0")
        return None
    
    @staticmethod
    def find_first_ima(root_path: str) -> Optional[str]:
        """Find first .ima file under root_path."""
        for dirpath, _, files in os.walk(root_path):
            for f in files:
                if f.lower().endswith(".ima"):
                    return os.path.join(dirpath, f)
        return None
    
    @staticmethod
    def get_dicom_attr(ds: pydicom.Dataset, keyword: str, default: Any = "") -> str:
        """Safely get DICOM attribute value as string."""
        try:
            val = getattr(ds, keyword, default)
            if hasattr(val, "value"):
                val = val.value
            return str(val) if val is not None else ""
        except Exception:
            return str(default)
    
    @staticmethod
    def generate_hash_id(*args) -> str:
        """Generate consistent hash ID from multiple arguments."""
        combined = "|".join(str(a) for a in args)
        return hashlib.md5(combined.encode()).hexdigest()[:16]


# ==================== DATA EXTRACTORS ====================

class DicomExtractor:
    """Extracts DICOM metadata and organizes it by node type."""
    
    def __init__(self):
        self.utils = Utils()
    
    def read_dicom(self, filepath: str) -> Optional[pydicom.Dataset]:
        """Read DICOM file safely."""
        try:
            return pydicom.dcmread(filepath, stop_before_pixels=True, force=True)
        except Exception as e:
            print(f"Warning: Could not read {filepath}: {e}")
            return None
    
    def extract_attributes(self, ds: pydicom.Dataset, attr_list: List[str]) -> Dict[str, str]:
        """Extract specific attributes from DICOM dataset."""
        result = {}
        for attr in attr_list:
            result[attr] = self.utils.get_dicom_attr(ds, attr)
        return result
    
    def extract_all_image_attributes(self, ds: pydicom.Dataset) -> Dict[str, str]:
        """Extract all DICOM attributes for Image node (excluding those in other nodes)."""
        result = {}
        for elem in ds:
            keyword = self.utils.get_dicom_attr(elem, "keyword", None)
            if not keyword or keyword in DicomMappings.EXCLUDED_FROM_IMAGE:
                continue
            try:
                val = elem.value
                # Skip binary data and references
                if "(0008,1155)" in str(val) or keyword == "PixelData":
                    continue
                result[keyword] = str(val)
            except Exception:
                pass
        return result


# ==================== EXPORTERS ====================

class DataExporter:
    """Main exporter class that orchestrates the export process."""
    
    def __init__(self, config: Config):
        self.config = config
        self.extractor = DicomExtractor()
        self.utils = Utils()
        
        # Counters for surrogate keys
        self.study_id_counter = 1
        self.series_id_counter = 1
        self.image_id_counter = 1
        self.equipment_id_counter = 1
        self.param_id_counter = 1
        
        # Data storage
        self.patients = []
        self.studies = []
        self.series_list = []
        self.images = []
        self.equipment_map = {}  # hash -> equipment_id
        self.param_map = {}  # hash -> param_id
        
        # Relationships
        self.rel_has_study = []
        self.rel_contains_series = []
        self.rel_contains_image = []
        self.rel_has_parameters = []
        self.rel_performed_on = []
        
        # Clinical notes
        self.clinical_notes = self._load_clinical_notes()
    
    def _load_clinical_notes(self) -> Dict[str, str]:
        """Load clinical notes from CSV."""
        try:
            df = pd.read_csv(self.config.NOTES_FILE)
            return dict(zip(df["Patient ID"].astype(str), df["Clinician's Notes"]))
        except Exception as e:
            print(f"Warning: Could not load clinical notes: {e}")
            return {}
    
    def _get_or_create_equipment(self, ds: pydicom.Dataset) -> int:
        """Get existing equipment ID or create new equipment entry."""
        attrs = self.extractor.extract_attributes(ds, DicomMappings.EQUIPMENT_ATTRS)
        
        # Create hash for uniqueness
        eq_hash = self.utils.generate_hash_id(
            attrs.get("Manufacturer", ""),
            attrs.get("ManufacturerModelName", ""),
            attrs.get("SoftwareVersions", ""),
            attrs.get("MagneticFieldStrength", "")
        )
        
        if eq_hash in self.equipment_map:
            return self.equipment_map[eq_hash]
        
        eq_id = self.equipment_id_counter
        self.equipment_id_counter += 1
        self.equipment_map[eq_hash] = eq_id
        
        self.equipment_map[eq_hash] = {
            "EquipmentId": eq_id,
            **attrs
        }
        
        return eq_id
    
    def _get_or_create_imaging_params(self, ds: pydicom.Dataset) -> int:
        """Get existing imaging parameters ID or create new entry."""
        attrs = self.extractor.extract_attributes(ds, DicomMappings.IMAGING_PARAM_ATTRS)
        
        # Create hash for uniqueness
        param_hash = self.utils.generate_hash_id(*attrs.values())
        
        if param_hash in self.param_map:
            return self.param_map[param_hash]
        
        param_id = self.param_id_counter
        self.param_id_counter += 1
        
        self.param_map[param_hash] = {
            "ParameterID": param_id,
            **attrs
        }
        
        return param_id
    
    def process_patient(self, patient_folder: str, patient_path: str):
        """Process a single patient folder."""
        patient_id = str(int(patient_folder))  # "0001" -> "1"
        
        # Find first DICOM file to extract patient attributes
        first_ima = self.utils.find_first_ima(patient_path)
        patient_attrs = {}
        
        if first_ima:
            ds = self.extractor.read_dicom(first_ima)
            if ds:
                patient_attrs = self.extractor.extract_attributes(ds, DicomMappings.PATIENT_ATTRS)
        
        # Create patient record
        patient_record = {
            "PatientId": patient_id,
            "Age": patient_attrs.get("PatientAge", ""),
            "Sex": patient_attrs.get("PatientSex", ""),
            "Size": patient_attrs.get("PatientSize", ""),
            "Weight": patient_attrs.get("PatientWeight", ""),
            "PatientIdentityRemoved": patient_attrs.get("PatientIdentityRemoved", ""),
            "DeidentificationMethod": patient_attrs.get("DeidentificationMethod", ""),
            "Birthdate": patient_attrs.get("PatientBirthDate", ""),
            "ClinicalNote": self.clinical_notes.get(patient_id, "")
        }
        self.patients.append(patient_record)
        
        # Process studies under this patient
        for study_folder in sorted(os.listdir(patient_path)):
            study_path = os.path.join(patient_path, study_folder)
            if not os.path.isdir(study_path):
                continue
            self.process_study(patient_id, study_folder, study_path)
    
    def process_study(self, patient_id: str, study_folder: str, study_path: str):
        """Process a single study folder."""
        region, protocol, timestamp = self.utils.parse_study_folder_name(study_folder)
        
        # Find representative DICOM
        rep_ima = self.utils.find_first_ima(study_path)
        if not rep_ima:
            return
        
        ds = self.extractor.read_dicom(rep_ima)
        if not ds:
            return
        
        study_attrs = self.extractor.extract_attributes(ds, DicomMappings.STUDY_ATTRS)
        
        # Get or create equipment
        equipment_id = self._get_or_create_equipment(ds)
        
        # Combine study date and time
        study_date = study_attrs.get("StudyDate", "")
        study_time = study_attrs.get("StudyTime", "")
        study_datetime = ""
        if study_date:
            try:
                dt_str = study_date + study_time.split(".")[0] if study_time else study_date
                dt = datetime.strptime(dt_str[:14], "%Y%m%d%H%M%S" if len(dt_str) >= 14 else "%Y%m%d")
                study_datetime = dt.isoformat()
            except Exception:
                study_datetime = timestamp
        
        study_id = self.study_id_counter
        self.study_id_counter += 1
        
        study_record = {
            "StudyId": study_id,
            "StudyInstanceUID": study_attrs.get("StudyInstanceUID", ""),
            "StudyDatetime": study_datetime or timestamp,
            "StudyDescription": study_attrs.get("StudyDescription", f"{region}_{protocol}"),
            "AccessionNumber": study_attrs.get("AccessionNumber", ""),
            "InstitutionName": study_attrs.get("InstitutionName", ""),
            "ReferringPhysician": study_attrs.get("ReferringPhysicianName", "")
        }
        self.studies.append(study_record)
        
        # Add relationships
        self.rel_has_study.append({"PatientId": patient_id, "StudyId": study_id})
        self.rel_performed_on.append({"StudyId": study_id, "EquipmentId": equipment_id})
        
        # Process series under this study
        for series_folder in sorted(os.listdir(study_path)):
            series_path = os.path.join(study_path, series_folder)
            if not os.path.isdir(series_path):
                continue
            self.process_series(study_id, series_folder, series_path)
    
    def process_series(self, study_id: int, series_folder: str, series_path: str):
        """Process a single series folder."""
        series_desc, series_num = self.utils.parse_series_folder_name(series_folder)
        
        # Find representative DICOM
        rep_ima = self.utils.find_first_ima(series_path)
        if not rep_ima:
            return
        
        ds = self.extractor.read_dicom(rep_ima)
        if not ds:
            return
        
        series_attrs = self.extractor.extract_attributes(ds, DicomMappings.SERIES_ATTRS)
        
        # Get or create imaging parameters
        param_id = self._get_or_create_imaging_params(ds)
        
        # Combine series date and time
        series_date = series_attrs.get("SeriesDate", "")
        series_time = series_attrs.get("SeriesTime", "")
        series_datetime = ""
        if series_date:
            try:
                dt_str = series_date + series_time.split(".")[0] if series_time else series_date
                dt = datetime.strptime(dt_str[:14], "%Y%m%d%H%M%S" if len(dt_str) >= 14 else "%Y%m%d")
                series_datetime = dt.isoformat()
            except Exception:
                pass
        
        series_id = self.series_id_counter
        self.series_id_counter += 1
        
        series_record = {
            "SeriesId": series_id,
            "SeriesInstanceUID": series_attrs.get("SeriesInstanceUID", ""),
            "SeriesNumber": series_attrs.get("SeriesNumber", series_num),
            "SeriesDatetime": series_datetime,
            "SeriesDescription": series_attrs.get("SeriesDescription", series_desc),
            "SeriesType": series_desc,
            "Modality": series_attrs.get("Modality", ""),
            "BodyPartExamined": series_attrs.get("BodyPartExamined", "")
        }
        self.series_list.append(series_record)
        
        # Add relationships
        self.rel_contains_series.append({
            "StudyId": study_id,
            "SeriesId": series_id,
            "SeriesNumber": series_num
        })
        self.rel_has_parameters.append({"SeriesId": series_id, "ParameterID": param_id})
        
        # Process images in this series
        for dirpath, _, files in os.walk(series_path):
            for fname in sorted(files):
                if not fname.lower().endswith(".ima"):
                    continue
                fullpath = os.path.join(dirpath, fname)
                self.process_image(series_id, fname, fullpath)
    
    def process_image(self, series_id: int, filename: str, filepath: str):
        """Process a single image file."""
        ds = self.extractor.read_dicom(filepath)
        if not ds:
            return
        
        instance_num = self.utils.parse_image_instance_number(filename)
        image_attrs = self.extractor.extract_all_image_attributes(ds)
        
        image_id = self.image_id_counter
        self.image_id_counter += 1
        
        rel_path = os.path.relpath(filepath, self.config.BASE_DIR).replace(os.sep, "/")
        
        image_record = OrderedDict()
        image_record["ImageId"] = image_id
        image_record["FilePath"] = self.config.BASE_URL + rel_path
        # Add all remaining DICOM attributes
        image_record.update(image_attrs)
        
        self.images.append(image_record)
        
        # Add relationship
        self.rel_contains_image.append({
            "SeriesId": series_id,
            "ImageId": image_id,
            "InstanceNumber": instance_num or 0
        })
    
    def export(self):
        """Main export method."""
        os.makedirs(self.config.OUT_DIR, exist_ok=True)
        
        print("Starting export process...")
        
        # Process all patients
        for patient_folder in sorted(os.listdir(self.config.BASE_DIR)):
            patient_path = os.path.join(self.config.BASE_DIR, patient_folder)
            if not os.path.isdir(patient_path) or not re.fullmatch(r"\d+", patient_folder):
                continue
            
            print(f"Processing patient {patient_folder}/575...")
            self.process_patient(patient_folder, patient_path)
        
        # Write CSVs
        print("\nWriting CSV files...")
        self._write_csvs()
        
        print("\n✅ Export complete!")
        print(f"   Output directory: {self.config.OUT_DIR}")
        print(f"   Patients: {len(self.patients)}")
        print(f"   Studies: {len(self.studies)}")
        print(f"   Series: {len(self.series_list)}")
        print(f"   Images: {len(self.images)}")
        print(f"   Equipment: {len(self.equipment_map)}")
        print(f"   Imaging Parameters: {len(self.param_map)}")
    
    def _write_csvs(self):
        """Write all data to CSV files."""
        # Patient
        self._write_csv(self.config.PATIENT_CSV, self.patients)
        
        # Study
        self._write_csv(self.config.STUDY_CSV, self.studies)
        
        # Series
        self._write_csv(self.config.SERIES_CSV, self.series_list)
        
        # Equipment
        equipment_list = list(self.equipment_map.values())
        self._write_csv(self.config.EQUIPMENT_CSV, equipment_list)
        
        # Imaging Parameters
        param_list = list(self.param_map.values())
        self._write_csv(self.config.IMAGING_PARAMS_CSV, param_list)
        
        # Image (with dynamic columns)
        self._write_csv_dynamic(self.config.IMAGE_CSV, self.images)
        
        # Relationships
        self._write_csv(self.config.REL_HAS_STUDY_CSV, self.rel_has_study)
        self._write_csv(self.config.REL_CONTAINS_SERIES_CSV, self.rel_contains_series)
        self._write_csv(self.config.REL_CONTAINS_IMAGE_CSV, self.rel_contains_image)
        self._write_csv(self.config.REL_HAS_PARAMETERS_CSV, self.rel_has_parameters)
        self._write_csv(self.config.REL_PERFORMED_ON_CSV, self.rel_performed_on)
    
    def _write_csv(self, filename: str, data: List[Dict], fieldnames: List[str] = None):
        """Write data to CSV with fixed columns."""
        if not data:
            return
        
        filepath = os.path.join(self.config.OUT_DIR, filename)
        if fieldnames is None:
            fieldnames = list(data[0].keys())
        
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                writer.writerow({k: row.get(k, "") for k in fieldnames})
    
    def _write_csv_dynamic(self, filename: str, data: List[Dict]):
        """Write data to CSV with dynamic columns (for Image)."""
        if not data:
            return
        
        # Collect all unique keys
        fixed_keys = ["ImageId", "FilePath"]
        dynamic_keys = []
        dynamic_key_set = set()
        
        for row in data:
            for k in row.keys():
                if k in fixed_keys:
                    continue
                if k not in dynamic_key_set:
                    dynamic_keys.append(k)
                    dynamic_key_set.add(k)
        
        fieldnames = fixed_keys + dynamic_keys
        self._write_csv(filename, data, fieldnames)


# ==================== MAIN ====================

def main():
    """Main entry point."""
    config = Config()
    exporter = DataExporter(config)
    exporter.export()


if __name__ == "__main__":
    main()