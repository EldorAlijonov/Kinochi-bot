CREATE TABLE IF NOT EXISTS users (
    telegram_id BIGINT PRIMARY KEY,
    full_name VARCHAR(255),
    username VARCHAR(255),
    joined_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_active_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_banned BOOLEAN NOT NULL DEFAULT FALSE,
    referred_by BIGINT,
    start_payload VARCHAR(255)
);

CREATE INDEX IF NOT EXISTS ix_users_joined_at ON users (joined_at);
CREATE INDEX IF NOT EXISTS ix_users_last_active_at ON users (last_active_at);
CREATE INDEX IF NOT EXISTS ix_users_referred_by ON users (referred_by);

CREATE TABLE IF NOT EXISTS user_action_logs (
    id BIGSERIAL PRIMARY KEY,
    user_telegram_id BIGINT NOT NULL,
    action_type VARCHAR(50) NOT NULL,
    movie_id INTEGER,
    movie_code VARCHAR(32),
    subscription_id INTEGER,
    is_success BOOLEAN,
    payload VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_user_action_logs_action_created
    ON user_action_logs (action_type, created_at);
CREATE INDEX IF NOT EXISTS ix_user_action_logs_user_created
    ON user_action_logs (user_telegram_id, created_at);
CREATE INDEX IF NOT EXISTS ix_user_action_logs_movie_id
    ON user_action_logs (movie_id);
CREATE INDEX IF NOT EXISTS ix_user_action_logs_subscription_id
    ON user_action_logs (subscription_id);
