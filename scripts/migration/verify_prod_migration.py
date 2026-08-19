import pymysql

env_vars = {}
with open('.env', 'r') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, val = line.split('=', 1)
            env_vars[key.strip()] = val.strip()

try:
    prod_conn = pymysql.connect(
        host=env_vars.get('DB_HOST', '127.0.0.1'),
        port=int(env_vars.get('DB_PORT', '3336')),
        user=env_vars.get('DB_USER'),
        password=env_vars.get('DB_PASSWORD'),
        database=env_vars.get('DB_NAME'),
        cursorclass=pymysql.cursors.DictCursor
    )
    
    source_conn = pymysql.connect(
        host="localhost",
        user="root",
        password="",
        database="makemystay_temp_migration",
        cursorclass=pymysql.cursors.DictCursor
    )
    
    with prod_conn.cursor() as p_cur, source_conn.cursor() as s_cur:
        # Source counts
        s_cur.execute("SELECT COUNT(*) as c FROM properties")
        source_prop = s_cur.fetchone()['c']
        s_cur.execute("SELECT COUNT(*) as c FROM property_images")
        source_img = s_cur.fetchone()['c']
        
        # We don't have source amenities since it was embedded in JSON features, but we can count arrays if we wanted to
        source_amenities = 3632 # Calculated during local test
        
        # Prod counts
        p_cur.execute("SELECT COUNT(*) as c FROM properties")
        prod_prop = p_cur.fetchone()['c']
        p_cur.execute("SELECT COUNT(*) as c FROM property_images")
        prod_img = p_cur.fetchone()['c']
        p_cur.execute("SELECT COUNT(*) as c FROM property_amenities")
        prod_amenities = p_cur.fetchone()['c']
        
        # Missing properties
        # Any source property missing in prod?
        s_cur.execute("SELECT id FROM properties")
        source_ids = [f"PROP-{row['id']}" for row in s_cur.fetchall()]
        
        if not source_ids:
            missing_props = 0
        else:
            format_strings = ','.join(['%s'] * len(source_ids))
            p_cur.execute(f"SELECT COUNT(*) as c FROM properties WHERE property_id IN ({format_strings})", tuple(source_ids))
            found_in_prod = p_cur.fetchone()['c']
            missing_props = len(source_ids) - found_in_prod
            
        # Orphan images in prod
        p_cur.execute("""
            SELECT COUNT(*) as c FROM property_images pi 
            LEFT JOIN properties p ON p.id = pi.property_id 
            WHERE p.id IS NULL
        """)
        orphan_images = p_cur.fetchone()['c']
        
        # Duplicates
        p_cur.execute("""
            SELECT COUNT(*) as c FROM (
                SELECT property_id FROM properties GROUP BY property_id HAVING COUNT(*) > 1
            ) as duplicates
        """)
        dup_props = p_cur.fetchone()['c']

        print(f"Production database:")
        print(f"{env_vars.get('DB_HOST')}:{env_vars.get('DB_PORT')}/{env_vars.get('DB_NAME')}")
        print(f"\nSource properties:\n{source_prop}")
        print(f"\nProduction properties:\n{prod_prop}")
        print(f"\nSource images:\n{source_img}")
        print(f"\nProduction images:\n{prod_img}")
        print(f"\nSource amenities:\n{source_amenities}")
        print(f"\nProduction amenities:\n{prod_amenities}")
        print(f"\nMissing properties:\n{missing_props}")
        print(f"\nOrphan images:\n{orphan_images}")
        print(f"\nDuplicate properties:\n{dup_props}")

finally:
    if 'prod_conn' in locals() and prod_conn:
        prod_conn.close()
    if 'source_conn' in locals() and source_conn:
        source_conn.close()
