-- Find play with match_candidates but without play_resolution
SELECT p.play_id
FROM play p
LEFT JOIN play_resolution pr
    ON pr.play_id = p.play_id
WHERE
    EXISTS(SELECT candidate_id FROM match_candidate mc WHERE mc.play_id = p.play_id ) AND
    pr.play_id IS NULL;

-- Delete match_candidates without play_resolution to force a check
DELETE FROM match_candidate WHERE play_id IN (
    SELECT p.play_id
        FROM play p
        LEFT JOIN play_resolution pr
            ON pr.play_id = p.play_id
        WHERE
            EXISTS(SELECT candidate_id FROM match_candidate mc WHERE mc.play_id = p.play_id ) AND
            pr.play_id IS NULL;
)

-- Find latest resolutions with low score
SELECT
    p.play_id,
    pr.chosen_score,
    p.title_raw,
    s.song_title,
    p.performer_raw,
    s.song_performers
    FROM play p
    LEFT JOIN play_resolution pr
        ON pr.play_id = p.play_id
    LEFT JOIN song s
        ON s.song_id = pr.song_id
    WHERE
        pr.chosen_score > 0 AND pr.chosen_score < 0.7
ORDER BY pr.decided_at DESC
LIMIT 20;


-- Remove duplicated match_candidate
WITH ranked AS (
  SELECT
    candidate_id,
    play_id,
    song_id,
    ROW_NUMBER() OVER (
      PARTITION BY play_id, song_id
      ORDER BY candidate_score DESC, candidate_id ASC
    ) AS rn
  FROM match_candidate
)
DELETE FROM match_candidate
WHERE candidate_id IN (
  SELECT candidate_id
  FROM ranked
  WHERE rn > 1
);
