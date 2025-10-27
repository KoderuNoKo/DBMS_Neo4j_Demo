--Session B
SELECT * FROM Movie WHERE movieId = 3;
-- Expect: NO rows (uncommitted changes are not visible)

SELECT * FROM Movie WHERE movieId = 3;
-- Expect: row NOW VISIBLE (commit made it durable and visible)

SELECT * FROM Movie WHERE movieId = 4;
-- Expect: NO rows (rollback removed it)


UPDATE Rating SET rating = 1.0 WHERE movieId = 1 AND userId = 1;
COMMIT;

