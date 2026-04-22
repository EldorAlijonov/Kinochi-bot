ALTER TABLE movies
ADD COLUMN IF NOT EXISTS title VARCHAR(255);

UPDATE movies
SET title = LEFT(
    COALESCE(
        NULLIF(BTRIM(BTRIM(BTRIM(split_part(COALESCE(caption, ''), E'\n', 1)), '/')), ''),
        'Nomsiz kino'
    ),
    255
)
WHERE title IS NULL;

ALTER TABLE movies
ALTER COLUMN title SET NOT NULL;
