### Livebox Monitor DHCP Server Logs dialog ###

from datetime import datetime
from dateutil.relativedelta import relativedelta
from enum import IntEnum

from PyQt6 import QtCore, QtWidgets

from LiveboxMonitor.app import LmConfig
from LiveboxMonitor.app.LmTableWidget import LmTableWidget
from LiveboxMonitor.lang.LmLanguages import get_dhcp_logs_label as lx
from LiveboxMonitor.tools import LmTools


# ################################ VARS & DEFS ################################

# List columns
class DhcpLogsCol(IntEnum):
    Key = 0     # Must be the same as DevCol.Key
    Name = 1
    MAC = 2
    Timestamp = 3
    RequestType = 4
    Duration = 5

MONTHS = {
    "January": 1,
    "February": 2,
    "March": 3,
    "April": 4,
    "May": 5,
    "June": 6,
    "July": 7,
    "August": 8,
    "September": 9,
    "October": 10,
    "November": 11,
    "December": 12
}


# ################################ DNS dialog ################################
class DhcpLogsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resize(850, 56 + LmConfig.dialog_height(12))

        # Device table
        self._logs_table = LmTableWidget(objectName="logsTable")
        self._logs_table.set_columns({DhcpLogsCol.Key: ["Key", 0, None],
                                      DhcpLogsCol.Name: [lx("Name"), 300, "logs_Name"],
                                      DhcpLogsCol.MAC: [lx("MAC"), 120, "logs_MAC"],
                                      DhcpLogsCol.Timestamp: [lx("Date/Time"), 150, "logs_Timestamp"],
                                      DhcpLogsCol.RequestType: [lx("Type"), 200, "logs_RequestType"],
                                      DhcpLogsCol.Duration: [lx("Duration"), 80, "logs_Duration"]})
        self._logs_table.set_header_resize([DhcpLogsCol.Name])
        self._logs_table.set_standard_setup(parent, allow_sel=False)

        # Button bar
        hbox = QtWidgets.QHBoxLayout()
        ok_button = QtWidgets.QPushButton(lx("OK"), objectName="ok")
        ok_button.clicked.connect(self.accept)
        ok_button.setDefault(True)
        hbox.addWidget(ok_button, 1, QtCore.Qt.AlignmentFlag.AlignRight)

        vbox = QtWidgets.QVBoxLayout(self)
        vbox.addWidget(self._logs_table, 1)
        vbox.addLayout(hbox, 1)

        LmConfig.set_tooltips(self, "dlogs")

        self.setWindowTitle(lx("DHCP Logs"))
        self.setModal(True)
        self.show()


    ### Load DHCP logs
    def load_dhcp_logs(self, logs):
        if logs is not None:
            self._logs_table.setSortingEnabled(False)
            i = 0
            app = self.parent()
            for l in logs:
                # Display data
                key = l.get("MACADDRESS", "").upper()
                app.add_device_line_key(self._logs_table, i, key)

                app.format_name_widget(self._logs_table, i, key, DhcpLogsCol.Name)

                app.format_mac_widget(self._logs_table, i, key, DhcpLogsCol.MAC)

                timestamp = DhcpLogsDialog.compute_timestamp(l)
                self._logs_table.setItem(i, DhcpLogsCol.Timestamp, QtWidgets.QTableWidgetItem(timestamp))

                request_type = l.get("Type", "").strip()
                self._logs_table.setItem(i, DhcpLogsCol.RequestType, QtWidgets.QTableWidgetItem(request_type))

                duration = str(l.get("Duration(ms)", ""))
                self._logs_table.setItem(i, DhcpLogsCol.Duration, QtWidgets.QTableWidgetItem(duration))

                i += 1

            self._logs_table.sortItems(DhcpLogsCol.Timestamp, QtCore.Qt.SortOrder.DescendingOrder)
            self._logs_table.setSortingEnabled(True)


    ### Compute a log timestamp
    @staticmethod
    def compute_timestamp(log):
        # Get log's timestamp
        timestamp_str = log.get("StartTime", None)

        if timestamp_str:
            parts = timestamp_str.split()

            # Translate date manually as locale might not be set to English
            day = int(parts[0])
            try:
                month = MONTHS[parts[1]]
            except Exception as e:
                LmTools.error(str(e))
                return "Error"
            hour = int(parts[2].split(':')[0])
            minute = int(parts[2].split(':')[1])
            ampm = parts[3].upper()
            if (ampm == 'PM') and (hour < 12):
                hour += 12
            elif (ampm == 'AM') and (hour == 12):
                hour = 0
            if month > datetime.now().month:
                year = datetime.now().year - 1
            else:
                year = datetime.now().year

            return LmTools.fmt_datetime(datetime(year, month, day, hour, minute))

        return ""
