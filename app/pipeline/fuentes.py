"""Nombres canónicos de las 7 Fuentes de arranque del MVP.

Las fuentes se definen en código (F8 · gestión de fuentes queda para después
del MVP), así que el nombre actúa como clave estable entre el seed
(`scripts/seed.py`) y la fábrica de conectores (`app/pipeline/ingesta/factory.py`).
"""

NOMBRE_REDDIT_IDEAS = "Reddit — ideas"
NOMBRE_REDDIT_NEGOCIO = "Reddit — negocio/SaaS"
NOMBRE_HACKERNEWS = "Hacker News — Ask + Show"
NOMBRE_APPLE = "Apple App Store — reseñas"
NOMBRE_GOOGLE_NEWS = "Google News — búsquedas temáticas"
NOMBRE_PRENSA = "Prensa tech (TechCrunch + Xataka)"
NOMBRE_PRODUCT_HUNT = "Product Hunt"
