class Config:
    """Configuration settings for the export process."""
    BASE_DIR = "./01_MRI_Data"
    NOTES_FILE = "./Radiologists Notes for Lumbar Spine MRI Dataset/radiologists_report.csv"
    OUT_DIR = "./mri_export"
    BASE_URL = "http://localhost:8000/"  # Base URL for serving images
    
    # Image processing options
    EXPORT_IMAGES = True          # Extract images from .ima
    IMAGE_FORMAT = "png"          # Choose: png, jpg, jpeg, etc.
    GENERATE_EMBEDDINGS = True    # Generate CLIP embeddings
    
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