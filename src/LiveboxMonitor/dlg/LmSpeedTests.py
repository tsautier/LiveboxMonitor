### Livebox Monitor Speed Tests dialog ###

import json

from enum import IntEnum

from PyQt6 import QtCore, QtWidgets

from LiveboxMonitor.app import LmQtTools, LmConfig
from LiveboxMonitor.app.LmConfig import LmConf
from LiveboxMonitor.lang.LmLanguages import get_speed_tests_label as lx
from LiveboxMonitor.tools import LmTools


# ################################ VARS & DEFS ################################

class TestType(IntEnum):
    Native = 0
    MonReseauLocal = 1


# ################################ DynDNS setup dialog ################################
class SpeedTestsDialog(QtWidgets.QDialog):
    ### Constructor
    def __init__(self, parent):
        super().__init__(parent)
        self.resize(400, 320)

        self._app = parent
        self._api = parent._api
        self._test_type = TestType.Native
        self._wording = ""
        self._results = {}

        # Top bar layout
        top_bar = QtWidgets.QHBoxLayout()
        top_bar.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        top_bar.setSpacing(10)

        # Speed test type option
        type_layout = QtWidgets.QHBoxLayout()
        type_layout.setSpacing(10)
        type_label = QtWidgets.QLabel(lx("Test"), objectName="typeLabel")
        type_layout.addWidget(type_label, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        self._type_combo = QtWidgets.QComboBox(objectName="typeCombo")
        self._type_combo.activated.connect(self.type_selected)
        self._type_combo.addItem(lx("Native"))
        self._type_combo.addItem(lx("mon-reseau-local.orange.fr"))
        type_layout.addWidget(self._type_combo, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        top_bar.addLayout(type_layout)

        # Run test button
        self._run_button = QtWidgets.QPushButton(lx("Run"), objectName="run")
        self._run_button.clicked.connect(self.run_test)
        top_bar.addStretch(1)   # To align the button to the right
        top_bar.addWidget(self._run_button, 0, QtCore.Qt.AlignmentFlag.AlignRight)

        # Results box
        results_group = QtWidgets.QGroupBox(lx("Results"), objectName="resultsGroup")
        results_layout = QtWidgets.QGridLayout(results_group)
        results_layout.setSpacing(15)
        results_layout.setColumnStretch(1, 1)
        results_layout.setColumnStretch(3, 1)

        datetime_label = QtWidgets.QLabel(lx("Date/Time:"), objectName="datetimeLabel")
        self._datetime = QtWidgets.QLabel("-", objectName="datetime")

        downrate_label = QtWidgets.QLabel(lx("Down Rate:"), objectName="downrateLabel")
        self._downrate = QtWidgets.QLabel("-", objectName="downrate")

        downlatency_label = QtWidgets.QLabel(lx("Down Latency:"), objectName="downlatencyLabel")
        self._downlatency = QtWidgets.QLabel("-", objectName="downlatency")

        uprate_label = QtWidgets.QLabel(lx("Up Rate:"), objectName="uprateLabel")
        self._uprate = QtWidgets.QLabel("-", objectName="uprate")

        uplatency_label = QtWidgets.QLabel(lx("Up Latency:"), objectName="uplatencyLabel")
        self._uplatency = QtWidgets.QLabel("-", objectName="uplatency")

        results_layout.addWidget(datetime_label, 0, 0)
        results_layout.addWidget(self._datetime, 0, 1)
        results_layout.addWidget(downrate_label, 1, 0)
        results_layout.addWidget(self._downrate, 1, 1)
        results_layout.addWidget(downlatency_label, 1, 2)
        results_layout.addWidget(self._downlatency, 1, 3)
        results_layout.addWidget(uprate_label, 2, 0)
        results_layout.addWidget(self._uprate, 2, 1)
        results_layout.addWidget(uplatency_label, 2, 2)
        results_layout.addWidget(self._uplatency, 2, 3)

        # Status box
        status_group = QtWidgets.QGroupBox(lx("Status"), objectName="statusGroup")
        status_layout = QtWidgets.QHBoxLayout(status_group)
        self._status = LmQtTools.AutoHeightLabel(objectName="status")
        self._status.setText("")
        status_layout.addWidget(self._status, 1, QtCore.Qt.AlignmentFlag.AlignLeft)

        # Button bar
        ok_button = QtWidgets.QPushButton(lx("OK"), objectName="ok")
        ok_button.clicked.connect(self.accept)
        ok_button.setDefault(True)
        button_bar = QtWidgets.QHBoxLayout()
        button_bar.setSpacing(10)
        button_bar.addWidget(ok_button, 0, QtCore.Qt.AlignmentFlag.AlignRight)

        # Final layout
        vbox = QtWidgets.QVBoxLayout(self)
        vbox.setSpacing(20)
        vbox.addLayout(top_bar, 0)
        vbox.addWidget(results_group, 0)
        vbox.addWidget(status_group, 1)
        vbox.addLayout(button_bar, 0)

        LmConfig.set_tooltips(self, "speedtests")

        self.setWindowTitle(lx("Speed Tests"))
        self.setModal(True)
        self.load_saved_results()
        self.type_selected(TestType.Native)
        self.show()


    ### Test type selected
    def type_selected(self, index):
        self._test_type = index
        self.display_results()


    ### Click on run test button
    # Execution is asynchronous and is tracked via AutoDiag events
    def run_test(self):
        match self._test_type:
            case TestType.Native:
                test_id = "speedService"
            case TestType.MonReseauLocal:
                test_id = "visuServiceLan"
            case _:
                LmTools.error("Invalid test type")
                return

        try:
            self._api._autodiag.execute_diagnostic(test_id)
        except Exception as e:
            self._app.display_error(str(e))
            return

        self._run_button.setEnabled(False)
        self._type_combo.setEnabled(False)


    ### Load saved results from configuration file
    def load_saved_results(self, update_status=True):
        r = LmConf.SpeedTests
        if r:
            if not isinstance(r, dict):
                LmTools.error("Invalid saved speed tests data")
                r = {}
        else:
            r = {}
        self._results = r

        # If no saved result load the latest ones from Livebox
        if not self._results:
            self.load_livebox_results()


    ### Save results in configuration file
    def save_results(self):
        LmConf.SpeedTests = self._results
        LmConf.save()


    ### Load Livebox results
    def load_livebox_results(self):
        try:
            lbr = self._api._autodiag.get_speed_test_results()
        except Exception as e:
            self._app.display_error(str(e))
            return

        if lbr.get("status") != "Completed":
            LmTools.log_debug(1, "No completed speed test results found")
            return

        down = lbr.get("Downstream")
        up = lbr.get("Upstream")
        if not down or not up:
            LmTools.error("Speed test results have unexpected format")
            return

        r = {
            "Timestamp": LmTools.fmt_livebox_timestamp(down.get("start")),
            "downrate": int(int(down.get("rate", 0)) / 1000),
            "downlatency": int(down.get("latency", 0)),
            "uprate": int(int(up.get("rate", 0)) / 1000),
            "uplatency": int(up.get("latency", 0)),
            "wording": self._wording
        }

        self._results[self._test_type] = r


    ### Display results
    def display_results(self, status=""):
        r = self._results.get(self._test_type)

        if not r:
            self.reset_results()
            return

        self._datetime.setText(r.get("Timestamp"))

        font = self._downrate.font()
        font.setBold(True)
        self._downrate.setText(f"{r.get('downrate', 0)} Mbps")
        self._downrate.setFont(font)
        self._downlatency.setText(f"{r.get('downlatency', 0)} ms")
        self._downlatency.setFont(font)
        self._uprate.setText(f"{r.get('uprate', 0)} Mbps")
        self._uprate.setFont(font)
        self._uplatency.setText(f"{r.get('uplatency', 0)} ms")
        self._uplatency.setFont(font)

        if status:
            self._status.setText(f"{status}\n{r.get('wording', '')}")
        else:
            self._status.setText(r.get("wording", ""))


    ### Reset displayed results
    def reset_results(self, status=""):
        self._datetime.setText("-")

        font = self._downrate.font()
        font.setBold(False)
        self._downrate.setText("-")
        self._downrate.setFont(font)

        self._downlatency.setText("-")
        self._downlatency.setFont(font)

        self._uprate.setText("-")
        self._uprate.setFont(font)

        self._uplatency.setText("-")
        self._uplatency.setFont(font)

        self._status.setText(status)


    ### Actions when a test is starting
    def test_start(self):
        self._run_button.setEnabled(False)
        self._type_combo.setEnabled(False)
        self.reset_results(lx("Speed test in progress..."))
        self._wording = ""


    ### Actions when a test is done
    def test_done(self):
        self.load_livebox_results()
        self.display_results(lx("Done."))
        self.save_results()
        self._run_button.setEnabled(True)
        self._type_combo.setEnabled(True)


    ### Autodiag event received
    def process_auto_diag_event(self, event):
        reason = event.get("reason")
        match reason:
            case "UI":  # Raised by both native and MRL tests
                attributes = event.get("attributes")
                if attributes:
                    status = attributes.get("exec")
                    match status:
                        case "start":
                            self.test_start()
                        case "done":
                            self.test_done()
                        case _:
                            self._status.setText(lx(f"{str(status).capitalize()}."))

            case "Event":   # Raised only by MRL test to give results (before "done" event)
                if self._test_type == TestType.MonReseauLocal:
                    attributes = event.get("attributes")
                    if attributes:
                        report = attributes.get("ADReport")
                        mrl_results = self.parse_adr_report(report)
                        self._wording = mrl_results.get("wording", "")
        return


    ### Convert MRL results given in ADRReport string into valid dict
    @staticmethod
    def parse_adr_report(report):
        try:
            c = json.loads(report)
        except Exception as e:
            LmTools.error(f"Error while parsing MRL test ADReport: {str(e)}")
            return None

        wording = c.get("wording")
        if wording:
            c["wording"] = wording.strip()
        else:
            LmTools.error("No wording in MRL test ADRReport")

        return c
