


DROP INDEX IF EXISTS idx_patient_age;
DROP INDEX IF EXISTS idx_patient_sex;
DROP INDEX IF EXISTS idx_study_patient_id;
DROP INDEX IF EXISTS idx_series_study_id;
DROP INDEX IF EXISTS idx_image_series_id;

-- ===============================================================
--  QUERY 1: Find all images of patients aged between 40–60
-- ===============================================================

-- Before indexing
EXPLAIN ANALYZE
SELECT i.image_id, s.series_id, p.age, p.sex
FROM image i
JOIN series s ON i.series_id = s.series_id
JOIN study st ON s.study_id = st.study_id
JOIN patient p ON st.patient_id = p.patient_id
WHERE p.age BETWEEN 40 AND 60;

-- Create index on patient age
CREATE INDEX idx_patient_age ON patient(age);

-- After indexing
EXPLAIN ANALYZE
SELECT i.image_id, s.series_id, p.age, p.sex
FROM image i
JOIN series s ON i.series_id = s.series_id
JOIN study st ON s.study_id = st.study_id
JOIN patient p ON st.patient_id = p.patient_id
WHERE p.age BETWEEN 40 AND 60;

-- ===============================================================
--  QUERY 2: Find all male patient images
-- ===============================================================

-- Before indexing
EXPLAIN ANALYZE
SELECT i.image_id, p.sex, st.study_id
FROM image i
JOIN series s ON i.series_id = s.series_id
JOIN study st ON s.study_id = st.study_id
JOIN patient p ON st.patient_id = p.patient_id
WHERE p.sex = 'M';

-- Create index on patient sex
CREATE INDEX idx_patient_sex ON patient(sex);

-- After indexing
EXPLAIN ANALYZE
SELECT i.image_id, p.sex, st.study_id
FROM image i
JOIN series s ON i.series_id = s.series_id
JOIN study st ON s.study_id = st.study_id
JOIN patient p ON st.patient_id = p.patient_id
WHERE p.sex = 'M';

-- ===============================================================
--  QUERY 3: Count number of images per patient
-- ===============================================================

-- Before indexing
EXPLAIN ANALYZE
SELECT p.patient_id, COUNT(i.image_id) AS image_count
FROM patient p
JOIN study st ON p.patient_id = st.patient_id
JOIN series s ON st.study_id = s.study_id
JOIN image i ON s.series_id = i.series_id
GROUP BY p.patient_id;

-- Create indexes for join optimization
CREATE INDEX idx_study_patient_id ON study(patient_id);
CREATE INDEX idx_series_study_id ON series(study_id);
CREATE INDEX idx_image_series_id ON image(series_id);

-- After indexing
EXPLAIN ANALYZE
SELECT p.patient_id, COUNT(i.image_id) AS image_count
FROM patient p
JOIN study st ON p.patient_id = st.patient_id
JOIN series s ON st.study_id = s.study_id
JOIN image i ON s.series_id = i.series_id
GROUP BY p.patient_id;

-- ===============================================================
--  QUERY 4: Get all images from a specific study
-- ===============================================================

-- Before indexing
EXPLAIN ANALYZE
SELECT i.image_id, s.series_id
FROM image i
JOIN series s ON i.series_id = s.series_id
WHERE s.study_id = 101;

-- Indexes for study filtering
CREATE INDEX IF NOT EXISTS idx_series_study_id ON series(study_id);
CREATE INDEX IF NOT EXISTS idx_image_series_id ON image(series_id);

-- After indexing
EXPLAIN ANALYZE
SELECT i.image_id, s.series_id
FROM image i
JOIN series s ON i.series_id = s.series_id
WHERE s.study_id = 101;

