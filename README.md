# Rastreador de Oportunidades

Herramienta personal que rastrea a diario un conjunto de fuentes externas, detecta oportunidades de negocio/desarrollo (explícitas e inferidas), las puntúa según calidad y encaje con el usuario, y las presenta en un feed para revisarlas, guardarlas o descartarlas.

El diseño completo (descubrimiento, funcional, modelo de datos, arquitectura, UX/UI, MVP y roadmap) vive en los documentos `01`–`07` y en `00-decisiones.md` / `00-parking.md` (aportados por Gabriel, no versionados en este repo).

## Estado

En construcción, siguiendo el plan de implementación del MVP (H1: F1–F6) fase a fase.

## Desarrollo

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # y rellena ANTHROPIC_API_KEY cuando llegue la Fase 5

pytest                  # tests
python -m scripts.seed  # crea el Perfil inicial y las 7 Fuentes de arranque
```
