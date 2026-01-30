FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py migrate
RUN python manage.py loaddata api/fixtures/test_data.json
RUN python manage.py setup_oauth

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
