"""Telegraph Writer: cliente de escritorio GTK 4 para Telegra.ph."""
import os as _os

__version__ = "2.7.2"


def _fix_input_method() -> None:
    # IBus 1.5.29 con GTK4 no confirma la tecla muerta (tilde flotando). El método
    # integrado de GTK compone bien las teclas muertas. Debe fijarse antes de que
    # GTK arranque, por eso se ejecuta al importar el paquete.
    if _os.environ.get("GTK_IM_MODULE") == "ibus":
        _os.environ["GTK_IM_MODULE"] = "simple"


_fix_input_method()
