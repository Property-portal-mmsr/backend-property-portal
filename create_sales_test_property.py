from fastapi.testclient import TestClient
from app.main import app
from app.dependencies import get_current_admin_user
from app.models.employee import Employee
from app.database.database import get_db

def mock_admin():
    return Employee(id=1, name="Test Admin", email="admin@test.com", role="Admin")

app.dependency_overrides[get_current_admin_user] = mock_admin

client = TestClient(app)

payload = {
    "name": "TEST - MakeMyStay Sales Review Property",
    "description": "Premium fully furnished co-living property suitable for working professionals and students.",
    "city": "Bangalore",
    "state": "Karnataka",
    "pincode": "560102",
    "deposit": 30000,
    "unitType": "Bed",
    "furnishing": "Fully Furnished",
    "propertyType": "PG",
    "category": "Co-Living",
    "location": "HSR Layout",
    "address": "27th Main Road, HSR Layout, Bangalore",
    "status": "Available",
    "images": [
        "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=800&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1502672260266-1c1c24240f38?w=800&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1513694203232-719a280e022f?w=800&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1505691938895-1758d7feb511?w=800&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1493809842364-78817add7ffb?w=800&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1524758631624-e2822e304c36?w=800&auto=format&fit=crop"
    ],
    "owner": {"name": "Test Property Owner", "phone": "9999999999"},
    "caretaker": {"name": "Test Caretaker", "phone": "8888888888"},
    "availableUnits": 6,
    "totalUnits": 20,
    "amenities": [
        "WiFi", "AC", "TV", "Bed", "Wardrobe", "Geyser", 
        "Washing Machine", "Refrigerator", "Gas Stove", "Lift", 
        "Security", "CCTV", "Bike Parking", "Sofa", "Dressing Table"
    ],
    "price": {
        "starting": 10000,
        "single": 15000,
        "double": 12000,
        "triple": 10000,
        "private": 20000
    },
    "salesKit": {
        "photoAlbum": "https://example.com/photo_album",
        "brochure": "https://example.com/brochure.pdf",
        "wap": "https://wa.me/919999999999",
        "pricing": "https://example.com/pricing.pdf",
        "map": "https://maps.google.com/?q=HSR+Layout"
    },
    "preferredFor": "Anyone",
    "youtubeLink": "https://youtube.com/watch?v=dQw4w9WgXcQ"
}

response = client.post("/api/v1/properties", json=payload)
print("Create Status:", response.status_code)
if response.status_code == 201:
    print("Created ID:", response.json()["id"])
else:
    print("Error:", response.json())















