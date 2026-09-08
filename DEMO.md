# Guion de demo · Critical Signal

Duración recomendada: 4–6 minutos.

## Antes de empezar

```bash
docker compose -f "Containers and Deployment with Docker/docker-compose.demo.yml" up --build
```

Abre `http://localhost:4000` en el navegador. Si quieres enseñar el estado de la infraestructura, deja también abiertas `http://localhost:3000` para Grafana y `http://localhost:4000/api/health` para la API.

## Narrativa

### 1. El problema

“En un sistema crítico no basta con guardar una medición. Hay que saber si encaja con el comportamiento esperado, conservar el contexto y poder explicar la decisión.”

Enseña el bloque principal: la interfaz representa una señal y permite enviar un valor sin esconder la respuesta del modelo.

### 2. El flujo normal

Introduce `70` y pulsa `Analizar` cuatro veces: las tres primeras crean la ventana de contexto y la cuarta valida una señal normal.

“La API recibe el valor, lee las tres señales anteriores desde RedisTimeSeries, pide al autoencoder LSTM la reconstrucción de la ventana, calcula el error absoluto, registra el resultado y devuelve un JSON a la interfaz.”

Señala la predicción, el error y el umbral. En las primeras interacciones puede aparecer “Recopilando contexto”; es intencionado: el sistema espera una ventana completa.

### 3. La anomalía

Pulsa `anomalía 445`.

“La señal se aleja claramente de lo que el modelo esperaba. El error supera el umbral aprendido y la UI lo convierte en una alerta visible.”

Abre `/api/measurements` si quieres enseñar que la señal se ha persistido y que la respuesta está separada de la capa visual.

### 4. La arquitectura

Vuelve al README y explica el diagrama:

- Flask sirve la interfaz y la API.
- RedisTimeSeries conserva la serie.
- El modelo `.keras` realiza inferencia.
- Grafana añade observabilidad.
- ZooKeeper coordina varios productores y solo su líder envía la media a `/nuevo`.

### 5. Cierre honesto

“El resultado no se presenta como un producto terminado: es una base técnica que enseña decisiones de modelado, integración, distribución y los límites que todavía habría que resolver para producción.”

Menciona como evolución natural la validación temporal, tests automatizados, seguridad de la API y configuración reproducible de Grafana.
