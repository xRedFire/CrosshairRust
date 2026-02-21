import sys
import json
import threading
from pynput import keyboard

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton,
    QSlider, QColorDialog, QFrame, QCheckBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QColor


CONFIG_FILE = "config.json"


def load_config():
    default = {
        "size": 6,
        "gap": 2,
        "thickness": 1,
        "color": [255, 0, 0],
        "center_dot": False
    }

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        for k in default:
            if k not in data:
                data[k] = default[k]

        return data
    except:
        return default


def save_config(overlay):
    data = {
        "size": int(overlay.size),
        "gap": int(overlay.gap),
        "thickness": int(overlay.thickness),
        "color": [overlay.color.red(), overlay.color.green(), overlay.color.blue()],
        "center_dot": bool(overlay.center_dot)
    }

    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except:
        pass


class CrosshairOverlay(QWidget):
    def __init__(self, config):
        super().__init__()

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

        # IMPORTANT: never take focus (prevents mouse showing in fullscreen)
        self.setFocusPolicy(Qt.NoFocus)
        self.setWindowFlag(Qt.WindowDoesNotAcceptFocus, True)

        self.showFullScreen()

        self.size = config["size"]
        self.gap = config["gap"]
        self.thickness = config["thickness"]
        self.color = QColor(*config["color"])
        self.center_dot = config["center_dot"]

    def paintEvent(self, event):
        painter = QPainter(self)
        pen = QPen(self.color)
        pen.setWidth(self.thickness)
        painter.setPen(pen)

        cx = self.width() // 2
        cy = self.height() // 2

        painter.drawLine(cx - self.gap - self.size, cy, cx - self.gap, cy)
        painter.drawLine(cx + self.gap, cy, cx + self.gap + self.size, cy)
        painter.drawLine(cx, cy - self.gap - self.size, cx, cy - self.gap)
        painter.drawLine(cx, cy + self.gap, cx, cy + self.gap + self.size)

        if self.center_dot:
            painter.drawPoint(cx, cy)


class CrosshairPreview(QWidget):
    def __init__(self, overlay: CrosshairOverlay):
        super().__init__()
        self.overlay = overlay

        self.setFixedSize(190, 190)
        self.setStyleSheet("""
            background-color: rgb(0, 0, 0);
            border: 1px solid rgba(255, 255, 255, 18);
            border-radius: 14px;
        """)

    def paintEvent(self, event):
        painter = QPainter(self)

        pen = QPen(self.overlay.color)
        pen.setWidth(self.overlay.thickness)
        painter.setPen(pen)

        cx = self.width() // 2
        cy = self.height() // 2

        painter.drawLine(cx - self.overlay.gap - self.overlay.size, cy, cx - self.overlay.gap, cy)
        painter.drawLine(cx + self.overlay.gap, cy, cx + self.overlay.gap + self.overlay.size, cy)
        painter.drawLine(cx, cy - self.overlay.gap - self.overlay.size, cx, cy - self.overlay.gap)
        painter.drawLine(cx, cy + self.overlay.gap, cx, cy + self.overlay.gap + self.overlay.size)

        if self.overlay.center_dot:
            painter.drawPoint(cx, cy)


class SettingsMenu(QWidget):
    toggle_requested = pyqtSignal()

    def __init__(self, overlay: CrosshairOverlay):
        super().__init__()
        self.overlay = overlay

        # Frameless / borderless
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(360, 700)

        self._drag_pos = None

        self.setStyleSheet("""
            QWidget {
                background-color: transparent;
                color: rgb(235, 235, 235);
                font-family: Segoe UI;
                font-size: 13px;
            }

            QLabel {
                color: rgb(235, 235, 235);
            }

            QSlider::groove:horizontal {
                height: 6px;
                background: rgba(255, 255, 255, 20);
                border-radius: 3px;
            }

            QSlider::handle:horizontal {
                width: 18px;
                margin: -7px 0;
                border-radius: 9px;
                background: rgba(255, 255, 255, 170);
            }

            QPushButton {
                background-color: rgb(22, 22, 22);
                border: 1px solid rgba(255, 255, 255, 16);
                padding: 11px;
                border-radius: 14px;
                font-size: 14px;
                color: rgb(240, 240, 240);
            }

            QPushButton:hover {
                background-color: rgb(28, 28, 28);
            }

            QPushButton:pressed {
                background-color: rgb(35, 35, 35);
            }

            QCheckBox {
                color: rgb(245, 245, 245);
            }

            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
        """)

        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.container = QWidget()
        self.container.setObjectName("container")
        self.container.setStyleSheet("""
            QWidget#container {
                background-color: rgb(12, 12, 12);
                border-radius: 18px;
                border: 1px solid rgba(255, 255, 255, 12);
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("🎯 Crosshair Settings")
        title.setStyleSheet("font-size: 20px; font-weight: 900;")
        layout.addWidget(title)

        subtitle = QLabel("Live preview + auto-save config.json")
        subtitle.setStyleSheet("color: rgba(255,255,255,120); font-size: 12px;")
        layout.addWidget(subtitle)

        self.preview = CrosshairPreview(self.overlay)
        layout.addWidget(self.preview, alignment=Qt.AlignCenter)

        layout.addWidget(self._line())

        # SIZE
        self.size_label = QLabel(f"Size: {self.overlay.size}")
        self.size_label.setStyleSheet("font-size: 14px; font-weight: 800;")
        layout.addWidget(self.size_label)

        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setMinimum(1)
        self.size_slider.setMaximum(40)
        self.size_slider.setValue(self.overlay.size)
        self.size_slider.valueChanged.connect(self.set_size)
        layout.addWidget(self.size_slider)

        # GAP
        self.gap_label = QLabel(f"Gap: {self.overlay.gap}")
        self.gap_label.setStyleSheet("font-size: 14px; font-weight: 800;")
        layout.addWidget(self.gap_label)

        self.gap_slider = QSlider(Qt.Horizontal)
        self.gap_slider.setMinimum(0)
        self.gap_slider.setMaximum(30)
        self.gap_slider.setValue(self.overlay.gap)
        self.gap_slider.valueChanged.connect(self.set_gap)
        layout.addWidget(self.gap_slider)

        # THICKNESS
        self.thick_label = QLabel(f"Thickness: {self.overlay.thickness}")
        self.thick_label.setStyleSheet("font-size: 14px; font-weight: 800;")
        layout.addWidget(self.thick_label)

        self.thick_slider = QSlider(Qt.Horizontal)
        self.thick_slider.setMinimum(1)
        self.thick_slider.setMaximum(12)
        self.thick_slider.setValue(self.overlay.thickness)
        self.thick_slider.valueChanged.connect(self.set_thickness)
        layout.addWidget(self.thick_slider)

        # CENTER DOT
        self.dot_checkbox = QCheckBox("Enable center dot")
        self.dot_checkbox.setChecked(self.overlay.center_dot)
        self.dot_checkbox.stateChanged.connect(self.set_center_dot)
        self.dot_checkbox.setStyleSheet("font-size: 16px; font-weight: 900; padding: 8px;")
        layout.addWidget(self.dot_checkbox, alignment=Qt.AlignCenter)

        layout.addWidget(self._line())

        # COLOR
        self.color_btn = QPushButton("🎨 Change color")
        self.color_btn.clicked.connect(self.pick_color)
        layout.addWidget(self.color_btn)

        # RESET
        self.reset_btn = QPushButton("🔁 Reset to defaults")
        self.reset_btn.clicked.connect(self.reset_defaults)
        layout.addWidget(self.reset_btn)

        layout.addWidget(self._line())

        # EXIT
        self.kill_btn = QPushButton("❌ EXIT (close everything)")
        self.kill_btn.setStyleSheet("""
            QPushButton {
                background-color: rgb(35, 12, 12);
                border: 1px solid rgba(255, 80, 80, 35);
                font-weight: 900;
            }
            QPushButton:hover {
                background-color: rgb(45, 15, 15);
            }
        """)
        self.kill_btn.clicked.connect(QApplication.quit)
        layout.addWidget(self.kill_btn)

        info = QLabel("Hotkey: Ctrl + Shift + Alt + X (toggle menu)")
        info.setStyleSheet("color: rgba(255,255,255,110); font-size: 12px; margin-top: 6px;")
        layout.addWidget(info, alignment=Qt.AlignCenter)

        self.container.setLayout(layout)
        outer.addWidget(self.container)
        self.setLayout(outer)

    def _line(self):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("color: rgba(255,255,255,25);")
        return line

    # Dragging (since no title bar)
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def refresh(self):
        self.overlay.update()
        self.preview.update()
        save_config(self.overlay)

    def set_size(self, v):
        self.overlay.size = v
        self.size_label.setText(f"Size: {v}")
        self.refresh()

    def set_gap(self, v):
        self.overlay.gap = v
        self.gap_label.setText(f"Gap: {v}")
        self.refresh()

    def set_thickness(self, v):
        self.overlay.thickness = v
        self.thick_label.setText(f"Thickness: {v}")
        self.refresh()

    def set_center_dot(self, state):
        self.overlay.center_dot = (state == Qt.Checked)
        self.refresh()

    def pick_color(self):
        c = QColorDialog.getColor(self.overlay.color, self, "Choose a color")
        if c.isValid():
            self.overlay.color = c
            self.refresh()

    def reset_defaults(self):
        self.overlay.size = 6
        self.overlay.gap = 2
        self.overlay.thickness = 1
        self.overlay.color = QColor(255, 0, 0)
        self.overlay.center_dot = False

        self.size_slider.setValue(self.overlay.size)
        self.gap_slider.setValue(self.overlay.gap)
        self.thick_slider.setValue(self.overlay.thickness)
        self.dot_checkbox.setChecked(self.overlay.center_dot)

        self.refresh()


def main():
    config = load_config()

    app = QApplication(sys.argv)

    overlay = CrosshairOverlay(config)
    menu = SettingsMenu(overlay)
    menu.hide()

    def toggle_menu():
        if menu.isVisible():
            menu.hide()
        else:
            menu.show()
            menu.raise_()
            # DO NOT activateWindow() -> breaks fullscreen mouse lock
            # menu.activateWindow()

    menu.toggle_requested.connect(toggle_menu)

    def hotkey_thread():
        combo = "<ctrl>+<shift>+<alt>+x"
        with keyboard.GlobalHotKeys({combo: lambda: menu.toggle_requested.emit()}) as h:
            h.join()

    threading.Thread(target=hotkey_thread, daemon=True).start()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
