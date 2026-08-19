import pymysql
import json

SOURCE_DB = "makemystay_temp_migration"
DEST_DB = "property_portal"
HOST = "localhost"
USER = "root"
PASSWORD = "" # Assuming no password as per previous commands

def get_connection(db):
    return pymysql.connect(
        host=HOST,
        user=USER,
        password=PASSWORD,
        database=db,
        cursorclass=pymysql.cursors.DictCursor
    )

def migrate():
    print("Starting migration...")
    source_conn = get_connection(SOURCE_DB)
    dest_conn = get_connection(DEST_DB)

    try:
        with source_conn.cursor() as s_cur:
            # 1. Fetch properties
            s_cur.execute("SELECT * FROM properties")
            properties = s_cur.fetchall()
            
            with dest_conn.cursor() as d_cur:
                for prop in properties:
                    # UPSERT Property
                    status = "available" if prop.get('is_available') else "unavailable"
                    category = prop.get('listing_type', '')
                    
                    sql_prop = """
                    INSERT INTO properties (id, property_id, property_name, location, property_type, category, address, status, owner_phone)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE 
                        property_name = VALUES(property_name),
                        location = VALUES(location),
                        property_type = VALUES(property_type),
                        category = VALUES(category),
                        address = VALUES(address),
                        status = VALUES(status),
                        owner_phone = VALUES(owner_phone)
                    """
                    address = f"{prop.get('location', '')}, {prop.get('city', '')}".strip(', ')
                    
                    d_cur.execute(sql_prop, (
                        prop['id'],
                        f"PROP-{prop['id']}",
                        prop['property_name'],
                        prop['location'],
                        prop['property_type'],
                        category,
                        address,
                        status,
                        prop.get('phone')
                    ))

                    # UPSERT Pricing
                    sql_pricing = """
                    INSERT INTO property_pricing (property_id, private_price, single_price, double_price, triple_price, starting_price)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        private_price = VALUES(private_price),
                        single_price = VALUES(single_price),
                        double_price = VALUES(double_price),
                        triple_price = VALUES(triple_price),
                        starting_price = VALUES(starting_price)
                    """
                    d_cur.execute(sql_pricing, (
                        prop['id'],
                        prop.get('private_price'),
                        prop.get('single_price'),
                        prop.get('double_price'),
                        prop.get('triple_price'),
                        prop.get('starting_price')
                    ))

                    # Process amenities (features)
                    features_json = prop.get('features')
                    if features_json:
                        try:
                            if isinstance(features_json, str):
                                features = json.loads(features_json)
                            else:
                                features = features_json
                            
                            if isinstance(features, list):
                                for feature in features:
                                    if not feature: continue
                                    sql_amenity = """
                                    INSERT IGNORE INTO property_amenities (property_id, amenity_name)
                                    VALUES (%s, %s)
                                    """
                                    d_cur.execute(sql_amenity, (prop['id'], str(feature).strip()))
                        except json.JSONDecodeError:
                            pass
                
            # 2. Fetch images
            s_cur.execute("SELECT * FROM property_images")
            images = s_cur.fetchall()
            
            with dest_conn.cursor() as d_cur:
                for img in images:
                    sql_img = """
                    INSERT INTO property_images (id, property_id, image_url, is_primary, sort_order, created_at, content_type, file_size)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        image_url = VALUES(image_url),
                        is_primary = VALUES(is_primary),
                        sort_order = VALUES(sort_order),
                        content_type = VALUES(content_type),
                        file_size = VALUES(file_size)
                    """
                    d_cur.execute(sql_img, (
                        img['id'],
                        img['property_id'],
                        img['image_url'],
                        img['is_primary'],
                        img['sort_order'],
                        img['created_at'],
                        img['content_type'],
                        img.get('file_size')
                    ))
                
        dest_conn.commit()
        print(f"Successfully migrated {len(properties)} properties and {len(images)} images.")
        
    except Exception as e:
        dest_conn.rollback()
        print(f"Error during migration: {e}")
        raise e
    finally:
        source_conn.close()
        dest_conn.close()

if __name__ == "__main__":
    migrate()
