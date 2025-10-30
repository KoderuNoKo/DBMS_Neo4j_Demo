-- ============================================
-- 🔹 1. Kiểm tra dữ liệu ban đầu
-- ============================================
SELECT * FROM rating LIMIT 10;
SELECT * FROM movie LIMIT 10;

-- ============================================
-- 🔹 2. Đo tốc độ truy vấn ban đầu (chưa có index)
-- ============================================
EXPLAIN ANALYZE
SELECT * FROM rating
WHERE movieid = 50;

EXPLAIN ANALYZE
SELECT m.title, r.rating
FROM movie m
JOIN rating r ON m.movieid = r.movieid
WHERE r.userid = 100;

-- ============================================
-- 🔹 3. Tạo index để tối ưu truy vấn
-- (Xóa index cũ nếu có để tránh lỗi)
-- ============================================
DROP INDEX IF EXISTS idx_rating_movieid;
DROP INDEX IF EXISTS idx_rating_userid;

CREATE INDEX idx_rating_movieid ON rating(movieid);
CREATE INDEX idx_rating_userid ON rating(userid);

-- ============================================
-- 🔹 4. Đo lại tốc độ sau khi có index
-- So sánh "Execution Time" với lần đầu
-- ============================================
EXPLAIN ANALYZE
SELECT * FROM rating
WHERE movieid = 50;

EXPLAIN ANALYZE
SELECT m.title, r.rating
FROM movie m
JOIN rating r ON m.movieid = r.movieid
WHERE r.userid = 100;
