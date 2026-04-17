# Fitness Tracker — Project Instructions

## Stack
- FastAPI + Jinja2 templates + SQLite (aiosqlite)
- Tailwind CSS via CDN (no build step)
- Chart.js + HTMX + Leaflet.js
- Hosted on Fly.io

## Data Sources (by priority)
1. **Huawei Health** — fuente de verdad (GT2 → Huawei Health → Strava)
2. **Strava** — enriquecimiento GPS (polyline, segmentos)
3. **Jefit** — entrenamientos de fuerza/gym

## Design Context

### Users
Thomas — trail runner personal en Chile, entrena en los Andes. Usa la app en desktop post-entrenamiento o para planificar carreras. Quiere datos rápidos y accionables.

### Brand Personality
**Limpio, atlético, moderno.** Como Strava pero personal y sin ruido social. Datos son los protagonistas.

### Aesthetic Direction
- Dark mode (fondo `oklch(0.12 0.008 55)`, no negro puro)
- Acento naranja/ámbar: `oklch(0.72 0.17 55)`
- Tipografía: Barlow Semi Condensed (headings/números) + Manrope (UI/cuerpo)
- Referencia visual: Strava — jerarquía fuerte, espaciado generoso, limpio

### Design Principles
1. Datos primero — números grandes son protagonistas
2. Espaciado con propósito — densidad controlada, no abigarrado
3. Acento con significado — naranja solo para acciones/estados activos
4. Sin ruido visual — nada de gradientes decorativos, glassmorphism, sombras pesadas
5. Consistencia atlética — misma fuente, escala y grid en todas las páginas

### Anti-patterns (nunca usar)
- `border-left` coloreado como acento en cards
- Gradient text
- Glassmorphism
- Cards dentro de cards
- Sombras decorativas pesadas
