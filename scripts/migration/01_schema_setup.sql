USE property_portal;

CREATE TABLE IF NOT EXISTS `property_images` (
  `id` int NOT NULL AUTO_INCREMENT,
  `property_id` int NOT NULL,
  `image_url` varchar(500) NOT NULL,
  `is_primary` tinyint(1) NOT NULL DEFAULT '0',
  `sort_order` int NOT NULL DEFAULT '0',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `is_deleted` tinyint(1) NOT NULL DEFAULT '0',
  `content_type` varchar(80) NOT NULL DEFAULT 'image/jpeg',
  `file_size` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_property_images_property_id` (`property_id`),
  CONSTRAINT `fk_property_images_prop` FOREIGN KEY (`property_id`) REFERENCES `properties` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `property_amenities` (
  `id` int NOT NULL AUTO_INCREMENT,
  `property_id` int NOT NULL,
  `amenity_name` varchar(255) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_prop_amenity` (`property_id`, `amenity_name`),
  CONSTRAINT `fk_property_amenities_prop` FOREIGN KEY (`property_id`) REFERENCES `properties` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `property_pricing` (
  `id` int NOT NULL AUTO_INCREMENT,
  `property_id` int NOT NULL,
  `private_price` decimal(10,2) DEFAULT NULL,
  `single_price` decimal(10,2) DEFAULT NULL,
  `double_price` decimal(10,2) DEFAULT NULL,
  `triple_price` decimal(10,2) DEFAULT NULL,
  `starting_price` decimal(10,2) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_prop_pricing` (`property_id`),
  CONSTRAINT `fk_property_pricing_prop` FOREIGN KEY (`property_id`) REFERENCES `properties` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `property_units` (
  `id` int NOT NULL AUTO_INCREMENT,
  `property_id` int NOT NULL,
  `unit_name` varchar(255) DEFAULT NULL,
  `status` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`id`),
  CONSTRAINT `fk_property_units_prop` FOREIGN KEY (`property_id`) REFERENCES `properties` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `property_documents` (
  `id` int NOT NULL AUTO_INCREMENT,
  `property_id` int NOT NULL,
  `document_url` varchar(500) NOT NULL,
  PRIMARY KEY (`id`),
  CONSTRAINT `fk_property_documents_prop` FOREIGN KEY (`property_id`) REFERENCES `properties` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `property_downloads` (
  `id` int NOT NULL AUTO_INCREMENT,
  `property_id` int NOT NULL,
  `download_url` varchar(500) NOT NULL,
  PRIMARY KEY (`id`),
  CONSTRAINT `fk_property_downloads_prop` FOREIGN KEY (`property_id`) REFERENCES `properties` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `property_nearby_places` (
  `id` int NOT NULL AUTO_INCREMENT,
  `property_id` int NOT NULL,
  `place_name` varchar(255) NOT NULL,
  `distance` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`id`),
  CONSTRAINT `fk_property_nearby_places_prop` FOREIGN KEY (`property_id`) REFERENCES `properties` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `property_tags` (
  `id` int NOT NULL AUTO_INCREMENT,
  `property_id` int NOT NULL,
  `tag_name` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_prop_tag` (`property_id`, `tag_name`),
  CONSTRAINT `fk_property_tags_prop` FOREIGN KEY (`property_id`) REFERENCES `properties` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `property_seo` (
  `id` int NOT NULL AUTO_INCREMENT,
  `property_id` int NOT NULL,
  `meta_title` varchar(255) DEFAULT NULL,
  `meta_description` text,
  `meta_keywords` text,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_prop_seo` (`property_id`),
  CONSTRAINT `fk_property_seo_prop` FOREIGN KEY (`property_id`) REFERENCES `properties` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
