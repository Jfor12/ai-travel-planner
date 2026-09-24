-- One-off: copy guides the old version cached in saved_itineraries into the new
-- guide_cache table, so they don't have to be generated (and paid for) again.
--
-- Only rows that look clean are copied: the expected "Place [Month]" name, a real
-- month, and no '<' or '>' anywhere (no HTML). Where one place/month has several
-- rows, the OLDEST is used, since later rows could have been added through the
-- old unauthenticated save endpoint. Rows already in guide_cache are left alone.
--
-- Run it in the Supabase SQL editor after the new API has started once.
INSERT INTO guide_cache (destination_key, month, guide_text)
SELECT DISTINCT ON (destination_key, month) destination_key, month, itinerary_text
FROM (
    SELECT lower(regexp_replace(trim(substring(destination FROM '^(.*) \[[A-Za-z]+\]$')), '\s+', ' ', 'g')) AS destination_key,
           substring(destination FROM ' \[([A-Za-z]+)\]$') AS month,
           itinerary_text,
           created_at
    FROM saved_itineraries
) old
WHERE month IN ('January','February','March','April','May','June','July',
                'August','September','October','November','December')
  AND destination_key ~ '^[[:alpha:]][[:alpha:] ''’.,-]{0,79}$'
  AND itinerary_text !~ '[<>]'
ORDER BY destination_key, month, created_at ASC
ON CONFLICT (destination_key, month) DO NOTHING;
