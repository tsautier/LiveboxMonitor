### Livebox Monitor AutoDiag APIs ###

from LiveboxMonitor.api.LmApi import LmApi, LmApiException


# ################################ AutoDiag APIs ################################
class AutoDiagApi(LmApi):
    def __init__(self, api_registry):
        super().__init__(api_registry)


    ### List all available diagnostics
    def list_diagnostics(self):
        return self.call_no_check("AutoDiag", "listDiagnostics")


    ### Get state of the latest executed diagnostic
    def get_diagnostic_state(self):
        return self.call("AutoDiag", "getDiagnosticsState")


    ### Execute a diagnostic, first check if one is not already running (only one at a time)
    # Asynchronous execution / interactions can be tracked with events -> "AutoDiag" handler
    def execute_diagnostic(self, id, user_requested=True):
        s = self.get_diagnostic_state()
        state = s.get("DiagnosticsState")
        if state and (state != "Complete"):
            raise LmApiException(f"A diagnostic is already running: {s.get('Diagnostics')}")
        self.call("AutoDiag", "executeDiagnostics", {"id": id, "usr": user_requested})


    ### Answer to a question raised by event
    # In case of a "yes/no" question the input must be in French: "oui/non"
    def set_user_input(self, user_input):
        self.call("AutoDiag", "setUserInput", {"input": user_input})


    ### Get latest speed test results
    # Works only for "speedService" and "visuAtlasSpeedTest" diagnostics
    def get_speed_test_results(self):
        return self.call("SpeedTest", "getWANResults")
