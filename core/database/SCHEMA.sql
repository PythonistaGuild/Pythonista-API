CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;


CREATE TABLE IF NOT EXISTS users (
    uid BIGINT PRIMARY KEY,
    github_id BIGINT UNIQUE NOT NULL,
    admin BOOLEAN NOT NULL DEFAULT false,
    bearer TEXT NOT NULL,
    created TIMESTAMP DEFAULT (now() at time zone 'utc')
);


CREATE TABLE IF NOT EXISTS tokens (
    tid SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(uid),
    token_name VARCHAR(32) NOT NULL CHECK (LENGTH(token_name) > 2),
    token_description VARCHAR(256),
    token TEXT NOT NULL,
    verified BOOLEAN NOT NULL DEFAULT false,
    uses INTEGER NOT NULL DEFAULT 0,
    UNIQUE (user_id, token_name)
);


CREATE TABLE IF NOT EXISTS bans (
    ip TEXT UNIQUE,
    userid BIGINT UNIQUE,
    reason TEXT
);