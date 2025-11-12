BEGIN;

UPDATE patient
SET weight = weight + 5
WHERE sex = 'M';

-- Check change before commit
SELECT * FROM patient WHERE sex = 'M';

COMMIT;

BEGIN;

UPDATE patient
SET weight = weight + 7
WHERE sex = 'F';
SELECT * FROM patient WHERE sex = 'F';

ROLLBACK;

INSERT INTO PATIENT VALUES (9, 40, 'F');

BEGIN;
SELECT AVG(weight) FROM patient;
SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
END;

-- Don’t commit yet

INSERT INTO patient(patient_id, age, sex) VALUES (1000, 60, 'M');
COMMIT;

SELECT * FROM patient WHERE patient_id = '1000';

