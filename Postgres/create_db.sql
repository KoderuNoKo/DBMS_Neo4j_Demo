CREATE TABLE Movie (
    movieId INT PRIMARY KEY,
    title VARCHAR(256),
    genres VARCHAR(256)
);

CREATE TABLE Rating (
    userId INT,
    movieId INT REFERENCES Movie(movieId),
    rating NUMERIC,
    timestamp BIGINT,
    CONSTRAINT pk_rating PRIMARY KEY (userId, movieId)
);


CREATE TABLE Link (
    movieId INT PRIMARY KEY REFERENCES Movie(movieId),
    imdbId INT,
    tmdbId INT
);

CREATE TABLE Tag (
    tagId SERIAL,
    userId INT,
    movieId INT REFERENCES Movie(movieId),
    tag VARCHAR(1024),
    timestamp BIGINT
);

CREATE TABLE GenomeTag (
    tagId INT PRIMARY KEY,
    tag VARCHAR(1024)
);

CREATE TABLE GenomeScore (
    movieId INT REFERENCES Movie(movieId),
    tagId INT REFERENCES GenomeTag(tagId),
    relevance NUMERIC

    CONSTRAINT pk_gscore PRIMARY KEY (movieId, tagId)
);