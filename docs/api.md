# API Summary

## Authentication

- `POST /api/v1/auth/login`

## Students

- `GET /api/v1/students`
- `POST /api/v1/students`
- `GET /api/v1/students/{student_id}`
- `PUT /api/v1/students/{student_id}`
- `DELETE /api/v1/students/{student_id}`
- `POST /api/v1/students/upload-csv`
- `GET /api/v1/students/{student_id}/predictions`

## AI / Analytics

- `POST /api/v1/predict-risk`
- `GET /api/v1/analytics`
- `GET /api/v1/recommendations/{student_id}`
- `POST /api/v1/train-model`

## Email Automation

- Medium and high risk predictions automatically attempt SMTP delivery to the student.
- SMTP settings are read from environment variables.
