PROFILE
CALL db.index.fulltext.queryNodes("movieTitleIndex","Avatar")
YIELD node, score
RETURN node.title, score;