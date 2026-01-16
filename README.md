# Blood Pressure Monitor
Very simple Blood Pressure Logger.

You input your name, DOB & optional comment. Add 2 readings for both Systolic & Diastolic. It'll automatically log the date & time. At the end of 7 days worth of readings, it'll calculate the totals, excluding day 1.
You can also export the data as a .csv file, either all data, or specified range.

This has no authentication, is not in any way secure. Do NOT expose it to the internet.

This is working perfectly fine for my own usage. Feel free to clone, fork or whatever.

<img width="1980" height="928" alt="image" src="https://github.com/user-attachments/assets/b25ab673-6ec4-44fc-86cb-c4b1abde0b5a" />


Can be run with a simple docker-compose.yml

```
services:
  bp_mon_web:
    image: ghcr.io/psybernoid/bp_monitor
    container_name: bp_mon_web
    restart: unless-stopped
    ports:
      - "5000:5000"
    environment:
      - DATABASE_URL=postgresql://user:password_changeme@bp_mon_db:5432/bp_db # change 'password_changeme' to something secure
    depends_on:
      bp_mon_db:
        condition: service_healthy

  bp_mon_db:
    image: postgres:15
    container_name: bp_mon_db
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d bp_db"]
      interval: 5s
      timeout: 5s
      retries: 5
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password_changeme # change 'password_changeme' to something secure
      - POSTGRES_DB=bp_db
    volumes:
      - ./data:/var/lib/postgresql/data
```
