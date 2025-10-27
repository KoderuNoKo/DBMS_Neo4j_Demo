PROFILE
MATCH (m:Movie)
WHERE m.title CONTAINS "Avatar"
RETURN m.title;