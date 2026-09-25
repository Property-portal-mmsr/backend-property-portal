import pymysql
import json
from datetime import datetime

try:
    conn = pymysql.connect(
        host='127.0.0.1',
        port=3336,
        user='appuser',
        password='StrongPassword@123',
        cursorclass=pymysql.cursors.DictCursor
    )
    
    cursor = conn.cursor()
    
    # Get all properties from PP to find which ones we already have
    cursor.execute("SELECT property_id FROM property_portal.properties WHERE property_id IS NOT NULL")
    existing_pp_props = cursor.fetchall()
    existing_pp_ids = set()
    for p in existing_pp_props:
        pid = p['property_id']
        if pid and pid.startswith('PROP-'):
            try:
                m_id = int(pid.replace('PROP-', ''))
                existing_pp_ids.add(m_id)
            except:
                pass
                
    print(f"Existing properties in PP: {len(existing_pp_ids)}")
    
    # Get properties from MMS
    cursor.execute("SELECT * FROM makemystay.properties WHERE is_deleted = 0")
    mms_props = cursor.fetchall()
    
    print(f"Total active properties in MMS: {len(mms_props)}")
    
    missing_props = [p for p in mms_props if p['id'] not in existing_pp_ids]
    print(f"Missing properties to migrate: {len(missing_props)}")
    
    inserted = 0
    images_inserted = 0
    
    for mp in missing_props:
        # map fields
        p_id = f"PROP-{mp['id']}"
        p_name = mp.get('property_name')
        p_type = mp.get('property_type')
        category = mp.get('property_category')
        location = mp.get('location')
        address = mp.get('locality') # or map_link?
        status = mp.get('status')
        owner_name = mp.get('owner_name')
        owner_phone = mp.get('owner_phone')
        
        description = mp.get('description')
        city = mp.get('city')
        furnishing = mp.get('furnishing')
        
        features = mp.get('features')
        amenities_json = features if features else '[]'
        if isinstance(amenities_json, (dict, list)):
             amenities_json = json.dumps(amenities_json)
        
        insert_query = """
            INSERT INTO property_portal.properties 
            (property_id, property_name, property_type, category, location, address, status, owner_name, owner_phone, description, city, furnishing, amenities)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (
            p_id, p_name, p_type, category, location, address, status, owner_name, owner_phone, description, city, furnishing, amenities_json
        ))
        
        new_pp_id = cursor.lastrowid
        inserted += 1
        
        # Now migrate images
        cursor.execute("SELECT * FROM makemystay.property_images WHERE property_id = %s", (mp['id'],))
        m_images = cursor.fetchall()
        
        image_urls = []
        for img in m_images:
            img_url = img['image_url']
            image_urls.append(img_url)
            
            insert_img_query = """
                INSERT INTO property_portal.property_images 
                (property_id, image_url, is_primary, sort_order, created_at, is_deleted, content_type, file_size)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(insert_img_query, (
                new_pp_id, 
                img_url, 
                img.get('is_primary', 0), 
                img.get('sort_order', 0), 
                img.get('created_at'), 
                img.get('is_deleted', 0), 
                img.get('content_type'), 
                img.get('file_size')
            ))
            images_inserted += 1
            
        images_json = json.dumps(image_urls)
        cursor.execute(
            "UPDATE property_portal.properties SET images = %s WHERE id = %s",
            (images_json, new_pp_id)
        )
        
    conn.commit()
    print(f"Successfully inserted {inserted} properties and {images_inserted} images.")

except Exception as e:
    print('Error:', e)
finally:
    if 'conn' in locals() and conn.open:
        cursor.close()
        conn.close()
