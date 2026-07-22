from fastapi import FastAPI

from app.database.database import Base, engine

# Import models
from app.models.employee import Employee
from app.models.owner import Owner
from app.models.property import Property

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Property Portal API")


@app.get("/")
def root():
    return {
        "message": "Property Portal API Running 🚀"
    }