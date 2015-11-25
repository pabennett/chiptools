import os
import glob
import tarfile
import logging

log = logging.getLogger(__name__)


class PackageBuilder:
    def __init__(self, path):
        self.archive = tarfile.TarFile(name=path, mode='a')

    def addAll(self, path, pattern='*'):
        """Add all items from path that match pattern"""
        currentDir = os.getcwd()
        if os.path.exists(path):
            # Set CWD to the path
            os.chdir(path)
            for item in glob.glob(pattern):
                self.archive.add(item)
                log.info('Added: ' + str(item))
            # Restore the CWD
            os.chdir(currentDir)
        else:
            log.error('Not a valid path: ' + str(path))

    def save(self):
        self.archive.close()
