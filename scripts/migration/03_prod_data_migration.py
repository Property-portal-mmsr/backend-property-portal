import pymysql
import json

SOURCE_DB = "makemystay_temp_migration"

# Parse .env securely
env_vars = {}
with open('.env', 'r') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, val = line.split('=', 1)
            env_vars[key.strip()] = val.strip()

PROD_HOST = env_vars.get('DB_HOST', '127.0.0.1')
PROD_PORT = int(env_vars.get('DB_PORT', '3336'))
PROD_USER = env_vars.get('DB_USER', 'appuser')
PROD_PASSWORD = env_vars.get('DB_PASSWORD', '')
PROD_DB = env_vars.get('DB_NAME', 'property_portal')

def get_source_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="",
        database=SOURCE_DB,
        cursorclass=pymysql.cursors.DictCursor
    )

def get_prod_connection():
    return pymysql.connect(
        host=PROD_HOST,
        port=PROD_PORT,
        user=PROD_USER,
        password=PROD_PASSWORD,
        database=PROD_DB,
        cursorclass=pymysql.cursors.DictCursor
    )

def migrate():
    print("Starting production migration...")
    source_conn = get_source_connection()
    dest_conn = get_prod_connection()

    try:
        source_id_to_dest_id = {}
        
        with source_conn.cursor() as s_cur, dest_conn.cursor() as d_cur:
            # 1. Fetch properties
            s_cur.execute("SELECT * FROM properties")
            properties = s_cur.fetchall()
            
            for prop in properties:
                status = "available" if prop.get('is_available') else "unavailable"
                category = prop.get('listing_type', '')
                address = f"{prop.get('location', '')}, {prop.get('city', '')}".strip(', ')
                prop_id_str = f"PROP-{prop['id']}"
                
                # Check if property already exists based on property_id
                d_cur.execute("SELECT id FROM properties WHERE property_id = %s", (prop_id_str,))
                existing = d_cur.fetchone()
                
                if existing:
                    # Update existing
                    dest_id = existing['id']
                    sql_update = """
                    UPDATE properties SET
                        property_name = %s,
                        location = %s,
                        property_type = %s,
                        category = %s,
                        address = %s,
                        status = %s,
                        owner_phone = %s
                    WHERE id = %s
                    """
                    d_cur.execute(sql_update, (
                        prop['property_name'],
                        prop['location'],
                        prop['property_type'],
                        category,
                        address,
                        status,
                        prop.get('phone'),
                        dest_id
                    ))
                else:
                    # Insert new (database assigns ID)
                    sql_insert = """
                    INSERT INTO properties (property_id, property_name, location, property_type, category, address, status, owner_phone)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    d_cur.execute(sql_insert, (
                        prop_id_str,
                        prop['property_name'],
                        prop['location'],
                        prop['property_type'],
                        category,
                        address,
                        status,
                        prop.get('phone')
                    ))
                    dest_id = d_cur.lastrowid
                
                # Save mapping for child tables
                source_id_to_dest_id[prop['id']] = dest_id

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
                    dest_id,
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
                                d_cur.execute(sql_amenity, (dest_id, str(feature).strip()))
                    except json.JSONDecodeError:
                        pass
            
            # 2. Fetch images
            s_cur.execute("SELECT * FROM property_images")
            images = s_cur.fetchall()
            
            for img in images:
                source_prop_id = img['property_id']
                if source_prop_id not in source_id_to_dest_id:
                    continue # Skip orphans from source
                    
                dest_prop_id = source_id_to_dest_id[source_prop_id]
                
                sql_img = """
                INSERT INTO property_images (property_id, image_url, is_primary, sort_order, created_at, content_type, file_size)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    is_primary = VALUES(is_primary),
                    sort_order = VALUES(sort_order),
                    content_type = VALUES(content_type),
                    file_size = VALUES(file_size)
                """
                # We need a unique constraint to make ON DUPLICATE KEY work for images
                # Since property_images might not have a UNIQUE key on (property_id, image_url), 
                # let's manually check if it exists or we can just assume the migration runs once.
                # To be perfectly idempotent without altering schema:
                d_cur.execute("SELECT id FROM property_images WHERE property_id = %s AND image_url = %s", (dest_prop_id, img['image_url']))
                existing_img = d_cur.fetchone()
                if existing_img:
                    sql_upd_img = """
                    UPDATE property_images SET is_primary = %s, sort_order = %s, content_type = %s, file_size = %s
                    WHERE id = %s
                    """
                    d_cur.execute(sql_upd_img, (img['is_primary'], img['sort_order'], img['content_type'], img.get('file_size'), existing_img['id']))
                else:
                    d_cur.execute(sql_img, (
                        dest_prop_id,
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
