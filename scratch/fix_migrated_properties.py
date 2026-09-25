import pymysql

try:
    conn = pymysql.connect(
        host='127.0.0.1',
        port=3336,
        user='appuser',
        password='StrongPassword@123',
        cursorclass=pymysql.cursors.DictCursor
    )
    cursor = conn.cursor()
    cursor_update = conn.cursor()
    
    # Get all drafted properties in PP that we need to fix
    cursor.execute("SELECT id, property_id FROM property_portal.properties WHERE status = 'draft' OR status = 'Draft'")
    draft_props = cursor.fetchall()
    
    print(f"Found {len(draft_props)} drafted properties to fix.")
    
    fixed_count = 0
    pricing_inserted = 0
    
    for dp in draft_props:
        p_id_int = dp['id']
        p_id_str = dp['property_id']
        
        if not p_id_str or not p_id_str.startswith('PROP-'):
            continue
            
        m_id = int(p_id_str.replace('PROP-', ''))
        
        # Get data from MMS
        cursor.execute("SELECT listing_type, private_price, single_price, double_price, triple_price, starting_price FROM makemystay.properties WHERE id = %s", (m_id,))
        mms_data = cursor.fetchone()
        
        if not mms_data:
            continue
            
        # Update category and status in PP
        listing_type = mms_data.get('listing_type', 'rent')
        if not listing_type:
            listing_type = 'rent'
            
        cursor_update.execute(
            "UPDATE property_portal.properties SET category = %s, status = 'Available' WHERE id = %s",
            (listing_type, p_id_int)
        )
        
        # Check if pricing exists in PP
        cursor.execute("SELECT id FROM property_portal.property_pricing WHERE property_id = %s", (p_id_int,))
        has_pricing = cursor.fetchone()
        
        if not has_pricing:
            # Insert pricing
            cursor_update.execute(
                """
                INSERT INTO property_portal.property_pricing 
                (property_id, private_price, single_price, double_price, triple_price, starting_price)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    p_id_int,
                    mms_data.get('private_price'),
                    mms_data.get('single_price'),
                    mms_data.get('double_price'),
                    mms_data.get('triple_price'),
                    mms_data.get('starting_price')
                )
            )
            pricing_inserted += 1
            
        fixed_count += 1
        
    conn.commit()
    print(f"Successfully fixed {fixed_count} properties and inserted {pricing_inserted} pricing records.")
    
except Exception as e:
    print("Error:", e)
finally:
    if 'conn' in locals() and conn.open:
        cursor.close()
        cursor_update.close()
        conn.close()
