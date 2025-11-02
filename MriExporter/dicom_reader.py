from utils import Utils
from config import DicomMappings

from typing import Dict, List, Tuple, Optional, Any
import pydicom

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