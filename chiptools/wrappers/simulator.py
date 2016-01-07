import logging
import os
import time

from chiptools.common import exceptions
from chiptools.common import utils
from chiptools.wrappers.toolchains import ToolchainBase

log = logging.getLogger(__name__)


class Simulator(ToolchainBase):
    """
    The Simulator class provides a base class for all simulator tool wrapper
    implementations.
    Common functions used by all simulator tool wrappers are implemented in
    this class.
    """
    def __init__(self, project, executables, user_paths):
        super(Simulator, self).__init__(
            project,
            executables,
            user_paths
        )
        self.libraries = {}

    def compile(self, file_object):
        """
        Compile the supplied *file_object* into the current working library.
        """
        raise NotImplementedError

    def simulate(self, library, entity, **kwargs):
        """
        Invoke the simulator and target the given *entity* in the given
        *library*.
        If the optional argument *gui* is set to False the simulator will
        execute as a console application (where supported) otherwise it will
        run as a GUI. This function is blocking and will only continue when
        the simulator terminates.
        The optional argument *generics* provides a dictionary of *generic
        name*/*generic value* key, value pairs that are passed to the
        simulator as a command line argument. This allows you to set generics
        present on the entity being simulated.
        The optional argument *do* can be used to supply a string argument to
        be interpreted by the simulator as a script to execute after loading.

        """
        raise NotImplementedError

    def set_working_library(self, library, cwd=None):
        """
        Set the current working library where source files are to be compiled
        to when using the 'compile' method.
        """
        raise NotImplementedError

    def add_library(self, library):
        """
        Create a new source file library for compiling design files into.
        For example on ModelSim this would invoke the *vlib* command with the
        supplied *library* name.
        """
        raise NotImplementedError

    def library_exists(self, libname, workdir):
        """
        Return True if the given libname exists in the workdir.
        """
        lib_path = os.path.join(workdir, libname)
        return os.path.isdir(lib_path)

    def compile_project(self, includes={}):
        self.libraries.update(includes)
        for libname, path in includes.items():
            self.set_library_path(libname, path)
        # Load the cache
        cache = self.project.cache
        # Compile the project
        try:
            cwd = self.project.get_simulation_directory()
            # Placeholder arguments
            force = False
            # Compile each of the sources in the project file
            created_libraries = []
            skipped = 0
            count = 0
            start_time = time.time()
            file_object = None
            try:
                for file_object in self.project.get_files():
                    libname = file_object.library
                    count += 1
                    # Check the md5sum of this file and compare it to the
                    # md5sum cache to see if it has changed since it was
                    # last compiled
                    if os.path.isfile(file_object.path):
                        if (
                            not force and
                            not cache.is_file_changed(file_object, self.name)
                        ):
                            # The hashes match. If the library already exists
                            # then dont compile the file.
                            if self.library_exists(libname, cwd):
                                if libname not in created_libraries:
                                    skipped += 1
                                    log.info(
                                        "...skipping: " + file_object.path
                                    )
                                    continue
                        cache.add_file(file_object, self.name)
                        # Map or create the library, track which libraries
                        # were already created
                        if (
                            not cache.library_in_cache(libname, self.name) or
                            not self.library_exists(libname, cwd)
                        ):
                            # If this library is in the cache file someone must
                            # have deleted it since the last run, we need to
                            # recompile all files that are targeted at this
                            # library.
                            created_libraries.append(libname)
                            log.info("...adding library: " + libname)
                            self.add_library(libname)
                            cache.add_library(libname.lower(), self.name)
                        # Map the library to work so files can be added
                        self.set_working_library(libname, cwd=cwd)
                        log.info(
                            '...compiling {0} ({1}) into library {2}'.format(
                                os.path.basename(file_object.path),
                                file_object.fileType,
                                libname)
                        )
                        # Compile the source
                        self.compile(file_object, cwd=cwd)
                    else:
                        raise FileNotFoundError(
                            'File could not be found: ' +
                            '{0}, operation aborted.'.format(
                                file_object.path
                            )
                        )
            except:
                # Clear the SHA1 for the file that failed so it will recompile
                # next time
                if file_object is not None:
                    cache.remove_file(file_object, self.name)
                cache.save_cache()
                raise
            if skipped > 0:
                log.info(
                    '...skipped ' + str(skipped) +
                    ' unmodified file(s). Use \"clean\" to erase' +
                    ' the file cache'
                )
            log.info("...saving cache file")
            # Save the cache file
            cache.save_cache()
            log.info("...done")
            log.info(
                str(count) +
                ' file(s) processed in ' +
                utils.time_delta_string(start_time, time.time())
            )
        except exceptions.ProjectFileException:
            log.error('Compilation aborted due to error in project file.')
            return
