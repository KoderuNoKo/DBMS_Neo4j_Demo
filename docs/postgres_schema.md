# PostgreSQL Schema Documentation: Lumbar Spine MRI Dataset

## Overview

This database schema is designed to store and manage lumbar spine MRI imaging data in a relational format. It mirrors a Neo4j graph database design while maintaining relational database best practices.

## Schema Diagram

```
Patient (1) ──< Study (N)
                 │
                 └──> Equipment (1)
                 │
                 └──< Series (N)
                       │
                       └──> ImagingParameters (1)
                       │
                       └──< Image (N)
```

## Tables

### 1. patient

Stores patient demographic and identification information.

|Column|Type|Constraints|Description|
|---|---|---|---|
|patient_id|VARCHAR(255)|PRIMARY KEY|Patient identifier from folder name|
|age|INTEGER||Patient age|
|sex|VARCHAR(10)||Patient sex/gender|
|size|FLOAT||Patient height|
|weight|FLOAT||Patient weight|
|patient_identity_removed|BOOLEAN||Flag indicating if PHI was removed|
|deidentification_method|VARCHAR(255)||Method used for deidentification|
|birthdate|DATE||Patient date of birth|
|clinical_note|TEXT||Clinical notes from physician|


---

### 2. equipment

Stores MRI scanner equipment specifications.

| Column                  | Type         | Constraints | Description                            |
| ----------------------- | ------------ | ----------- | -------------------------------------- |
| equipment_id            | SERIAL       | PRIMARY KEY | Auto-generated equipment ID            |
| manufacturer            | VARCHAR(255) |             | Equipment manufacturer (e.g., SIEMENS) |
| manufacturer_model      | VARCHAR(255) |             | Model name (e.g., MAGNETOM_ESSENZA)    |
| software_version        | VARCHAR(255) |             | Scanner software version               |
| magnetic_field_strength | FLOAT        |             | Field strength (e.g., 1.5T, 3T)        |
| institution_name        | VARCHAR(255) |             | Name of institution                    |


---

### 3. study

Represents an MRI study/examination session.

|Column|Type|Constraints|Description|
|---|---|---|---|
|study_id|SERIAL|PRIMARY KEY|Auto-generated study ID|
|study_instance_uid|VARCHAR(255)|UNIQUE, NOT NULL|DICOM Study Instance UID|
|study_datetime|TIMESTAMP||Date and time of study|
|study_description|TEXT||Description of study|
|accession_number|VARCHAR(255)||Study accession number|
|institution_name|VARCHAR(255)||Institution where study performed|
|referring_physician|VARCHAR(255)||Name of referring physician|
|patient_id|VARCHAR(255)|FOREIGN KEY|Reference to patient|
|equipment_id|INTEGER|FOREIGN KEY|Reference to equipment used|

**Relationships:**

- `patient_id` → `patient.patient_id` (Many studies per patient)
- `equipment_id` → `equipment.equipment_id` (Many studies per equipment)

---

### 4. imaging_parameters

Stores technical MRI acquisition parameters.

|Column|Type|Constraints|Description|
|---|---|---|---|
|parameter_id|SERIAL|PRIMARY KEY|Auto-generated parameter set ID|
|scanning_sequence|VARCHAR(50)||Sequence type (GR, SE, etc.)|
|sequence_variant|VARCHAR(50)||Variant of sequence|
|sequence_name|VARCHAR(255)||Name of sequence|
|mr_acquisition_type|VARCHAR(10)||2D or 3D acquisition|
|slice_thickness|FLOAT||Thickness of slice in mm|
|repetition_time|FLOAT||TR in milliseconds|
|echo_time|FLOAT||TE in milliseconds|
|flip_angle|FLOAT||Flip angle in degrees|
|magnetic_field_strength|FLOAT||Field strength (1.5T, 3T)|
|imaging_frequency|FLOAT||Imaging frequency in MHz|


---

### 5. series

Represents an image series within a study.

|Column|Type|Constraints|Description|
|---|---|---|---|
|series_id|SERIAL|PRIMARY KEY|Auto-generated series ID|
|series_instance_uid|VARCHAR(255)|UNIQUE, NOT NULL|DICOM Series Instance UID|
|series_number|INTEGER||Series number within study|
|series_datetime|TIMESTAMP||Date and time of series|
|series_description|TEXT||Description of series|
|series_type|VARCHAR(100)||Type of series|
|modality|VARCHAR(10)||Imaging modality (e.g., MR)|
|body_part_examined|VARCHAR(100)||Body part examined|
|study_id|INTEGER|FOREIGN KEY|Reference to parent study|
|parameter_id|INTEGER|FOREIGN KEY|Reference to imaging parameters|


---

### 6. image

Stores individual DICOM images.

|Column|Type|Constraints|Description|
|---|---|---|---|
|image_id|SERIAL|PRIMARY KEY|Auto-generated image ID|
|instance_number|INTEGER||Instance number within series|
|file_path|VARCHAR(512)||Path to image file|
|series_id|INTEGER|FOREIGN KEY|Reference to parent series|


**Note:** Additional DICOM properties from .ima files should be added as columns as needed (e.g., rows, columns, pixel_spacing, window_center, window_width, etc.)

---

## Common Query Patterns

### Get all studies for a patient

```sql
SELECT s.* 
FROM study s
WHERE s.patient_id = 'PATIENT_ID';
```

### Get all series in a study with parameters

```sql
SELECT s.*, ip.*
FROM series s
LEFT JOIN imaging_parameters ip ON s.parameter_id = ip.parameter_id
WHERE s.study_id = 123;
```

### Get complete hierarchy for a patient

```sql
SELECT 
    p.patient_id,
    st.study_instance_uid,
    st.study_datetime,
    se.series_description,
    COUNT(i.image_id) as image_count
FROM patient p
JOIN study st ON p.patient_id = st.patient_id
JOIN series se ON st.study_id = se.study_id
LEFT JOIN image i ON se.series_id = i.series_id
WHERE p.patient_id = 'PATIENT_ID'
GROUP BY p.patient_id, st.study_instance_uid, st.study_datetime, se.series_description
ORDER BY st.study_datetime, se.series_number;
```

### Find studies by equipment

```sql
SELECT st.*, e.manufacturer, e.manufacturer_model
FROM study st
JOIN equipment e ON st.equipment_id = e.equipment_id
WHERE e.manufacturer = 'SIEMENS';
```

## Data Loading Guidelines

1. **Load order** (due to foreign key constraints):

    - patient
    - equipment
    - imaging_parameters
    - study
    - series
    - image

## Maintenance

### Vacuum and Analyze

Run regularly to maintain query performance:

```sql
VACUUM ANALYZE patient;
VACUUM ANALYZE study;
VACUUM ANALYZE series;
VACUUM ANALYZE image;
```

### Check Foreign Key Integrity

```sql
-- Find orphaned studies
SELECT * FROM study WHERE patient_id NOT IN (SELECT patient_id FROM patient);

-- Find orphaned series
SELECT * FROM series WHERE study_id NOT IN (SELECT study_id FROM study);

-- Find orphaned images
SELECT * FROM image WHERE series_id NOT IN (SELECT series_id FROM series);
```

## Migration from Neo4j

This schema directly corresponds to the Neo4j graph structure:

|Neo4j Element|PostgreSQL Element|
|---|---|
|Node: Patient|Table: patient|
|Node: Study|Table: study|
|Node: Series|Table: series|
|Node: Image|Table: image|
|Node: Equipment|Table: equipment|
|Node: ImagingParameters|Table: imaging_parameters|
|Relationship: [:HAS_STUDY]|FK: study.patient_id|
|Relationship: [:PERFORMED_ON]|FK: study.equipment_id|
|Relationship: [:CONTAINS_SERIES]|FK: series.study_id|
|Relationship: [:HAS_PARAMETERS]|FK: series.parameter_id|
|Relationship: [:CONTAINS_IMAGE]|FK: image.series_id|

## Notes

- All timestamp fields use PostgreSQL's `TIMESTAMP` type (without timezone)
- VARCHAR fields are sized generously to accommodate DICOM standards
- SERIAL types auto-increment and are implemented as sequences
- The schema uses snake_case naming convention (PostgreSQL standard)