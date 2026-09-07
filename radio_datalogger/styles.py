"""Thème visuel de l'application."""

APP_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #0b1220;
    color: #e5edf8;
}
QFrame#card {
    background-color: #111b2e;
    border: 1px solid #24334d;
    border-radius: 12px;
}
QLabel#title {
    font-size: 24px;
    font-weight: 700;
    color: #f4f8ff;
}
QLabel#subtitle, QLabel#muted {
    color: #91a4bf;
}
QLabel#sectionTitle {
    color: #c4d5eb;
    font-size: 12px;
    font-weight: 700;
}
QLabel#metricValue {
    color: #f4f8ff;
    font-size: 18px;
    font-weight: 700;
}
QLabel#metricCaption {
    color: #7f92ae;
    font-size: 11px;
}
QLabel#statusPill {
    background-color: #17243a;
    color: #9db0c9;
    border: 1px solid #2a3b57;
    border-radius: 10px;
    padding: 5px 10px;
}
QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {
    background-color: #0c1627;
    border: 1px solid #2a3b57;
    border-radius: 7px;
    padding: 7px 9px;
    min-height: 20px;
    selection-background-color: #2f81f7;
}
QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {
    border-color: #47709f;
}
QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #4aa8ff;
}
QComboBox QAbstractItemView {
    background-color: #101b2d;
    color: #e5edf8;
    border: 1px solid #2a3b57;
    selection-background-color: #1f6feb;
}
QPushButton {
    background-color: #18263c;
    color: #dce8f7;
    border: 1px solid #314663;
    border-radius: 8px;
    padding: 8px 13px;
    font-weight: 600;
}
QPushButton:hover { background-color: #20324e; }
QPushButton:pressed { background-color: #142035; }
QPushButton:disabled { color: #5e6e84; background-color: #101827; border-color: #1b283c; }
QPushButton#primaryButton {
    background-color: #1677d2;
    border-color: #2995ef;
    color: white;
}
QPushButton#primaryButton:hover { background-color: #2188df; }
QPushButton#dangerButton {
    background-color: #8f2d3a;
    border-color: #bf4a5a;
    color: white;
}
QPushButton#recordButton:checked {
    background-color: #b42337;
    border-color: #ef5268;
    color: white;
}
QStatusBar {
    background-color: #0a111e;
    color: #8fa2bd;
    border-top: 1px solid #1b2940;
}
QToolTip {
    background-color: #18263c;
    color: #f4f8ff;
    border: 1px solid #3a5273;
}
"""
