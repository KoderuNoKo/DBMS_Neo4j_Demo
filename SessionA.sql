--Session A

BEGIN;
INSERT INTO Movie VALUES (3, 'Avatar', 'Action|Adventure');
SELECT * FROM Movie WHERE movieId = 3;
-- Expect: row visible inside this session only

COMMIT;

BEGIN;
INSERT INTO Movie VALUES (4, 'Gladiator', 'Action|Drama');
SELECT * FROM Movie WHERE movieId = 4;  -- sees it in this session
ROLLBACK;

BEGIN;
INSERT INTO Rating VALUES (9, 99, 4.0, EXTRACT(EPOCH FROM now())::bigint);
ROLLBACK;
-- movieId = 99 does NOT exist => FK violation expected
-- The INSERT will error and the transaction will be marked aborted.

BEGIN;
SELECT * FROM Rating WHERE movieId = 1;
-- Note values (snapshot at time of this statement in READ COMMITTED)

SELECT * FROM Rating WHERE movieId = 1;
-- In READ COMMITTED, a new SELECT will see the updated value (committed by Session B).
COMMIT;







