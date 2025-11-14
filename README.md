# FOSSEE-SCREENING Backend

This is the backend API for the FOSSEE-SCREENING project, built using Django 3.2.6 and Django REST Framework.

---

## Features

- REST API for chemical process equipment data
- Token-based authentication
- Swagger API documentation
- CORS enabled for frontend access
- PostgreSQL database support

---

## Setup Instructions

### 1. Clone the repository
```
git clone <your-repo-url>
cd <your-repo-directory>
```
### 2. Create and activate a virtual environment
```
python -m venv venv
source venv/bin/activate # On Windows use venv\Scripts\activate
```

### 3. Install dependencies
```
pip install -r requirements.txt
```
### 4. Configure environment variables

Create a `.env` file at the project root with the following variables (replace values accordingly):
```
DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=fossee-screening.onrender.com,localhost,127.0.0.1
DATABASE_URL=postgres://username:password@your-db-host:port/dbname
```

### 5. Run database migrations
```
python manage.py migrate
```

### 6. Create a superuser (for admin access)
```
python manage.py createsuperuser
```

### 7. Run the development server locally (optional)
```
python manage.py runserver
```

### 8. Deployment

- Ensure the environment variables are set in your deployment platform (e.g., Render).
- Set Python runtime version to 3.11.10 using `runtime.txt`:
```
python-3.11.10
```

- Your deployment start command should include migrations if possible:
```
python manage.py migrate && gunicorn equipment_backend.wsgi
```
---

## API Usage

- Access API endpoints under `/api/`.
- Swagger UI available at `/swagger/`.

---

## Troubleshooting

- Login fails? Ensure user exists in the deployed database.
- Database errors? Verify `DATABASE_URL` and run migrations.
- Deployment errors? Check logs and confirm Python version is 3.11.10.

---



