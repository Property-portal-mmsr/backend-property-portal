# Property Portal - Backend

## Setup

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   ```

2. **Environment Variables**
   ```bash
   cp .env.example .env
   ```
   *Note: Never commit `.env` to git.*

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run Local Development Server**
   ```bash
   uvicorn app.main:app --reload
   ```

## Folder Structure

```text
property-portal-backend/
├── app/
├── routers/
├── models/
├── services/
├── core/
├── .env.example
└── .env (Git ignored)
```

## Coding Conventions
- Never hardcode URLs or secrets in the code.
- Ensure all secrets are kept out of the code and `.env.example`.
