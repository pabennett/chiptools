import os
import re
import sys
import logging
from chiptools.common import utils
import xml

log = logging.getLogger(__name__)

filetypes = [
    'Unknown',
    'VHDL',             # VHDL
    'Verilog',          # Verilog
    'SystemVerilog',    # Verilog (SV)
    'NGCNetlist',       # Netlist
    'TCL',              # TCL
    'UCF',              # Universal constraints format
    'SDC',              # Synopsis design constraints
    'Python',
    'VivadoIp',
    'VivadoXDC',
]

try:
    from enum import Enum
    FileType = Enum('FileType', ' '.join(f for f in filetypes))
except ImportError:
    # Enum module not supported, roll our own.
    def enum(*sequence, **names):
        enums = dict(zip(sequence, range(len(sequence))), **names)
        return type('Enum', (), enums)
    FileType = enum(*filetypes)

# Mapping of file extensions to FileType objects
fileExtensionsLookup = {
    # Common VHDL source extensions
    '.vhd': FileType.VHDL,
    '.vhdl': FileType.VHDL,
    # Common Verilog source extentions
    '.v': FileType.Verilog,
    '.vl': FileType.Verilog,
    '.sv': FileType.SystemVerilog,
    # Netlist Extensions
    '.ngc': FileType.NGCNetlist,
    # Constraint/Script Extensions
    '.tcl': FileType.TCL,
    '.sdc': FileType.SDC,
    # Python
    '.py': FileType.Python,
    # Vivado/ISE Extentions
    '.xci': FileType.VivadoIp,
    '.xco': FileType.VivadoIp,
    '.xdc': FileType.VivadoXDC,
    '.ucf': FileType.UCF,
}


class ProjectAttributes:
    # XML nodes identify opening tags that can be used in the file
    XML_NODE_PROJECT = 'project'
    XML_NODE_LIBRARY = 'library'
    XML_NODE_FILE = 'file'
    XML_NODE_CONFIG = 'config'
    XML_NODE_COMMENT = '#comment'
    XML_NODE_TEXT = '#text'
    XML_NODE_CONSTRAINTS = 'constraints'
    XML_NODE_GENERIC = 'generic'
    XML_NODE_UNITTEST = 'unittest'
    # XML attributes identify parameters that can be applied to XML nodes.
    ATTRIBUTE_NAME = 'name'
    ATTRIBUTE_PATH = 'path'
    ATTRIBUTE_FLOW = 'flow'
    ATTRIBUTE_PREPROCESSOR = 'preprocessor'
    ATTRIBUTE_SYNTHESIS = 'synthesise'
    # These XML attributes are required configuration attributes that control
    # which tools and directories are used by the framework. They must be
    # present in the project file.
    ATTRIBUTE_SIM_DIR = 'simulation_directory'
    ATTRIBUTE_SYNTH_DIR = 'synthesis_directory'
    ATTRIBUTE_SIM_TOOL = 'simulator'
    ATTRIBUTE_SYNTH_TOOL = 'synthesiser'
    ATTRIBUTE_SYNTH_PART = 'part'
    ATTRIBUTE_REPORTER = 'reporter'
    ATTRIBUTE_LIBRARY = 'library'

    # Additional tool arguments can be attached to File objects by supplying
    # attributes using the naming convention:
    #   args_toolname_flowstagenname
    # These attributes will be stored with the file so that the additional
    # arguments can be used by the relevent tool and flow stage if it is
    # invoked on the file.
    XML_ADDITIONAL_TOOL_ARGS_RE = re.compile(
        'args_([A-Z,a-z]+)_([A-Z,a-z]+)'
    )

    def bool_processor(value, root):
        if isinstance(value, bool):
            return value
        elif value is None:
            return None
        else:
            return value.lower() != 'false'

    def string_tolower(value, root):
        if isinstance(value, str):
            return value.lower()
        else:
            return value

    # Process nodes according to the processor functions contained within this
    # dictionary.
    NODE_PROCESSOR = {
        ATTRIBUTE_PATH: utils.relative_path_to_abs,
        ATTRIBUTE_SIM_DIR: utils.relative_path_to_abs,
        ATTRIBUTE_SYNTH_DIR: utils.relative_path_to_abs,
        ATTRIBUTE_PREPROCESSOR: utils.relative_path_to_abs,
        ATTRIBUTE_REPORTER: utils.relative_path_to_abs,
        ATTRIBUTE_SYNTHESIS: bool_processor,
        ATTRIBUTE_SIM_TOOL: lambda x, root: x,
        ATTRIBUTE_SYNTH_TOOL: lambda x, root: x,
        ATTRIBUTE_SYNTH_PART: lambda x, root: x,
        ATTRIBUTE_LIBRARY: string_tolower,
    }

    # Default fields for different node types
    FILE_NODE_DEFAULTS = {
        ATTRIBUTE_PATH: None,
        ATTRIBUTE_SYNTHESIS: None,
        ATTRIBUTE_PREPROCESSOR: None,
    }

    PROJECT_NODE_DEFAULTS = {
        ATTRIBUTE_SYNTHESIS: None,
        ATTRIBUTE_PATH: None,
    }

    LIBRARY_NODE_DEFAULTS = {
        ATTRIBUTE_NAME: None,
        ATTRIBUTE_SYNTHESIS: None,
    }

    UNITTEST_NODE_DEFAULTS = {
        ATTRIBUTE_PATH: None,
    }

    CONSTRAINTS_NODE_DEFAULTS = {
        ATTRIBUTE_PATH: None,
        ATTRIBUTE_FLOW: None,
    }

    @staticmethod
    def cast_attributes_to_dict(attributes):
        """
        Ensure that attributes is a dictionary. Casts None to an empty dict
        and casts an xml.dom.minidom.NamedNodeMap to a dict.
        """
        if attributes is None:
            return {}
        elif isinstance(attributes, xml.dom.minidom.NamedNodeMap):
            attributes = dict(attributes.items())
        return attributes

    @staticmethod
    def process_attributes(attributes, root, defaults={}):
        """Process each of the attributes in the supplied dictionary or
        xml.dom.minidom.NamedNodeMap using the associated functions in the
        NODE_PROCESSOR dictionary and return an updated dictionary of the
        attribute name, value pairs. 
        
        If the defaults dictionary is supplied, the returned dictionary will
        contain *at least* the keys and associated values present in the
        defaults dictionary.
        
        The root argument is passed to the NODE_PROCESSOR functions and it
        should be a string path pointing to the project root directory, this
        ensures any file paths can be cast to absolute paths correctly.
        """
        # Ensure that the attributes argument is a dictionary type:
        attributes = ProjectAttributes.cast_attributes_to_dict(attributes)

        # Obtain a list of the attribute names to process, the result will
        # contain a value for each of these keys:
        keys = set(list(attributes.keys()) + list(defaults.keys()))
        # Process each of the attributes using the NODE_PROCESSOR
        for name in keys:
            # Obtain the function to process the attribute value from the
            # NODE_PROCESSOR dictionary if available, otherwise obtain the
            # value from the defaults dictionary. If neither dictionaries
            # contain an entry for the attribute then return the original
            # value.
            processor = ProjectAttributes.NODE_PROCESSOR.get(
                name,
                # Return the original value.
                lambda x, root: x 
            )
            value = attributes.get(name, defaults.get(name, None))
            attributes[name] = value
            if value is not None:
                attributes[name] = processor(value, root)
            
        return attributes

    @staticmethod
    def get_processed_attribute(attribute, root, name):
        """
        Process the given attribute according to the functions in the
        NODE_PROCESSOR dictionary using the name as a key and the root as the
        project root. The original attribute is returned if no NODE_PROCESSOR
        function can be found that matches the name.
        """
        return ProjectAttributes.NODE_PROCESSOR.get(
            name, 
            lambda x, root: x
        )(attribute, root)


class UnitTestFile(object):
    """The UnitTestFile object provides a container for Python test shims."""
    def __init__(self, **kwargs):
        self.path = kwargs[ProjectAttributes.ATTRIBUTE_PATH]
        self.fileType = FileType.Python
        self.testsuite = None


class File(object):
    """
    The File object contains properties of a design source file that has been
    loaded from the project XML file.
    """

    def __init__(self, library, **kwargs):
        # The library to which this file belongs
        self.library = library
        # MD5 sum for change detection
        self.md5 = ''
        # The path to this source file
        self.path = kwargs[ProjectAttributes.ATTRIBUTE_PATH]
        # A flag to indicate whether or not this file should be included for
        # synthesis. It not specified it will default to True.
        self.synthesise = kwargs.get(
            ProjectAttributes.ATTRIBUTE_SYNTHESIS,
            True
        )
        self.synthesise = True if self.synthesise is None else self.synthesise
        # The preprocessor is a path to a Python module containing a
        # preprocessor object that can edit the associated source file before
        # it is passed to synthesis.
        self.preprocessor = kwargs.get(
            ProjectAttributes.ATTRIBUTE_PREPROCESSOR,
            None
        )
        # Automatically discover the filetype from the extension
        fileName, fileExtension = os.path.splitext(self.path)
        fileExtension = fileExtension.strip(' ')  # Remove trailing whitespace
        self.fileType = fileExtensionsLookup.get(fileExtension, FileType.VHDL)
        # Search through the keyword arguments for any attributes that match
        # the XML_ADDITIONAL_TOOL_ARGS_RE search pattern and store these as
        # additional tool arguments
        self.optionalToolArgs = {}
        for k, v in kwargs.items():
            match = ProjectAttributes.XML_ADDITIONAL_TOOL_ARGS_RE.match(k)
            if match:
                try:
                    toolName = match.group(1)
                    flowName = match.group(2)
                except IndexError:
                    # The attribute matched but did not return enough match
                    # groups.
                    log.warning(
                        'Ignoring attribute {0} on file {1}'.format(
                            k,
                            self.path
                        )
                    )
                    continue
                if toolName not in self.optionalToolArgs:
                    self.optionalToolArgs[toolName] = {}
                self.optionalToolArgs[toolName][flowName] = v
                log.debug(
                    'Added attribute {0} with value {2} to file {1}'.format(
                        k,
                        self.path,
                        v
                    )
                )

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def get_tool_arguments(self, toolName, flowName):
        """
        Return the optional tool arguments attached to this file for the given
        toolname and flowname. If the tool or flow are not present in the
        optional arguments then return an empty string.
        """
        return self.optionalToolArgs.get(toolName, {}).get(flowName, '')


class Constraints(object):
    """The constraints object provides a container for constraints files"""
    def __init__(self, **kwargs):
        self.path = kwargs[ProjectAttributes.ATTRIBUTE_PATH]
        self.fileType = FileType.Unknown
        self.flow = kwargs.get(ProjectAttributes.ATTRIBUTE_FLOW, None)
        fileName, fileExtension = os.path.splitext(self.path)
        fileExtension = fileExtension.strip(' ')
        if fileExtension in fileExtensionsLookup.keys():
            self.fileType = fileExtensionsLookup[fileExtension]
