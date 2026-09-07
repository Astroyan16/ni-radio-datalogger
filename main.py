"""Point d'entrée de NI Radio Datalogger."""

from __future__ import annotations

import sys
import argparse
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from radio_datalogger.main_window import MainWindow
from radio_datalogger.styles import APP_STYLESHEET
from radio_datalogger import __version__


def main() -> int:
    parser = argparse.ArgumentParser(description="NI Radio Datalogger")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--smoke-test", type=Path, metavar="DOSSIER",
        help="Vérifier l'application en simulation et écrire un rapport dans DOSSIER.",
    )
    args, qt_args = parser.parse_known_args()
    app = QApplication([sys.argv[0], *qt_args])
    app.setApplicationName("NI Radio Datalogger")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("Observatoire de Paris")
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(APP_STYLESHEET)
    app.setAttribute(Qt.ApplicationAttribute.AA_DontUseNativeMenuBar, True)

    if args.smoke_test is not None:
        from radio_datalogger.smoke_test import run_smoke_test

        return run_smoke_test(app, args.smoke_test)

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
