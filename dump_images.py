import mysql.connector
import json

try:
    conn = mysql.connector.connect(
        host='127.0.0.1',
        port=3336,
        user='appuser',
        password='StrongPassword@123'
    )
    
    cursor_p = conn.cursor(dictionary=True)
    cursor_m = conn.cursor(dictionary=True)
    cursor_update = conn.cursor()
    
    # 1. Get properties in property_portal that don't have images (the ones we just inserted)
    cursor_p.execute("SELECT id, property_id FROM property_portal.properties WHERE images IS NULL")
    missing_images_props = cursor_p.fetchall()
    
    print(f"Found {len(missing_images_props)} properties without images in property_portal.")
    
    updated_count = 0
    images_inserted = 0
    
    for prop in missing_images_props:
        p_id = prop['id']
        prop_str_id = prop['property_id']
        
        # Extract original makemystay id from property_id (e.g. 'PROP-42' -> 42)
        if not prop_str_id or not prop_str_id.startswith('PROP-'):
            continue
            
        try:
            m_id = int(prop_str_id.replace('PROP-', ''))
        except ValueError:
            continue
            
        # 2. Get images from makemystay.property_images
        cursor_m.execute("SELECT * FROM makemystay.property_images WHERE property_id = %s", (m_id,))
        m_images = cursor_m.fetchall()
        
        if not m_images:
            continue
            
        image_urls = []
        for img in m_images:
            img_url = img['image_url']
            image_urls.append(img_url)
            
            # Insert into property_portal.property_images
            # Note: keeping is_primary, sort_order, etc.
            insert_query = """
                INSERT INTO property_portal.property_images 
                (property_id, image_url, is_primary, sort_order, created_at, is_deleted, content_type, file_size)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor_update.execute(insert_query, (
                p_id, 
                img_url, 
                img.get('is_primary', 0), 
                img.get('sort_order', 0), 
                img.get('created_at'), 
                img.get('is_deleted', 0), 
                img.get('content_type'), 
                img.get('file_size')
            ))
            images_inserted += 1
            
        # 3. Update the JSON images array in property_portal.properties
        images_json = json.dumps(image_urls)
        cursor_update.execute(
            "UPDATE property_portal.properties SET images = %s WHERE id = %s",
            (images_json, p_id)
        )
        updated_count += 1
        
    conn.commit()
    print(f"Successfully migrated images for {updated_count} properties. Total {images_inserted} images inserted.")
    
except Exception as e:
    print('Error:', e)
finally:
    if 'conn' in locals() and conn.is_connected():
        cursor_p.close()
        cursor_m.close()
        cursor_update.close()
        conn.close()
