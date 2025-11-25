DROP TABLE IF EXISTS contents;

CREATE TABLE contents (
    id SERIAL PRIMARY KEY,
    phash TEXT UNIQUE NOT NULL,
    publisher TEXT NOT NULL,
    title TEXT,
    description TEXT,
    timestamp BIGINT,
    txhash TEXT,
    blocknumber INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_phash ON contents(phash);
CREATE INDEX idx_publisher ON contents(publisher);
