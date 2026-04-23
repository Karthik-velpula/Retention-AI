# Predictive Analytics for Student Retention

Production-oriented full-stack web application for dropout risk prediction, explainable AI, and personalized academic intervention.

## Stack

- Frontend: React, TypeScript, Tailwind CSS, Recharts
- Backend: FastAPI, SQLAlchemy, JWT authentication
- Database: MySQL
- AI/ML: pandas, scikit-learn, Random Forest, Logistic Regression, SHAP
- Alerts: SMTP email automation

## Switching To A New MySQL Connection

If you already created a new MySQL database connection, update `backend/.env` and set either:

```bash
DATABASE_URL=mysql+pymysql://USER:PASSWORD@HOST:3306/DATABASE_NAME
```

or the individual values:

```bash
MYSQL_USER=USER
MYSQL_PASSWORD=PASSWORD
MYSQL_HOST=HOST
MYSQL_PORT=3306
MYSQL_DB=DATABASE_NAME
```

Then re-run:

```bash
cd backend
python -m app.utils.init_db
```

This will create the required tables in the new MySQL database connection.

## Project Structure

```text
backend/
  app/
  data/
  tests/
frontend/
docs/
docker-compose.yml
```

## Backend Setup

1. Create a virtual environment and install dependencies:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

2. Start MySQL:

```bash
cd /Users/karthi/2K26
docker compose up -d
```

3. Initialize the database and seed admin/faculty users:

```bash
cd /Users/karthi/2K26/backend
python -m app.utils.init_db
```

4. Train the ML models:

```bash
cd /Users/karthi/2K26/backend
python -c "from app.services.training_service import train_models; train_models(None)"
```

5. Run the API:

```bash
cd /Users/karthi/2K26/backend
uvicorn app.main:app --reload
```

## Frontend Setup

```bash
cd /Users/karthi/2K26/frontend
npm install
cp .env.example .env
npm run dev
```

## Seeded Credentials

- Admin: `admin@retentionai.com` / `Admin@123`
- Faculty: `faculty@retentionai.com` / `Faculty@123`

## Core APIs

- `POST /api/v1/auth/login`
- `GET /api/v1/students`
- `POST /api/v1/students`
- `POST /api/v1/students/upload-csv`
- `POST /api/v1/predict-risk`
- `GET /api/v1/recommendations/{student_id}`
- `GET /api/v1/analytics`
- `POST /api/v1/train-model`

OpenAPI docs are available at [http://localhost:8000/docs](http://localhost:8000/docs).

## AI Flow

1. Training data is loaded from [backend/data/student_retention_dataset.csv](/Users/karthi/2K26/backend/data/student_retention_dataset.csv).
2. Random Forest is used as the primary classifier for retention risk.
3. Logistic Regression is trained in parallel for score comparison.
4. SHAP feature importance is generated at inference time for explainability.
5. Rule-guided academic, career, and adaptive learning recommendations are generated per student.
6. Medium and high risk predictions can trigger automated SMTP alerts.

## Notes

- Configure Gmail SMTP app-password values in [backend/.env.example](/Users/karthi/2K26/backend/.env.example) to enable emails.
- Generated model artifacts are saved into `backend/models/`.
- The sample dataset includes low, medium, and high risk examples for training and CSV import.
