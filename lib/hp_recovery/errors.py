class RecoveryError(RuntimeError):
    code = "STOP"

    def __init__(self, message=""):
        super().__init__(message or self.code)


class ValidationError(RecoveryError):
    code = "STOP_VALIDATION"


class SourceError(RecoveryError):
    code = "STOP_SOURCE"


class SafetyError(RecoveryError):
    code = "STOP_SAFETY"


class StateError(RecoveryError):
    code = "STOP_STATE"


class ConfirmationError(RecoveryError):
    code = "STOP_CONFIRMATION"
