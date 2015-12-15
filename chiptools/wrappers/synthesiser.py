import os
import logging
import traceback

from chiptools.common import exceptions
from chiptools.core import package_builder
from chiptools.wrappers.toolchains import ToolchainBase

log = logging.getLogger(__name__)


def throws_synthesis_exception(fn):
    """
    A decorator to automatically catch and format synthesis exceptions raised
    by synthesis functions. The decorator will call the given function and log
    simulator specific exceptions before throwing them to the caller.
    """
    from functools import wraps

    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except exceptions.ExecutionError as e:
            raise exceptions.SynthesisException(e)
        except NotADirectoryError as e:
            log.error(traceback.format_exc())
            log.error(
                'The directory {0} could not be found, '.format(
                    args[0].synthesisRoot
                ) +
                'check the synthesis paths in the project and options file.'
            )
            raise exceptions.SynthesisException(e)
        except FileNotFoundError as e:
            log.error(traceback.format_exc())
            log.error(
                'The executable could not be found, check the executable ' +
                'paths in the options file.'
            )
            raise exceptions.SynthesisException(e)
        except:
            raise
    return wrapper


class Synthesiser(ToolchainBase):
    """
    The Synthesiser class provides a base class for all synthesis tool wrapper
    implementations. Common functions used by all synthesis tool wrappers are
    implemented in this class.
    """
    def __init__(self, project, executables, user_paths):
        super(Synthesiser, self).__init__(
            project,
            executables,
            user_paths
        )

    def synthesise(self, library, entity, fpga_part=None):
        """
        Synthesise the target entity in the given library for the currently
        loaded project.
        """
        pass

    def storeOutputs(self, workingDirectory, archiveName):
        """
        Add all files found in the supplied workingDirectory to an archive
        with the name archiveName. A PackageBuilder instance is used to manage
        the creation of the archive file.
        """
        archivePath = os.path.join(workingDirectory, '../', archiveName)
        archive = package_builder.PackageBuilder(archivePath)
        archive.addAll(workingDirectory)
        archive.save()
