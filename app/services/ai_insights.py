from google import genai

from app.config import settings

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY no está configurado")
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


_SYSTEM = (
    "Eres un entrenador experto en trail running con amplia experiencia en montaña andina. "
    "Das análisis concretos y accionables. Usas unidades métricas. "
    "El atleta corre habitualmente en los Andes de Chile."
)

_MODEL = "gemini-2.0-flash"


def _summarize_profile(profile: list[list]) -> str:
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
    client = _get_client()
    prompt = f"""{_SYSTEM}

Analiza esta ruta de trail running y entrega un análisis práctico y específico.

DATOS DE LA RUTA:
- Archivo: {filename}
- Distancia: {dist_km:.2f} km
- Desnivel positivo (D+): {gain_m:.0f} m
- Desnivel negativo (D-): {loss_m:.0f} m
- Altitud máxima: {f"{max_ele:.0f} m" if max_ele else "N/D"}
- Altitud mínima: {f"{min_ele:.0f} m" if min_ele else "N/D"}
- Dificultad estimada: {difficulty}
- Perfil de elevación (dist/altitud): {_summarize_profile(profile)}

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

    response = await client.aio.models.generate_content(
        model=_MODEL,
        contents=prompt,
    )
    return response.text
