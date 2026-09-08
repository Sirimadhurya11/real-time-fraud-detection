## Live Demo

[🚀 View Live Fraud Detection Dashboard](https://real-time-fraud-detection-pisn.onrender.com)


# Real-Time Fraud Detection System

A backend-driven real-time fraud detection system built with Python and FastAPI. The system authenticates users, processes financial transactions, evaluates transaction risk, generates fraud alerts, and provides a dashboard for monitoring transaction activity.

## Features

* JWT-based user authentication
* Secure password hashing
* Transaction creation and analysis
* Real-time fraud risk scoring
* LOW, MEDIUM, and HIGH risk classification
* Automatic fraud alerts
* Transaction history
* Fraud-alert monitoring
* Dashboard statistics
* Protected API endpoints
* SQLite database for local development
* Pytest-based testing

## Tech Stack

### Backend

* Python
* FastAPI
* Uvicorn
* Pydantic
* SQLAlchemy
* JWT Authentication
* Passlib

### Database

* SQLite
* SQLAlchemy ORM

### Frontend

* HTML
* CSS
* JavaScript
* Fetch API

### Testing

* Pytest

## Project Structure

```text
real-time-fraud-detection/
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── auth.py
│   ├── database.py
│   ├── fraud_engine.py
│   ├── models.py
│   └── schemas.py
│
├── frontend/
│   ├── login.html
│   └── dashboard.html
│
├── tests/
│
├── .gitignore
├── requirements.txt
└── README.md
```

## How the System Works

```text
User
  │
  ▼
Login
  │
  ▼
JWT Authentication
  │
  ▼
Transaction API
  │
  ▼
Fraud Detection Engine
  │
  ├── Risk Score
  ├── Risk Level
  ├── Fraud Decision
  └── Detection Reasons
  │
  ▼
Database
  │
  ├── Transactions
  └── Fraud Alerts
  │
  ▼
Dashboard
```

## Fraud Detection

Each transaction is analyzed by the fraud detection engine.

The system evaluates transaction characteristics such as:

* Transaction amount
* Transaction location
* Suspicious transaction patterns
* Other configured risk indicators

The engine produces:

```text
Risk Score
Risk Level
Fraud Decision
Fraud Status
Detection Reasons
```

Example:

```json
{
  "message": "Transaction analyzed successfully",
  "transaction_id": "TXN-20260906112724636077",
  "risk_score": 0,
  "risk_level": "LOW",
  "decision": "APPROVE",
  "is_fraud": false,
  "reasons": [
    "No suspicious activity detected"
  ]
}
```

A high-risk transaction can generate a fraud alert:

```json
{
  "risk_score": 80,
  "risk_level": "HIGH",
  "reason": "Very high transaction amount; Transaction originated from a high-risk location"
}
```

## API Endpoints

### Authentication

```text
POST /login
```

Authenticates a user and returns an access token.

### Health Check

```text
GET /health
```

Checks whether the backend is running.

### Transactions

```text
POST /transactions
GET /transactions
GET /transactions/{transaction_id}
```

Creates and retrieves financial transactions.

### Fraud Alerts

```text
GET /fraud-alerts
```

Returns detected fraud alerts.

### Dashboard

```text
GET /dashboard
```

Returns dashboard statistics.

### Frontend

```text
GET /login-page
GET /dashboard-page
```

## Running Locally

### 1. Clone the repository

```bash
git clone https://github.com/Sirimadhurya11/real-time-fraud-detection.git
```

### 2. Enter the project

```bash
cd real-time-fraud-detection
```

### 3. Create a virtual environment

Windows:

```powershell
python -m venv .venv
```

### 4. Activate the environment

```powershell
.venv\Scripts\Activate.ps1
```

### 5. Install dependencies

```powershell
pip install -r requirements.txt
```

### 6. Start the backend

```powershell
uvicorn app.main:app --reload
```

### 7. Open the application

Login:

```text
http://127.0.0.1:8000/login-page
```

API documentation:

```text
http://127.0.0.1:8000/docs
```

## Testing

Run:

```powershell
pytest
```

## Security

Environment variables and local development secrets are excluded from Git using `.gitignore`.

The local virtual environment and database files are also excluded from version control.

## Future Improvements

Possible production improvements include:

* PostgreSQL
* Redis/Kafka event streaming
* Docker
* Kubernetes
* Distributed fraud-analysis workers
* Machine-learning fraud models
* Rate limiting
* Advanced transaction anomaly detection
* Observability and monitoring
* CI/CD pipeline
* Cloud deployment

## Author

Sirimadhurya11

## License

This project is intended for educational and portfolio purposes.
