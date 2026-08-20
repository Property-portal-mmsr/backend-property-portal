from fastapi.testclient import TestClient
from app.main import app
from app.dependencies import get_current_admin_user
from app.models.employee import Employee
from app.database.database import get_db

# Mock the admin dependency
def mock_admin():
    return Employee(id=1, name="Test Admin", email="admin@test.com", role="Admin")

app.dependency_overrides[get_current_admin_user] = mock_admin

client = TestClient(app)

def run_test():
    # 1. Create a full property
    payload = {
        "name": "E2E Property Test - API",
        "description": "This is a full test property.",
        "city": "Bangalore",
        "state": "Karnataka",
        "pincode": "560034",
        "deposit": 50000,
        "unitType": "Bed",
        "furnishing": "Fully Furnished",
        "propertyType": "PG",
        "category": "Co-Living",
        "location": "Koramangala",
        "address": "123 Main St",
        "status": "Available",
        "images": ["url1", "url2"],
        "owner": {"name": "John", "phone": "9999999999"},
        "caretaker": {"name": "Jane", "phone": "8888888888"},
        "availableUnits": 5,
        "totalUnits": 10,
        "amenities": ["WiFi", "AC"],
        "price": {
            "starting": 10000,
            "single": 15000,
            "double": 12000,
            "triple": 10000,
            "private": 20000
        },
        "salesKit": {
            "brochure": "brochure_url",
            "photoAlbum": "photo_url"
        },
        "preferredFor": "Anyone",
        "youtubeLink": "youtube_url"
    }
    
    response = client.post("/api/v1/properties", json=payload)
    print("Create Status:", response.status_code)
    
    if response.status_code != 201:
        print("Error:", response.json())
        return
        
    prop_id = response.json()["id"]
    print("Created ID:", prop_id)
    
    # 2. Get property and verify fields
    response = client.get(f"/api/v1/properties/{prop_id}")
    data = response.json()
    
    print("Verification:")
    print("- Description:", data.get("description") == payload["description"])
    print("- City:", data.get("city") == payload["city"])
    print("- Deposit:", data.get("deposit") == payload["deposit"])
    print("- Price Single:", data.get("price", {}).get("single") == payload["price"]["single"])
    print("- Sales Kit Brochure:", data.get("salesKit", {}).get("brochure") == payload["salesKit"]["brochure"])
    
if __name__ == "__main__":
    run_test()
