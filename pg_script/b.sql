SELECT * FROM patient WHERE sex = 'M';
ROLLBACK;

UPDATE patient SET weight = 200 WHERE patient_id = '10';
COMMIT;
