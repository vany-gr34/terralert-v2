BEGIN READ ONLY;
SELECT count(*) AS rows, count(DISTINCT commune_id) AS unique_communes,
       sum((attributes->>'P_ensemble')::bigint) AS population_total,
       count(*) FILTER (WHERE attributes->'P_menages' = 'null'::jsonb) AS missing_households,
       count(*) FILTER (WHERE producer IS NULL AND reference_year IS NULL AND status='provisional') AS provisional_unconfirmed
FROM public.pilot_population;
SELECT p.commune_id, c.name_fr, (p.attributes->>'P_ensemble')::bigint AS population
FROM public.pilot_population p JOIN public.pilot_communes c USING (commune_id)
ORDER BY p.commune_id;
ROLLBACK;
