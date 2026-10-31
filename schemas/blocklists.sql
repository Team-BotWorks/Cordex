CREATE TABLE IF NOT EXISTS Blocklists (
    target_id   INTEGER NOT NULL,
    target_type TEXT    NOT NULL CHECK(target_type IN ('user', 'guild')),
    PRIMARY KEY (target_id, target_type)
);