import pymysql

conn = pymysql.connect(host='127.0.0.1', port=3336, user='appuser', password='StrongPassword@123', cursorclass=pymysql.cursors.DictCursor)
cursor = conn.cursor()

# Check property_type, category, and status in PP for properties that were migrated
cursor.execute("SELECT status, property_type, category FROM property_portal.properties WHERE status = 'draft' OR status = 'Draft' LIMIT 5")
print("Migrated properties sample:")
for r in cursor.fetchall():
    print(r)
    
cursor.execute("SELECT status, property_type, category FROM property_portal.properties WHERE status != 'draft' AND status != 'Draft' LIMIT 5")
print("\nExisting properties sample:")
for r in cursor.fetchall():
    print(r)
    
# Check where the prices are stored in PP for existing properties
cursor.execute("SELECT p.id, pp.starting_price, pp.private_price, p.rental_options, p.pg_options FROM property_portal.properties p LEFT JOIN property_portal.property_pricing pp ON p.id = pp.property_id WHERE p.status != 'draft' AND p.status != 'Draft' LIMIT 5")
print("\nPricing sample for existing PP properties:")
for r in cursor.fetchall():
    print(r)
    
# Let's see makemystay property table for private_price, starting_price etc.
cursor.execute("SELECT id, private_price, starting_price, single_price, double_price, triple_price FROM makemystay.properties LIMIT 5")
print("\nPricing columns in MMS properties table:")
for r in cursor.fetchall():
    print(r)

conn.close()
