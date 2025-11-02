-- ============================================
-- 🔹 1. Kiểm tra dữ liệu ban đầu
-- ============================================
SELECT COUNT(*) FROM rating;
SELECT COUNT(*) FROM movie;

-- ============================================
-- 🔹 2. Đo tốc độ truy vấn ban đầu (chưa có index)
-- ============================================
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM rating
WHERE movieid = 9999;

-- ============================================
-- 🔹 3. Tạo index để tối ưu truy vấn
-- (Xóa index cũ nếu có để tránh lỗi)
-- ============================================
DROP INDEX IF EXISTS idx_rating_movieid;
DROP INDEX IF EXISTS idx_rating_userid;
DROP INDEX IF EXISTS idx_rating_pk;

CREATE INDEX idx_rating_movieid ON rating(movieid);
CREATE INDEX idx_rating_userid ON rating(userid);
CREATE INDEX idx_rating_pk ON rating(userid, movieid);

-- ============================================
-- 🔹 4. Đo lại tốc độ sau khi có index
-- So sánh "Execution Time" với lần đầu
-- ============================================
