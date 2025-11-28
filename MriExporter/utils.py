from typing import Tuple, Optional, Any
import re
from datetime import datetime
import pydicom
import os
import hashlib

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
    
    
    def parse_patient_age(self, age_str: str) -> str:
        """Parse DICOM age string (e.g., '053Y') to integer."""
        if not age_str:
            return ""
        # Extract digits from age string
        match = re.search(r'(\d+)', age_str)
        if match:
            return str(int(match.group(1)))
        return ""

    def parse_yes_no_to_boolean(self, value: str) -> str:
        """Convert YES/NO string to boolean representation."""
        if not value:
            return ""
        value_upper = value.strip().upper()
        if value_upper == "YES":
            return "true"
        elif value_upper == "NO":
            return "false"
        return value