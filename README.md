# fitness-tracker
Thomas personal fitness tracker

## Deploy (Fly.io)

Auto-deploys a `fitness-tracker.fly.dev` en cada push a `main` via GitHub Actions.

### Setup inicial (una sola vez)

1. Crear la app en Fly.io:
   ```
   fly apps create fitness-tracker
   ```

2. Crear el volumen persistente para SQLite:
   ```
   fly volumes create fitness_data --region scl --size 1
   ```

3. Setear secrets:
   ```
   fly secrets set \
     STRAVA_CLIENT_ID=xxx \
     STRAVA_CLIENT_SECRET=xxx \
     STRAVA_ACCESS_TOKEN=xxx \
     STRAVA_REFRESH_TOKEN=xxx \
     ANTHROPIC_API_KEY=xxx \
     SECRET_KEY=xxx
   ```

4. Agregar `FLY_API_TOKEN` como secret en GitHub → Settings → Secrets → Actions.

5. Mergear a `main` — el Action hace el deploy.
