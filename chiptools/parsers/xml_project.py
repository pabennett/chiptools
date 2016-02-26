import logging
import traceback
import xml
import os
import time

from xml.dom import minidom

from chiptools.common import utils
from chiptools.common.filetypes import ProjectAttributes

log = logging.getLogger(__name__)


class XmlProjectParser:
    """
    The XmlProjectParser class implements an XML parser for project files using
    the following format.

    .. note:: All paths appearing in a project file are relative to the
              location of the project file.

    **<project>**

    The project parent tag encapsulates all configuration and file tags
    belonging to a project file. Existing project files may be imported into
    a project by including a project tag with the *path* attribute pointing to
    the existing XML file.

    +-----------+--------+----------------------------------------------------+
    | Attribute | Value  | Description                                        |
    +===========+========+====================================================+
    | synthesise| True   | (default) These files are included for synthesis.  |
    |           +--------+----------------------------------------------------+
    |           | False  | Exclude these files from synthesis.                |
    +-----------+--------+----------------------------------------------------+
    | path      |*string*| Path to existing project file to include.          |
    +-----------+--------+----------------------------------------------------+

    **<library>**

    The *library* tag is used to group all child file tags into
    the same library. If a file is not associated with a library it will
    default to the *work* library.

    +-----------+--------+----------------------------------------------------+
    | Attribute | Value  | Description                                        |
    +===========+========+====================================================+
    | synthesise| True   | (default) These files are included for synthesis.  |
    |           +--------+----------------------------------------------------+
    |           | False  | Exclude these files from synthesis.                |
    +-----------+--------+----------------------------------------------------+
    | name      |*string*| (required) Name of the HDL library for these files.|
    +-----------+--------+----------------------------------------------------+

    **<file>**

    The *file* tag is used to define a source file to include in the project.
    Source files can either be text based HDL source files (VHDL or Verilog) or
    they can be netlists. Tool wrapper plugins will check the file extension to
    determine how they should process the file, for example .VHD and .V files
    will be processed with vcom and vlog respectively by Modelsim and .ngc
    files will be copied into the synthesis folder by ISE.

    +-----------+--------+----------------------------------------------------+
    | Attribute | Value  | Description                                        |
    +===========+========+====================================================+
    | synthesise| True   | (default) This file is included for synthesis.     |
    |           +--------+----------------------------------------------------+
    |           | False  | Exclude this file from synthesis.                  |
    +-----------+--------+----------------------------------------------------+
    | path      |*string*| (required) Path to the source file.                |
    +-----------+--------+----------------------------------------------------+

    .. note:: If a file tag is used outside of a library tag the file will
              automatically be associated with the *work* library and a
              warning will be displayed.

    .. note:: File tags support additional optional attributes of the form
             *args_toolname_compile* where *toolname* is the name of a specific
             tool wrapper (for example: *modelsim*). The attribute value is
             passed to the simulation tool during compilation if it is the
             selected tool. *args_modelsim_compile='-2008'* would pass the
             command line arg '-2008' to Modelsim when it compiles the file.

    **<constraints>**

    The *constraints* tag defines the path to a constraints file to be included
    when performing synthesis on the project. Constraints can be limited to a
    specific synthesis tool via use of the *flow* attribute.

    +-----------+--------+----------------------------------------------------+
    | Attribute | Value  | Description                                        |
    +===========+========+====================================================+
    | path      |*string*| (required) Path to the constraints file.           |
    +-----------+--------+----------------------------------------------------+
    | flow      |*string*| (optional) Name of the associated synthesis tool.  |
    +-----------+--------+----------------------------------------------------+

    **<unittest>**

    The *unittest* tag defines the path to a Python based unit test suite to
    be included in the project test suite. Unit tests must be valid Python
    files with a .py extension. If the file is invalid or contains syntax
    errors it will be excluded from the project test suite. Runtime errors
    occurring from a unit test will result in that test failing.


    +-----------+--------+----------------------------------------------------+
    | Attribute | Value  | Description                                        |
    +===========+========+====================================================+
    | path      |*string*| (required) Path to the unit test file.             |
    +-----------+--------+----------------------------------------------------+

    **<generic>**

    The *generic* tag defines a generic value setting for the top level entity
    during synthesis. Generic attribute names map to the name of a generic on
    the top level entity and the associated value is passed as the generic
    value.

    +----------+-------+------------------------------------------------------+
    | Attribute| Value | Description                                          |
    +==========+=======+======================================================+
    | (name)   |(value)| Set top level generic *name* to *value* at synthesis.|
    +----------+-------+------------------------------------------------------+

    **<config>**

    The *config* tag defines a config value setting for the project.
    Config attribute names map to the name of a configuration item in the
    project and the associated value is passed as the config value.

    +----------+-------+------------------------------------------------------+
    | Attribute| Value | Description                                          |
    +==========+=======+======================================================+
    | (name)   |(value)| Set the configuration item *name* to *value*.        |
    +----------+-------+------------------------------------------------------+

    The following configuration items can be set in a project:

    +----------------------+--------------------------------------------------+
    | Config               | Description                                      |
    +======================+==================================================+
    | simulation_directory | Directory to use as simulation working directory.|
    +----------------------+--------------------------------------------------+
    | synthesis_directory  | Directory to use as synthesis working directory. |
    +----------------------+--------------------------------------------------+
    | simulator            | Default simulator to use for this project.       |
    +----------------------+--------------------------------------------------+
    | synthesiser          | Default synthesiser to use for this project.     |
    +----------------------+--------------------------------------------------+
    | part                 | FPGA part to target when performing synthesis.   |
    +----------------------+--------------------------------------------------+

    In addition to the above configuration items, the *config* tag also allows
    tool-specific argument passing through the use of config attributes using
    the following naming convention: *args_toolname_flowname*, where
    *toolname* is the name of the tool to target and *flowname* is the name
    of a specific tool flow stage. For example:
    args_ise_par='-mt 4 -ol high -xe n' would pass the arguments
    *-mt 4 -ol high -xe n* to the place and route stage of an ISE synthesis
    flow. Each tool wrapper implements its own specific flow stage names.

    .. note:: If a configuration item is already defined any new definitions
              will be ignored. A warning will be displayed if a
              redefinition is attempted.

    """

    @staticmethod
    def load_project(path, project_object):
        """
        Load the project XML file provided by the *path*.
        """
        log.info('Loading project: ' + str(path))
        project_object.initialise()
        base_name = os.path.basename(path).split('.')[0]
        cache_path = os.path.join(
            os.path.dirname(path),
            '.' + base_name
        )
        project_object.set_cache_path(cache_path)
        # Parse the project file
        XmlProjectParser.parse_project(path, project_object)

    @staticmethod
    def parse_project(
        filepath,
        project_object,
        synthesise=None
    ):
        """Parse the XML project and update the project_dictionary or return
        a new dictionary if one is not supplied.
        """
        log.info('Parsing: ' + str(filepath) + ' synthesis=' + str(synthesise))
        start_time = time.time()
        project_root = os.path.dirname(os.path.realpath(filepath))
        try:
            xml_obj = minidom.parse(filepath)
            for project_node in xml_obj.getElementsByTagName(
                ProjectAttributes.XML_NODE_PROJECT
            ):
                # Project attributes (if any)
                # If this whole node should not be synthesised, ignore any
                # child flags otherwise get the child synthesis flag and use
                # that.
                if synthesise is None:
                    project_attribs = ProjectAttributes.process_attributes(
                        project_node.attributes,
                        project_root
                    )
                    synthesis_enabled = project_attribs.get(
                        ProjectAttributes.ATTRIBUTE_SYNTHESIS,
                        None
                    )
                else:
                    synthesis_enabled = synthesise

                for child in project_node.childNodes:
                    if child.nodeName == ProjectAttributes.XML_NODE_PROJECT:
                        attribs = ProjectAttributes.process_attributes(
                            child.attributes,
                            project_root,
                            default=ProjectAttributes.PROJECT_NODE_DEFAULTS
                        )
                        # If this whole node should not be synthesised, ignore
                        # any child flags otherwise get the child synthesis
                        # flag and use that.
                        if synthesis_enabled is None:
                            synthesise = attribs.get(
                                ProjectAttributes.ATTRIBUTE_SYNTHESIS,
                                None
                            )
                        else:
                            synthesise = synthesis_enabled

                        if ProjectAttributes.ATTRIBUTE_PATH in attribs:
                            log.debug(
                                'Found sub-project: ' +
                                str(
                                    attribs[
                                        ProjectAttributes.ATTRIBUTE_PATH
                                    ]
                                )
                            )
                            # Recursively call this parser with the new project
                            # path
                            XmlProjectParser.parse_project(
                                str(
                                    attribs[
                                        ProjectAttributes.ATTRIBUTE_PATH
                                    ]
                                ),
                                project_object,
                                synthesise
                            )
                    elif child.nodeName == ProjectAttributes.XML_NODE_CONFIG:
                        XmlProjectParser._add_config(
                            child,
                            project_root,
                            project_object
                        )
                    elif child.nodeName == ProjectAttributes.XML_NODE_LIBRARY:
                        XmlProjectParser._add_library(
                            child,
                            project_root,
                            project_object,
                            synthesis_enabled
                        )
                    elif child.nodeName == (
                        ProjectAttributes.XML_NODE_CONSTRAINTS
                    ):
                        XmlProjectParser._add_constraints(
                            child,
                            project_root,
                            project_object,
                        )
                    elif child.nodeName == (
                        ProjectAttributes.XML_NODE_UNITTEST
                    ):
                        XmlProjectParser._add_unittest(
                            child,
                            project_root,
                            project_object,
                        )
                    elif child.nodeName == ProjectAttributes.XML_NODE_GENERIC:
                        # Build a dictionary of generics using the attribute
                        # name and value
                        attribs = child.attributes
                        if attribs is None:
                            continue
                        attribs = dict(attribs.items())
                        for attrName, attrVal in attribs.items():
                            project_object.add_generic(
                                attrName,
                                attrVal
                            )
                    elif child.nodeName == ProjectAttributes.XML_NODE_FILE:
                        # Files should not be left unassociated with a library
                        # unless you wish to add all files to the work library.
                        # The default behavior will be to add parentless files
                        # to the work library, but a configuration option could
                        # make this post an error instead.
                        log.warning(
                            'Found file with no parent library, ' +
                            'defaulting to work library'
                        )
                        # If this whole node should not be synthesised, ignore
                        # any child flags otherwise get the child synthesis
                        # flag and use that.
                        if synthesis_enabled is None:
                            synthesise = (
                                ProjectAttributes.get_processed_attribute(
                                    child.attributes.get(
                                        ProjectAttributes.ATTRIBUTE_SYNTHESIS,
                                        None
                                    ),
                                    project_root,
                                    ProjectAttributes.ATTRIBUTE_SYNTHESIS
                                )
                            )
                        else:
                            synthesise = synthesis_enabled

                        XmlProjectParser._add_file(
                            child,
                            'work',
                            project_root,
                            project_object,
                            synthesise=synthesise
                        )
                    elif child.nodeName == ProjectAttributes.XML_NODE_TEXT:
                        pass
                    elif child.nodeName == ProjectAttributes.XML_NODE_COMMENT:
                        pass
        except xml.parsers.expat.ExpatError:
            log.error(
                'Error found in XML file, check the formatting. ' +
                'Refer to the traceback below for the line number and file.'
            )
            log.error(traceback.format_exc())
            project_object.initialise()
            return
        log.debug(filepath + ' parsed in ' + utils.time_delta_string(
            start_time,
            time.time())
        )

    @staticmethod
    def _add_config(child, root, project_object):
        """Process and add all child attributes to the given
        configuration dict. Return a reference to the modified dict.
        """
        config = {}
        for k, v in child.attributes.items():
            if v is not None:
                config[k] = v
        project_object.add_config_dict(**config)

    @staticmethod
    def _add_file(
        file_node,
        library_name,
        root,
        project_object,
        synthesise
    ):
        """Add the given file to the given library and ensure that any
        relative file paths are correctly converted into absolute paths using
        the project_root as a reference"""
        attribs = ProjectAttributes.process_attributes(
            file_node.attributes,
            root,
            defaults=ProjectAttributes.FILE_NODE_DEFAULTS
        )
        if attribs[ProjectAttributes.ATTRIBUTE_PATH] is not None:
            # Override the file synthesis flag if the library is marked for
            # exclusion from synthesis
            if synthesise is not None:
                attribs[ProjectAttributes.ATTRIBUTE_SYNTHESIS] = synthesise
            # Path is passed directly, so remove it from kwargs
            path = attribs[ProjectAttributes.ATTRIBUTE_PATH]
            del attribs[ProjectAttributes.ATTRIBUTE_PATH]
            project_object.add_file(
                path=path,
                library=library_name,
                **attribs
            )
        else:
            log.warning('Ignoring file with no path.')

    @staticmethod
    def _add_library(
        child,
        root,
        project_object,
        synthesise,
    ):
        """Process the given library node and add it to the
        project_dictionary. Any files containedwithin the library will be
        added to the project_dictionary under that library"""
        attribs = ProjectAttributes.process_attributes(
            child.attributes, 
            root,
            defaults=ProjectAttributes.LIBRARY_NODE_DEFAULTS
        )
        if attribs[ProjectAttributes.ATTRIBUTE_NAME] is None:
            log.warning('Ignoring library with no name specified')
            return
        library_name = attribs[ProjectAttributes.ATTRIBUTE_NAME]
        if synthesise is None:
            synthesise = attribs[ProjectAttributes.ATTRIBUTE_SYNTHESIS]
        # Add all files in this library node to the project
        for file_node in filter(
            lambda x: x.nodeName == ProjectAttributes.XML_NODE_FILE,
            child.childNodes
        ):
            XmlProjectParser._add_file(
                file_node,
                library_name,
                root,
                project_object,
                synthesise,
            )

    @staticmethod
    def _add_constraints(child, root, project_object):
        attribs = ProjectAttributes.process_attributes(
            child.attributes, 
            root,
            defaults=ProjectAttributes.CONSTRAINTS_NODE_DEFAULTS
        )
        path = attribs[ProjectAttributes.ATTRIBUTE_PATH]
        # Path is passed separately, so delete it from the kwargs dict.
        del attribs[ProjectAttributes.ATTRIBUTE_PATH]
        project_object.add_constraints(
            path,
            **attribs
        )

    @staticmethod
    def _add_unittest(child, root, project_object):
        attribs = ProjectAttributes.process_attributes(
            child.attributes, 
            root,
            defaults=ProjectAttributes.UNITTEST_NODE_DEFAULTS
        )
        path = attribs[ProjectAttributes.ATTRIBUTE_PATH]
        # Path is passed separately, so delete it from the kwargs dict.
        del attribs[ProjectAttributes.ATTRIBUTE_PATH]
        project_object.add_unittest(
            path,
            **attribs
        )
