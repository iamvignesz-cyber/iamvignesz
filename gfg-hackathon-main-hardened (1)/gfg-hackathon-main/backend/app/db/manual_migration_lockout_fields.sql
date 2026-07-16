-- Base.metadata.create_all() (used for speed in this hackathon project,
-- see README "Known limitations") only creates tables that don't exist yet
-- — it will NOT add new columns to a table that's already there.
--
-- If you have an existing database (e.g. a already-deployed Render DB, or a
-- local docker-compose volume from before this change), run this once so
-- the new account-lockout columns on `users` exist. A brand-new/empty
-- database does not need this — create_all() will include them automatically.

ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS locked_until TIMESTAMP NULL;
