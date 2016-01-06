from copy import deepcopy
import pickle
import hashlib
import os
import traceback
import logging
import datetime
import time

from chiptools.common import utils

log = logging.getLogger(__name__)


class FileCache:
    """
    A FileCache instance can be used to create and maintain a cache of
    fileObjects so that file changes can be detected to allow intelligent
    recompilation. The FileCache accepts a project file path during creation,
    the cache file will be generated in the same directory as the Project file
    and will use a name derived from the Project file name. File objects can
    be added to the cache and the is_file_changed method can be used to
    determine if a given File object has been modified since it was last added
    to the cache.

    Internally the cache file is stored as a Pickled dictionary of two items:
        * LIBRARIES : A set of libraries that were added to the cache using
        *add_library*
        * FILES : A dictionary of file path / file md5 sum pairs
        of files added using *add_file*
    """
    cache_file_name = '_compilation.cache'
    field_id_files = 'FILES'
    field_id_libraries = 'LIBRARIES'
    blank_cache_element = {
        field_id_libraries: set(),
        field_id_files: {},
    }

    def __init__(self, cache_path):
        """
        Create a FileCache instance using the *projectPath* as the basis for
        the cache file name and root directory.
        """
        super(FileCache, self).__init__()
        self.cache_path = cache_path + self.cache_file_name
        try:
            self.load_cache()
        except IOError:
            self.initialise_cache()

    def load_cache(self):
        """
        Load the cache file pointed to by this FileCache instance. If no cache
        file is present a new one will be created.
        """
        start_time = time.time()
        try:
            # Load the cache file so we know the compilation state of the
            # design
            with open(self.cache_path, 'rb') as pickeFile:
                self.cache = pickle.load(pickeFile)
            log.debug(self.__str__())
        except:
            log.warning('The cache file was corrupted, re-initialising...')
            log.debug(traceback.format_exc())
            self.initialise_cache()
        log.debug(
            'Cache loaded in ' + utils.time_delta_string(
                start_time,
                time.time()
            )
        )

    def initialise_cache(self):
        """
        Initialise the FileCache by generating a new cache file and clearing
        the local cache dictionary.
        """
        log.debug('Clearing cache...')
        # The cache file doesn't exist, so we will create a new one
        self.cache = {}
        self.save_cache()

    def save_cache(self):
        """
        Store the local cache dictionary into the linked cache file so that it
        can be retrieved later.
        """
        log.debug('Saving cache...')
        with open(self.cache_path, 'wb') as cache_file:
            pickle.dump(self.cache, cache_file)
        log.debug('...done')

    def is_file_changed(self, file_object, tool_name):
        """
        Compare the given md5 with the given file path from the cache, if
        the match return True or return False if the hashes do not match or
        the file does not exist.
        """
        path = file_object.path
        if not os.path.exists(path):
            log.error('File does not exist: {0}'.format(path))
            return False

        if tool_name in self.cache:
            cached_md5 = self.cache[tool_name][
                self.field_id_files
            ].get(path, None)
            with open(path, 'rb') as f:
                md5 = hashlib.md5(f.read()).hexdigest()
            if cached_md5 == md5:
                # File is not changed
                return False
            else:
                # File was changed
                return True
            # File is not in cache
            return True
        else:
            return True

    def library_in_cache(self, libname, tool_name):
        """
        Return True if the given *libname* library name is present in the
        local cache dictionary.
        """
        if tool_name in self.cache:
            return libname in self.cache[tool_name][self.field_id_libraries]
        return False

    def get_libraries(self, tool_name):
        """
        Return the local cache dictionary library name set.
        """
        if tool_name in self.cache:
            return self.cache[tool_name].get(self.field_id_libraries, set())
        return set()

    def get_tool_names(self):
        return list(self.cache.keys())

    def add_library(self, library, tool_name):
        """
        Add the given *library* name to the local cache dictionary library
        name set.
        """
        if tool_name not in self.cache:
            self.cache[tool_name] = deepcopy(self.blank_cache_element)
        self.cache[tool_name][self.field_id_libraries].add(library)
        log.debug('Library added to cache: ' + library)

    def add_file(self, fileObject, tool_name):
        """
        Add the given *fileObject* to the local cache file/md5 dictionary. The
        FileObject MD5 and compilation time are updated by this method before
        it is added to the cache.
        """
        if tool_name not in self.cache:
            self.cache[tool_name] = deepcopy(self.blank_cache_element)
        with open(fileObject.path, 'rb') as f:
            md5 = hashlib.md5(f.read()).hexdigest()
        fileObject.compile_time = datetime.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        fileObject.md5 = md5
        self.cache[tool_name][self.field_id_files][fileObject.path] = (
            fileObject.md5
        )
        log.debug(
            'File added to cache: ' +
            os.path.basename(fileObject.path) +
            ' MD5: ' +
            md5
        )

    def remove_file(self, fileObject, tool_name):
        """
        Remove the given *fileObject* from the local cache file/md5 dictionary
        if it is present.
        """
        if tool_name not in self.cache:
            self.cache[tool_name] = deepcopy(self.blank_cache_element)
        if fileObject.path in self.cache[tool_name][self.field_id_files]:
            del self.cache[tool_name][self.field_id_files][fileObject.path]
            log.debug(
                'File removed from cache: ' +
                os.path.basename(fileObject.path)
            )

    def delete(self):
        """
        Delete the cache file pointed to by this FileCache instance.
        """
        if os.path.exists(self.cache_path):
            os.remove(self.cache_path)
