# Checklist de mejoras - version aislada 2026-06-11

Objetivo: revisar y reintroducir cambios de forma controlada, con validacion por etapa.

## 1) Carga de imagenes
- [ ] Inventariar tipos de URL de imagen (Cloudinary, api.myl.cl, /media local)
- [ ] Definir estrategia unica por origen (sin dependencia critica de proxy externo)
- [ ] Agregar fallback consistente en todas las vistas con miniaturas
- [ ] Medir tiempo de carga en Deck View, Tienda y Carpeta antes/despues
- [ ] Verificar comportamiento con Service Worker activo y cache limpia

## 2) Calidad visual sin romper performance
- [ ] Revisar reglas globales de titulos y validar que no reaparezcan barras blancas
- [ ] Confirmar consistencia dark/light en vistas Riftbound clave
- [ ] Asegurar que ajustes visuales no alteren flujo de carga de imagenes

## 3) Riftbound sync (backend)
- [ ] Reintroducir integracion riftcodex por feature flag
- [ ] Soportar modo offline por archivo JSON en produccion (PA)
- [ ] Agregar runbook operativo de sync y rollback
- [ ] Definir monitoreo de errores de sincronizacion

## 4) Admin y UX
- [ ] Revalidar menu compartir y accesibilidad con pruebas de teclado
- [ ] Confirmar que tests cubren flujos de error de copiado y cierre del menu

## 5) CI y despliegue
- [ ] Mantener CI frontend/backend en verde antes de cada merge
- [ ] Agregar check de smoke para imagenes en rutas criticas
- [ ] Documentar pasos de deploy para Vercel y PythonAnywhere

## 6) Plan de reintroduccion
- [ ] Reintroducir solo carga de imagenes primero
- [ ] Validar en produccion y recopilar feedback
- [ ] Reintroducir capa visual por bloques pequenos
- [ ] Reintroducir backend Riftbound ops al final
