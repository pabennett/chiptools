class SimulatorException(Exception):
    pass


class CompilationException(SimulatorException):
    pass


class ExecutionError(Exception):
    pass


class ProjectFileException(Exception):
    pass


class SynthesisException(Exception):
    pass
