ALTER TABLE subscriptions
ADD CONSTRAINT uq_subscriptions_invite_link UNIQUE (invite_link);
