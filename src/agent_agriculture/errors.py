"""Safe, actionable error codes without dumping private record contents."""


class PipelineError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)
