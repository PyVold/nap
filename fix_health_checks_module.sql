-- Add health_checks module to the active license
-- This ensures "Health Monitoring" appears as enabled on the /license page

-- First, check the current state
SELECT
    id,
    license_tier,
    customer_name,
    enabled_modules,
    is_active
FROM licenses
WHERE is_active = true;

-- Update the active license to include health_checks in enabled_modules
-- This handles different cases based on the current license tier

-- For Starter tier: Ensure health_checks is in the module list
UPDATE licenses
SET enabled_modules = CASE
    -- If the array doesn't contain health_checks, add it
    WHEN NOT ('health_checks' = ANY(enabled_modules)) THEN
        array_append(enabled_modules, 'health_checks')
    ELSE
        enabled_modules
END
WHERE is_active = true
  AND license_tier = 'starter'
  AND NOT ('health_checks' = ANY(enabled_modules));

-- For Professional tier: Ensure health_checks is in the module list
UPDATE licenses
SET enabled_modules = CASE
    WHEN NOT ('health_checks' = ANY(enabled_modules)) THEN
        array_append(enabled_modules, 'health_checks')
    ELSE
        enabled_modules
END
WHERE is_active = true
  AND license_tier = 'professional'
  AND NOT ('health_checks' = ANY(enabled_modules));

-- For Enterprise tier: Usually has "all" but let's ensure it's there if using explicit list
UPDATE licenses
SET enabled_modules = CASE
    WHEN NOT ('health_checks' = ANY(enabled_modules)) AND NOT ('all' = ANY(enabled_modules)) THEN
        array_append(enabled_modules, 'health_checks')
    ELSE
        enabled_modules
END
WHERE is_active = true
  AND license_tier = 'enterprise'
  AND NOT ('health_checks' = ANY(enabled_modules))
  AND NOT ('all' = ANY(enabled_modules));

-- Verify the update
SELECT
    id,
    license_tier,
    customer_name,
    enabled_modules,
    'health_checks' = ANY(enabled_modules) AS has_health_checks
FROM licenses
WHERE is_active = true;
