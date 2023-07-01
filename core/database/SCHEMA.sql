CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;


CREATE TABLE IF NOT EXISTS users (
    uid BIGINT PRIMARY KEY,
    github_id BIGINT UNIQUE NOT NULL,
    username TEXT NOT NULL,
    admin BOOLEAN NOT NULL DEFAULT false,
    bearer TEXT NOT NULL,
    created TIMESTAMP DEFAULT (now() at time zone 'utc')
);


CREATE TABLE IF NOT EXISTS tokens (
    tid SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(uid),
    token_name VARCHAR(32) NOT NULL CHECK (LENGTH(token_name) > 2),
    token_description VARCHAR(512),
    token TEXT NOT NULL,
    verified BOOLEAN NOT NULL DEFAULT false,
    websockets BOOLEAN NOT NULL DEFAULT false,
    invalid BOOLEAN NOT NULL DEFAULT false,
    UNIQUE (user_id, token_name)
);


CREATE TABLE IF NOT EXISTS bans (
    ip TEXT UNIQUE,
    userid BIGINT UNIQUE,
    reason TEXT
);

CREATE TABLE IF NOT EXISTS logs (
    ip TEXT,
    userid BIGINT REFERENCES users(uid),
    appid BIGINT REFERENCES tokens(tid),
    accessed TIMESTAMP WITH TIME ZONE,
    cf_ray TEXT,
    cf_country TEXT,
    method TEXT NOT NULL,
    route TEXT NOT NULL,
    body TEXT,
    response_code INTEGER NOT NULL
);