import os
import tempfile

# Las pruebas nunca tocan los datos reales (el config.json con el access token y los borradores de ~/Telegra.ph):
# antes de importar nada del paquete, que fija sus rutas al importarse, HOME apunta a una carpeta temporal.
# También se fija el idioma, para que los textos sean los del idioma fuente (español) vengan los .mo o no.
os.environ["HOME"] = tempfile.mkdtemp(prefix="telegraph-writer-tests-")
os.environ["LANGUAGE"] = "es"
