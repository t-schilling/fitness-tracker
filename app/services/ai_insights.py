import json

import anthropic

from app.config import settings

_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


def _summarize_profile(profile: list[list]) -> str:
    """Reduce elevation profile to ~10 key waypoints for the prompt."""
    if not profile:
        return "Sin datos de elevación."
    n = len(profile)
    step = max(1, n // 10)
    points = profile[::step]
    if profile[-1] not in points:
        points.append(profile[-1])
    return " → ".join(f"{p[0]:.1f}km/{p[1]:.0f}m" for p in points)


async def analyze_gpx_route(
    filename: str,
    dist_km: float,
    gain_m: float,
    loss_m: float,
    max_ele: float | None,
    min_ele: float | None,
    difficulty: str,
    profile: list[list],
) -> str:
    profile_summary = _summarize_profile(profile)

    prompt = f"""Analiza esta ruta de trail running y entrega un análisis práctico y específico.

DATOS DE LA RUTA:
- Archivo: {filename}
- Distancia: {dist_km:.2f} km
- Desnivel positivo (D+): {gain_m:.0f} m
- Desnivel negativo (D-): {loss_m:.0f} m
- Altitud máxima: {f"{max_ele:.0f} m" if max_ele else "N/D"}
- Altitud mínima: {f"{min_ele:.0f} m" if min_ele else "N/D"}
- Dificultad estimada: {difficulty}
- Perfil de elevación (dist/altitud): {profile_summary}

Entrega el análisis en estas secciones exactas con formato markdown:

## Lectura del perfil
Describe en 2-3 oraciones el carácter de la ruta: ¿es una vuelta, ascenso/descenso lineal, ondulada? ¿Dónde están los tramos duros?

## Segmentos clave
Lista los 3-5 tramos más importantes (subidas fuertes, bajadas técnicas, llanos recuperadores) con km aproximado y qué implican para el esfuerzo.

## Estrategia de ritmo
Recomendación concreta: cómo distribuir el esfuerzo, en qué tramos aflojar o apretar, si conviene caminar alguna subida.

## Nutrición e hidratación
Puntos de avituallamiento recomendados por km. Para rutas largas, frecuencia de ingesta de carbohidratos y electrolitos.

## Estimación de tiempo
Rango de tiempo estimado para un corredor de trail competente (no elite). Usa la fórmula de Naismith adaptada a trail: 1h por cada 5km + 1h por cada 500m D+, con un factor de dificultad de terreno de ±20%.

Sé específico y usa los datos reales. No des consejos genéricos."""

    client = _get_client()
    message = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=(
            "Eres un entrenador experto en trail running con amplia experiencia en montaña andina. "
            "Das análisis concretos y accionables. Usas unidades métricas. "
            "El atleta corre habitualmente en los Andes de Chile."
        ),
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text
