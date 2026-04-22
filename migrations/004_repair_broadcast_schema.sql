ALTER TABLE broadcast_jobs
    ADD COLUMN IF NOT EXISTS retry_count INTEGER NOT NULL DEFAULT 0;

ALTER TABLE broadcast_jobs
    ALTER COLUMN retry_count DROP DEFAULT;

ALTER TABLE broadcast_campaigns
    ADD COLUMN IF NOT EXISTS file_id VARCHAR(512);

UPDATE broadcast_campaigns
SET status = 'queued'
WHERE status = 'sending'
  AND id IN (
      SELECT campaign_id
      FROM broadcast_jobs
      WHERE status = 'queued'
  );
