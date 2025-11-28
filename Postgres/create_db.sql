-- PostgreSQL Schema for Lumbar Spine MRI Dataset

-- Patient Table (equivalent to Patient node)
CREATE TABLE patient (
    patient_id VARCHAR(255) PRIMARY KEY,  -- from Folder name
    age INTEGER,
    sex VARCHAR(10),
    size FLOAT,
    weight FLOAT,
    patient_identity_removed BOOLEAN,
    deidentification_method VARCHAR(255),
    birthdate DATE,
    clinical_note TEXT
);

-- Equipment Table (equivalent to Equipment node)
CREATE TABLE equipment (
    equipment_id SERIAL PRIMARY KEY,
    manufacturer VARCHAR(255),
    manufacturer_model VARCHAR(255),
    software_version VARCHAR(255),
    magnetic_field_strength FLOAT,
    institution_name VARCHAR(255)
);

-- Study Table (equivalent to Study node)
CREATE TABLE study (
    study_id SERIAL PRIMARY KEY,
    study_instance_uid VARCHAR(255) UNIQUE NOT NULL,
    study_datetime TIMESTAMP,
    study_description TEXT,
    accession_number VARCHAR(255),
    institution_name VARCHAR(255),
    referring_physician VARCHAR(255),
    patient_id VARCHAR(255) REFERENCES patient(patient_id),  -- [:HAS_STUDY]
    equipment_id INTEGER REFERENCES equipment(equipment_id)  -- [:PERFORMED_ON]
);

-- Imaging Parameters Table (equivalent to ImagingParameters node)
CREATE TABLE imaging_parameters (
    parameter_id SERIAL PRIMARY KEY,
    scanning_sequence VARCHAR(50),
    sequence_variant VARCHAR(50),
    sequence_name VARCHAR(255),
    mr_acquisition_type VARCHAR(10),
    slice_thickness FLOAT,
    repetition_time FLOAT,  -- TR in ms
    echo_time FLOAT,        -- TE in ms
    flip_angle FLOAT,
    magnetic_field_strength FLOAT,
    imaging_frequency FLOAT
);

-- Series Table (equivalent to Series node)
CREATE TABLE series (
    series_id SERIAL PRIMARY KEY,
    series_instance_uid VARCHAR(255) UNIQUE NOT NULL,
    series_number INTEGER,
    series_datetime TIMESTAMP,
    series_description TEXT,
    series_type VARCHAR(100),
    modality VARCHAR(10),
    body_part_examined VARCHAR(100),
    study_id INTEGER REFERENCES study(study_id),              -- [:CONTAINS_SERIES]
    parameter_id INTEGER REFERENCES imaging_parameters(parameter_id)  -- [:HAS_PARAMETERS]
);

-- Image Table (equivalent to Image node)
CREATE TABLE image (
    image_id SERIAL PRIMARY KEY,
    instance_number INTEGER,
    file_path VARCHAR(512),
    series_id INTEGER REFERENCES series(series_id),  -- [:CONTAINS_IMAGE]
    -- Add other properties from .ima file here as needed
    -- e.g., rows INTEGER, columns INTEGER, pixel_spacing VARCHAR(50), etc.
    CONSTRAINT unique_series_instance UNIQUE (series_id, instance_number)
);

-- Comments for documentation
COMMENT ON TABLE patient IS 'Patient demographic and identification information';
COMMENT ON TABLE study IS 'MRI study/examination information';
COMMENT ON TABLE series IS 'Image series within a study';
COMMENT ON TABLE image IS 'Individual DICOM images';
COMMENT ON TABLE imaging_parameters IS 'Technical imaging acquisition parameters';
COMMENT ON TABLE equipment IS 'MRI scanner equipment information';

COMMENT ON COLUMN study.patient_id IS 'FK to patient - equivalent to Neo4j [:HAS_STUDY] relationship';
COMMENT ON COLUMN study.equipment_id IS 'FK to equipment - equivalent to Neo4j [:PERFORMED_ON] relationship';
COMMENT ON COLUMN series.study_id IS 'FK to study - equivalent to Neo4j [:CONTAINS_SERIES] relationship';
COMMENT ON COLUMN series.parameter_id IS 'FK to imaging_parameters - equivalent to Neo4j [:HAS_PARAMETERS] relationship';
COMMENT ON COLUMN image.series_id IS 'FK to series - equivalent to Neo4j [:CONTAINS_IMAGE] relationship';