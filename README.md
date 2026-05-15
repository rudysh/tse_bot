# TSE Bot

Bot de consola para consultar cédulas en el sitio del TSE y escribir los resultados en el mismo archivo Excel.

## Uso

1. Coloca un único archivo `.xlsx` dentro de `uploads/`.
2. Instala dependencias:

```powershell
py -m pip install -r requirements.txt
```

3. Ejecuta:

```powershell
py main.py
```

El bot actualizará el mismo Excel agregando:

- Columna B: Nombre completo
- Columna C: Estado
- Columna D: Fecha y hora de consulta

Los logs se guardan en `logs/bot_tse.log`.
