import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QComboBox, QMessageBox
)
from PyQt5.QtCore import QTimer, QThread, pyqtSignal
import pyqtgraph as pg
import serial
import serial.tools.list_ports
import struct

class SerialThread(QThread):
    data_received = pyqtSignal(float)

    def __init__(self, port_name):
        super().__init__()
        self.port_name = port_name
        self.is_running = True

    def run(self):
        try:
            self.serial_port = serial.Serial(self.port_name, baudrate=9600, timeout=1)
            while self.is_running:
                if self.serial_port.in_waiting > 0:
                    data = self.serial_port.readline().decode('utf-8')
                    data = data.strip('\r\n')

                    data = float(data)
                    self.data_received.emit(data)
                    
                        
        except Exception as e:
            print(f"Error en el hilo serial: {e}")

    def stop(self):
        self.is_running = False
        self.serial_port.close()
        self.quit()

class PIDControllerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PID Controller GUI")
        self.setGeometry(100, 100, 800, 600)
        self.serial_thread = None
        self.series_x = []
        self.series_y = []
        self.time = 0

        self.init_ui()
        self.update_ports()

    def init_ui(self):
        # Layout principal
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Panel de control
        control_panel = QHBoxLayout()
        layout.addLayout(control_panel)

        self.kp_field = self.add_input_field(control_panel, "Kp:", "7.12")
        self.ki_field = self.add_input_field(control_panel, "Ki:", "0.016")
        self.kd_field = self.add_input_field(control_panel, "Kd:", "25")
        self.setpoint_field = self.add_input_field(control_panel, "Setpoint:", "24")

        self.port_list = QComboBox()
        control_panel.addWidget(QLabel("Puertos COM:"))
        control_panel.addWidget(self.port_list)

        self.refresh_button = QPushButton("Refrescar")
        self.refresh_button.clicked.connect(self.update_ports)
        control_panel.addWidget(self.refresh_button)

        self.connect_button = QPushButton("Conectar")
        self.connect_button.clicked.connect(self.connect_to_port)
        control_panel.addWidget(self.connect_button)

        self.send_button = QPushButton("Enviar")
        self.send_button.setEnabled(False)
        self.send_button.clicked.connect(self.send_pid_values)
        control_panel.addWidget(self.send_button)

        # Gráfica
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setTitle("Distancia Sensor")
        self.plot_widget.setLabel("left", "Distancia (cm)")
        self.plot_widget.setLabel("bottom", "Tiempo")
        self.curve = self.plot_widget.plot(pen="b")
        layout.addWidget(self.plot_widget)

    def add_input_field(self, layout, label, default_value):
        field = QLineEdit()
        field.setText(default_value)
        layout.addWidget(QLabel(label))
        layout.addWidget(field)
        return field

    def update_ports(self):
        ports = serial.tools.list_ports.comports()
        self.port_list.clear()
        self.port_list.addItems([port.device for port in ports])

    def connect_to_port(self):
        port_name = self.port_list.currentText()
        if port_name:
            try:
                self.serial_thread = SerialThread(port_name)
                self.serial_thread.data_received.connect(self.on_data_received)
                self.serial_thread.start()
                self.send_button.setEnabled(True)
                self.connect_button.setEnabled(False)
                QMessageBox.information(self, "Conexión", f"Conectado al puerto: {port_name}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo conectar al puerto: {e}")

    def send_pid_values(self):
        try:
            kp = float(self.kp_field.text())
            ki = float(self.ki_field.text())
            kd = float(self.kd_field.text())
            setpoint = float(self.setpoint_field.text())

            packed_data = struct.pack('ffff', kp, ki, kd, setpoint)
            self.serial_thread.serial_port.write(packed_data)
        except ValueError:
            QMessageBox.critical(self, "Error", "Ingresa valores válidos.")

    def on_data_received(self, value):
        self.series_x.append(self.time)
        self.series_y.append(value)
        self.time += 1
        self.update_plot()

    def update_plot(self):
        self.curve.setData(self.series_x, self.series_y)

    def closeEvent(self, event):
        if self.serial_thread:
            self.serial_thread.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PIDControllerGUI()
    window.show()
    sys.exit(app.exec_())
