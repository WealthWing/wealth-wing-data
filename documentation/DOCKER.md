## Docker setup

- Create a `docker-compose.yaml` file in the root directory of your project.
- Copy and paste the following code snippet. Feel free to make modifications.

```
version: '3.8'
services:
  postgres:
    image: postgres:latest
    container_name: local_postgres
    environment:
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: 123123
      POSTGRES_DB: test_db2
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

- Run or update Docker services `docker-compose up -d`
- Verify the container is running `docker ps`
- Update your database url in your .env file `DATABASE_URL = postgresql://ed:123123@postgres:5432/test_db2`