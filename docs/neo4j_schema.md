# Neo4j Schema Design for Lumbar Spine MRI Dataset

## Node Types

### 1. **Patient**

```
Properties:
- patientId: String // from Folder name 
- age: Integer 
- sex: String 
- size: Float
- weight: Float
- patientIdentityRemoved: bool
- deidentificationMethod: String
- birthdate: Datetime
- clinicalNote: String // from clinical's note
```

### 2. **Study**

```
Properties:
- studyId: Integer // surrogate key
- studyInstanceUID: String
- studyDatetime: Datetime
- studyDescription: String
- accessionNumber: String
- institutionName: String
- referringPhysician: String
```

### 3. **Series**

```
Properties:
- seriesId: Integer // surrogate key
- seriesInstanceUID: String
- seriesNumber: Integer
- seriesDatetime: Datetime
- seriesDescription: String
- seriesType: String
- modality: String 
- bodyPartExamined: String
```



### 4. **ImagingParameters**

```
Properties:
- parameterID: Integer // surrogate key
- scanningSequence: String // GR, SE, etc.
- sequenceVariant: String
- sequenceName: String
- mrAcquisitionType: String // 2D, 3D
- sliceThickness: Float
- repetitionTime: Float // TR in ms
- echoTime: Float // TE in ms
- flipAngle: Float
- magneticFieldStrength: Float // 1.5T, 3T
- imagingFrequency: Float
```

### 5. **Equipment**

```
Properties:
- EquipmentId: Integer // surrogate key
- manufacturer: String // SIEMENS
- manufacturerModel: String // MAGNETOM_ESSENZA
- softwareVersion: String
- magneticFieldStrength: Float
- institutionName: String
```

### 6. **Image**

```
Properties:
- imageId: Integer // surrogate key
- ... // All remaining properties from .ima file that is not covered by others Node labels
- filePath: String // path to obtain the image file
```
## Relationships

### Primary Relationships

1. **Patient -[:HAS_STUDY]-> Study**
    
2. **Study -[:CONTAINS_SERIES]-> Series**
    
    ```
    Properties:
    - seriesNumber: Integer
    ```
    
3. **Series -[:CONTAINS_IMAGE]-> Image**
    
    ```
    Properties:
    - instanceNumber: Integer
    ```
    
4. **Series -[:HAS_PARAMETERS]-> ImagingParameters**
    
5. **Study -[:PERFORMED_ON]-> Equipment**
