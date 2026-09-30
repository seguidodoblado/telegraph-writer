# Cómo contribuir

Gracias por tu interés en contribuir a este proyecto.

## Desarrollo

Consulta el `README.md` y la [wiki](https://github.com/seguidodoblado/telegraph-writer/wiki) para preparar el
entorno de desarrollo.

## Cambios

Antes de realizar cambios importantes, abre una issue para describir la propuesta y facilitar su discusión.

## Pull Requests

Crea una rama pequeña desde `main`. Comprueba que las pruebas pasan (`python3 -m unittest discover -s tests`), que
la aplicación arranca y que el `.deb` se construye (`./build-deb.sh`). Si cambia el comportamiento visible,
actualiza la wiki.

Los cambios deben mantener la calidad y las convenciones establecidas para el proyecto.

Este proyecto se distribuye bajo licencia [GPL](LICENSE).
