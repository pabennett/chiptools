import logging
import traceback
import imp
import inspect
import sys
import os

log = logging.getLogger(__name__)


preprocessor_temporary_module = 'chiptools_preprocessor_temporary_module'


def get_preprocessor(path):
    """Import the Python script supplied by the path and return a handle to a
    preprocessor function from the import. It is expected that the file to be
    imported contains a function called 'process' that accepts a list of file
    data and a file path. If these conditions are not met this function will
    return None.
    """
    if preprocessor_temporary_module in sys.modules:
        # Clear the reference to the testPackageModule module
        # TODO: Although unlikely, it is possible that we may delete an
        # existing module from the modules list, is there a more robust way of
        # achieving this functionality?
        del sys.modules[preprocessor_temporary_module]
    if not os.path.exists(path):
        log.error('File not found, aborting preprocessor load: ' + str(path))
        return
    try:
        if sys.version_info < (3, 0, 0):
            # imp.load_source in Python2 will try to use a matching .pyc if 
            # found. We do not want this behavior so delete the .pyc:
            base = os.path.basename(path)
            root = os.path.dirname(path)
            name, ext = os.path.splitext(base)
            pyc_path = os.path.join(root, name + '.pyc')
            if os.path.exists(pyc_path):
                os.remove(pyc_path)
        # We are loading unchecked user code here, the import stage is
        # exception checked.
        imp.load_source(preprocessor_temporary_module, path)
        import chiptools_preprocessor_temporary_module
    except:
        log.error(
            'The module could not be imported due to the ' +
            ' following error:'
        )
        log.error(traceback.format_exc())
        return None
    # Search the module members until a function with the name 'process' is
    # found. If no function can be found return None
    for name, obj in inspect.getmembers(
        chiptools_preprocessor_temporary_module
    ):
        if hasattr(obj, '__name__'):
            if obj.__name__ == 'process' and callable(obj):
                return obj
    return None


class Preprocessor:
    """Preprocessor class to handle file preprocessor execution."""
    def __init__(self):
        super(Preprocessor, self).__init__()

    @classmethod
    def process(cls, path, processor_path):
        """
        Execute the preprocessor on the given file, return True on success
        """
        processor = get_preprocessor(processor_path)
        if processor is None:
            print(processor_path + ' not found ')
            return False
        try:
            data = cls.get_file_data(path)
        except FileNotFoundError:
            log.error('Preprocessor could not open {0}'.format(path))
            return False
        try:
            data = processor(data, path)
        except:
            log.error(
                'The preprocessor caused an exception, ' +
                'no modifications were made'
            )
            log.error(traceback.format_exc())
            return False
        cls.set_file_data(path, data)
        return True

    @classmethod
    def get_file_data(cls, path):
        """Return the file data as a list of lines."""
        try:
            with open(path, 'r') as fileToProcess:
                return fileToProcess.readlines()
        except FileNotFoundError:
            log.error('Preprocessor could not open {0}'.format(path))

    @classmethod
    def set_file_data(cls, path, fileData):
        """Update the file with the new file data."""
        if fileData is None:
            return
        with open(path, 'w') as fileToUpdate:
            for line in fileData:
                fileToUpdate.write(line)
