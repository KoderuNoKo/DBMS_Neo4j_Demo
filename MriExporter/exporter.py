"""
Modified exporter.py with batch writing capability
"""

from dicom_reader import DicomExtractor
from utils import Utils
from config import Config, DicomMappings
from ImaProcessor import ImaProcessor

from typing import Dict, List, Tuple, Optional, Any
import pandas as pd
import pydicom
from datetime import datetime
from collections import OrderedDict
import csv
import os
import re


class DataExporter:
    """Main exporter class that orchestrates the export process."""
    
    def __init__(self, config: Config, batch_size: int = 50):
        self.config = config
        self.extractor = DicomExtractor()
        self.utils = Utils()
        self.batch_size = batch_size  # Number of patients per batch
        
        # Counters for surrogate keys
        self.study_id_counter = 1
        self.series_id_counter = 1
        self.image_id_counter = 1
        self.equipment_id_counter = 1
        self.param_id_counter = 1
        
        # Data storage (current batch)
        self.patients = []
        self.studies = []
        self.series_list = []
        self.images = []
        self.equipment_map = {}  # hash -> equipment dict (persists across batches)
        self.param_map = {}  # hash -> param dict (persists across batches)
        
        # Relationships (current batch)
        self.rel_has_study = []
        self.rel_contains_series = []
        self.rel_contains_image = []
        self.rel_has_parameters = []
        self.rel_performed_on = []
        
        # Clinical notes
        self.clinical_notes = self._load_clinical_notes()
        
        # .Ima processing model
        self.ima_proc = ImaProcessor()
        
        # Track if first write (for headers)
        self.first_write = True
        
        # Patient counter for batching
        self.patient_count = 0
    
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
            return self.equipment_map[eq_hash]["EquipmentId"]
        
        eq_id = self.equipment_id_counter
        self.equipment_id_counter += 1
        
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
            return self.param_map[param_hash]["ParameterID"]
        
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
            "Age": self.utils.parse_patient_age(patient_attrs.get("PatientAge", "")),
            "Sex": patient_attrs.get("PatientSex", ""),
            "Size": patient_attrs.get("PatientSize", ""),
            "Weight": patient_attrs.get("PatientWeight", ""),
            "PatientIdentityRemoved": self.utils.parse_yes_no_to_boolean(patient_attrs.get("PatientIdentityRemoved", "")),
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
        
        if Config.GENERATE_EMBEDDINGS:
            image_record["EmbeddingVector"] = self.ima_proc.process_ima(filepath=filepath, to_img=Config.EXPORT_IMAGES, output_format=Config.IMAGE_FORMAT)
        
        if Config.EXPORT_IMAGES:
            rel_path = rel_path.replace(".ima", f".{Config.IMAGE_FORMAT}")
        
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
    
    def _write_batch(self):
        """Write current batch to CSV files."""
        if not self.patients:
            return
        
        print(f"  Writing batch ({len(self.patients)} patients)...")
        
        # Write nodes (append mode after first write)
        mode = 'w' if self.first_write else 'a'
        write_header = self.first_write
        
        self._write_csv_batch(self.config.PATIENT_CSV, self.patients, mode, write_header)
        self._write_csv_batch(self.config.STUDY_CSV, self.studies, mode, write_header)
        self._write_csv_batch(self.config.SERIES_CSV, self.series_list, mode, write_header)
        
        # Image with dynamic columns
        self._write_csv_dynamic_batch(self.config.IMAGE_CSV, self.images, mode, write_header)
        
        # Write relationships (append mode after first write)
        self._write_csv_batch(self.config.REL_HAS_STUDY_CSV, self.rel_has_study, mode, write_header)
        self._write_csv_batch(self.config.REL_CONTAINS_SERIES_CSV, self.rel_contains_series, mode, write_header)
        self._write_csv_batch(self.config.REL_CONTAINS_IMAGE_CSV, self.rel_contains_image, mode, write_header)
        self._write_csv_batch(self.config.REL_HAS_PARAMETERS_CSV, self.rel_has_parameters, mode, write_header)
        self._write_csv_batch(self.config.REL_PERFORMED_ON_CSV, self.rel_performed_on, mode, write_header)
        
        # Clear batch data (but keep equipment_map and param_map)
        self.patients = []
        self.studies = []
        self.series_list = []
        self.images = []
        self.rel_has_study = []
        self.rel_contains_series = []
        self.rel_contains_image = []
        self.rel_has_parameters = []
        self.rel_performed_on = []
        
        self.first_write = False
    
    def _finalize_equipment_and_params(self):
        """Write equipment and imaging parameters at the end (after all patients processed)."""
        print("  Writing equipment and imaging parameters...")
        
        equipment_list = list(self.equipment_map.values())
        self._write_csv(self.config.EQUIPMENT_CSV, equipment_list)
        
        param_list = list(self.param_map.values())
        self._write_csv(self.config.IMAGING_PARAMS_CSV, param_list)
    
    def export(self):
        """Main export method with batch writing."""
        os.makedirs(self.config.OUT_DIR, exist_ok=True)
        
        print("Starting export process...")
        print(f"  Batch size: {self.batch_size} patients")
        
        # Process all patients with batch writing
        patient_folders = sorted([
            f for f in os.listdir(self.config.BASE_DIR)
            if os.path.isdir(os.path.join(self.config.BASE_DIR, f)) and re.fullmatch(r"\d+", f)
        ])
        
        total_patients = len(patient_folders)
        
        for idx, patient_folder in enumerate(patient_folders, 1):
            patient_path = os.path.join(self.config.BASE_DIR, patient_folder)
            
            print(f"Processing patient {patient_folder} ({idx}/{total_patients})...")
            self.process_patient(patient_folder, patient_path)
            self.patient_count += 1
            
            # Write batch when batch_size reached
            if self.patient_count >= self.batch_size:
                self._write_batch()
                self.patient_count = 0
        
        # Write remaining data
        if self.patients:
            self._write_batch()
        
        # Write equipment and parameters (once at the end)
        self._finalize_equipment_and_params()
        
        print("\nExport complete!")
        print(f"   Output directory: {self.config.OUT_DIR}")
        print(f"   Total patients processed: {total_patients}")
        print(f"   Equipment entries: {len(self.equipment_map)}")
        print(f"   Imaging Parameters: {len(self.param_map)}")
    
    def _write_csv_batch(self, filename: str, data: List[Dict], mode: str = 'w', write_header: bool = True):
        """Write data to CSV in batch mode (append or write)."""
        if not data:
            return
        
        filepath = os.path.join(self.config.OUT_DIR, filename)
        fieldnames = list(data[0].keys())
        
        with open(filepath, mode, newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if write_header:
                writer.writeheader()
            for row in data:
                writer.writerow({k: row.get(k, "") for k in fieldnames})
    
    def _write_csv_dynamic_batch(self, filename: str, data: List[Dict], mode: str = 'w', write_header: bool = True):
        """Write data to CSV with dynamic columns in batch mode."""
        if not data:
            return
        
        filepath = os.path.join(self.config.OUT_DIR, filename)
        
        # Collect all unique keys for this batch
        fixed_keys = ["ImageId", "FilePath"]
        if Config.GENERATE_EMBEDDINGS:
            fixed_keys.insert(1, "EmbeddingVector")  # Insert after ImageId
        
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
        
        # For append mode, we need to read existing headers to maintain consistency
        if mode == 'a' and os.path.exists(filepath):
            with open(filepath, 'r', newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                existing_fieldnames = reader.fieldnames
                # Merge fieldnames (preserve order, add new ones)
                merged_fields = list(existing_fieldnames)
                for field in fieldnames:
                    if field not in merged_fields:
                        merged_fields.append(field)
                fieldnames = merged_fields
        
        with open(filepath, mode, newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if write_header:
                writer.writeheader()
            for row in data:
                writer.writerow({k: row.get(k, "") for k in fieldnames})
    
    def _write_csv(self, filename: str, data: List[Dict], fieldnames: List[str] = None):
        """Write data to CSV with fixed columns (used for equipment and params at end)."""
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