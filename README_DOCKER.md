Docker instructions

Build the Docker image:

```bash
docker build -t virtual-hire-coach:latest .
```

Run with Docker:

```bash
docker run -it --rm -p 5000:5000 -v "$(pwd)/uploads:/app/uploads" \
  -e SECRET_KEY=supersecret virtual-hire-coach:latest
```

Or use docker-compose:

```bash
docker compose up --build
```

Notes:
- The app exposes port 5000. Mount `./uploads` to persist uploaded files.
- For production, set a secure `SECRET_KEY` via env or Docker secrets.
- The image uses Gunicorn as the WSGI server.
