-- 1. Property counts
SELECT 'Source Properties' as metric, COUNT(*) as count FROM makemystay_temp_migration.properties
UNION ALL
SELECT 'Destination Properties' as metric, COUNT(*) as count FROM property_portal.properties;

-- 2. Image counts
SELECT 'Source Images' as metric, COUNT(*) as count FROM makemystay_temp_migration.property_images
UNION ALL
SELECT 'Destination Images' as metric, COUNT(*) as count FROM property_portal.property_images;

-- 3. Amenities migrated (new table)
SELECT 'Destination Amenities' as metric, COUNT(*) as count FROM property_portal.property_amenities;

-- 4. Pricing migrated (new table)
SELECT 'Destination Pricing Rows' as metric, COUNT(*) as count FROM property_portal.property_pricing;

-- 5. Missing properties (in source but not in destination)
SELECT source.id as missing_property_id
FROM makemystay_temp_migration.properties source
LEFT JOIN property_portal.properties dest ON dest.property_id = CONCAT('PROP-', source.id)
WHERE dest.id IS NULL;

-- 6. Orphan images (in destination but referencing a non-existent property)
SELECT img.id as orphan_image_id
FROM property_portal.property_images img
LEFT JOIN property_portal.properties prop ON img.property_id = prop.id
WHERE prop.id IS NULL;
