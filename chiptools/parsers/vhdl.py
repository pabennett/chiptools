import logging
import re
import os

log = logging.getLogger(__name__)


def remove_comments(data):
    """Return the supplied VHDL file data string, *data*, with all comments
    removed."""
    return re.sub(r'--[^\n]*', '', data)


class Function:

    REGEX = re.compile(
        r"""
        \s*
        function
        \s+
        (?P<ident>\w+)
        \s*
        (?:\([^;]*)?
        \s*
        return
        \s*
        (?:\w+)
        \s+
        is
        """, re.IGNORECASE | re.VERBOSE,
    )

    def __init__(self, name, library='work'):
        self.name = name
        self.library = library

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return "<Function {0}>".format(self.name)

    def __eq__(self, other):
        if not isinstance(other, Function):
            return False
        return self.name == other.name

    @classmethod
    def get_all_definitions(cls, data, library='work'):
        definitions = set()
        for match in cls.REGEX.finditer(data):
            ident = match.group('ident')
            definitions.add(cls(name=ident, library=library))
        return list(definitions)


class Procedure:

    REGEX = re.compile(
        r"""
        \s*
        procedure
        \s+
        (?P<id>\w+)
        \s*
        (?:\([^;]*)?
        \s*
        return
        \s*
        (?:\w+)
        \s+
        is
        """, re.IGNORECASE | re.VERBOSE,
    )

    def __init__(self, name, library='work'):
        self.name = name
        self.library = library

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return "<Procedure {0}>".format(self.name)

    def __eq__(self, other):
        if not isinstance(other, Procedure):
            return False
        return self.name == other.name

    @classmethod
    def get_all_definitions(cls, data, library='work'):
        definitions = set()
        for match in cls.REGEX.finditer(data):
            ident = match.group('ident')
            definitions.add(cls(name=ident, library=library))
        return list(definitions)


class Package:

    PACKAGE_START_RE = re.compile(
        r"""
        \b                      # Word boundary
        package                 # 'Package' keyword
        \s+                     # 1 or more whitespace
        (?P<ident>\w+)          # Mandatory identifier
        \s+                     # 1 or more whitespace
        (?:is)                  # 'is' keyword
        """, re.IGNORECASE | re.VERBOSE,
    )

    PACKAGE_USE_CLAUSES = (
        r"""
        \b                      # Word boundary
        use                     # use keyword
        \s*                     # Optional whitepsace
        %(library)s             # Dynamic library name
        \.                      # '.' separator
        (?P<module>\w+)         # Module name
        \.                      # '.' separator
        (?P<unit>all|\w+)       # Part name ('all' or custom name)
        \s*                     # Optional whitespace
        ;                       # Terminator
        """
    )

    def __init__(self, name, library='work', unit=None):
        self.name = name
        self.library = library
        # For package references, this is the unit referenced within the
        # package, either 'all' or a named unit.
        self.unit = unit

    @classmethod
    def get_all_references(cls, data, libraries):
        references = set()
        for library in libraries:
            includes_re = re.compile(
                Package.PACKAGE_USE_CLAUSES % dict(library=library),
                re.IGNORECASE | re.VERBOSE,
            )
            for include in includes_re.finditer(data):
                package = Package(
                    include.group('module'),
                    library=library,
                    unit=include.group('unit')
                )
                references.add(package)
        return list(references)

    @classmethod
    def get_all_definitions(cls, data, library='work'):
        definitions = set()
        for match in Package.PACKAGE_START_RE.finditer(data):
            ident = match.group('ident')
            definitions.add(Package(name=ident, library=library))
        return list(definitions)

    def __hash__(self):
        return hash((self.name, self.library))

    def __repr__(self):
        return "<Package {0}.{1}>".format(self.library, self.name)

    def __eq__(self, other):
        if not isinstance(other, Package):
            return False
        return (self.name == other.name and self.library == other.library)


class Entity:

    ENTITY_START_RE = re.compile(
        r"""
        \b              # Word boundary
        entity          # 'Entity' keyword
        \s+             # 1 or more whitespace
        (?P<ident>\w+)  # Mandatory identifier
        \s+             # 1 or more whitespace
        (?:is)          # 'is' keyword
        """, re.IGNORECASE | re.VERBOSE,
    )

    def __init__(self, name, library='work'):
        self.name = name
        self.library = library

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return "<Entity {0}>".format(self.name)

    def __eq__(self, other):
        if not isinstance(other, Entity):
            return False
        return self.name == other.name

    @classmethod
    def get_all_definitions(cls, data, library):
        definitions = set()
        for match in Entity.ENTITY_START_RE.finditer(data):
            ident = match.group('ident')
            definitions.add(Entity(name=ident, library=library))
        return list(definitions)

    @classmethod
    def get_all_references(cls, data, libraries):
        """
        Entity references are made by direct instantiation or by a component
        instantiation via a component definition. Embedded configurations can
        be used to make a component instantiation reference a entity directly.
        """
        # TODO:
        raise NotImplementedError('Use Component.get_all_references()')


class Configuration:

    CONFIGURATION_RE = re.compile(
        r"""
        \b                                  # Word boundary
        configuration                       # Component keyword
        \s+                                 # At least one whitespace
        (?P<ident>\w+)                      # Identifier
        \s+                                 # At least one whitespace
        of                                  # 'of' keyword
        \s+                                 # At least one whitespace
        (?P<entity>\w+)                     # Identifier
        \s+                                 # At least one whitespace
        is                                  # 'is' keyword
        """, re.IGNORECASE | re.VERBOSE,
    )

    def __init__(self, name, entity, library='work'):
        self.name = name
        self.entity = entity
        self.library = library

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return "<Configuration {0}>".format(self.name)

    def __eq__(self, other):
        if not isinstance(other, Configuration):
            return False
        return self.name == other.name

    @classmethod
    def get_all_definitions(cls, data, library):
        definitions = set()
        for match in cls.CONFIGURATION_RE.finditer(data):
            ident = match.group('ident'),
            entity = match.group('entity')
            definitions.add(
                Configuration(
                    name=ident,
                    entity=entity,
                    library=library
                )
            )
        return list(definitions)


class Component:

    COMPONENT_RE = re.compile(
        r"""
        \b                                  # Word boundary
        component                           # Component keyword
        \s*                                 # Optional whitepsace
        (?P<entity>\w+)                     # Identifier
        \s*                                 # Optional whitespace
        (is)?                               # Optional 'is' keyword
        \s*                                 # Optional whitespace
        """, re.IGNORECASE | re.VERBOSE,
    )

    # Detect an Entity or Component instantation
    INSTANCE_RE = re.compile(
        r"""
        \b                                  # Word boundary
        (?P<ident>\w+)                      # Identifier
        \s*                                 # Optional whitespace
        :                                   # ':' delimeter
        \s*                                 # Optional whitespace
        (?:entity\s*)?                      # Optional entity
        (?:(?P<library>\w+)(?:\.))?         # Optional library
        (?P<entity>\w+)                     # Module name
        \s*                                 # Optional whitespace
        (?:generic\s+map|port\s+map)        # Generic map or port map
        [^;]*                               # Everything except a Terminator
        ;                                   # Terminator
        """, re.IGNORECASE | re.VERBOSE,
    )

    def __init__(self, entity, instance=None, library=None):
        self.name = instance
        self.entity = entity
        self.library = library

    def __eq__(self, other):
        if not isinstance(other, Component):
            return False
        return self.entity == other.entity

    def __hash__(self):
        return hash(self.entity)

    def __repr__(self):
        if self.name is not None:
            return "<Component {0} ({1})>".format(self.entity, self.name)
        else:
            return "<Component {0}>".format(self.entity)

    @classmethod
    def get_all_definitions(cls, data, library):
        definitions = set()
        for match in Component.COMPONENT_RE.finditer(data):
            ident = match.group('entity')
            definitions.add(Component(ident, library=library))
        return list(definitions)

    @classmethod
    def get_all_references(cls, data, binding_indications=None):
        references = set()
        for instance in Component.INSTANCE_RE.finditer(data):
            ident = instance.group('ident')
            lib = instance.group('library')  # Optional
            entity = instance.group('entity')
            # Either a component or entity instantiation
            if lib is not None:
                # VHDL 93 style entity instantiation
                instance = Entity(entity, library=lib)
            else:
                instance = Component(entity, instance=ident, library=lib)
                # Component instantiation
                # Check the binding indications to see if the instance has
                # been explictly linked to an entity or configuration:
                if binding_indications is not None:
                    if ident in binding_indications:
                        if entity in binding_indications[ident]:
                            instance = binding_indications[ident][entity]
                    elif entity in binding_indications['all']:
                        instance = binding_indications['all'][entity]
            # Add the instance reference
            references.add(instance)
            # Instantiations referencing a compoent declaration introduce an
            # implicit reference to an entity of the same name and port mapping
            if isinstance(instance, Component):
                references.add(Entity(entity, library=lib))
        return list(references)


class ParsedVhdlFile:
    """
    The ParsedVhdlFile class provides a high level wrapper for a source Vhdl
    file and provides convenient access to the design units referenced and
    declared by a file.
    """

    LIBRARY_RE = re.compile(
        r"""
        \b                  # Word boundary
        library             # Library keyword
        \s*                 # Optional whitespace
        (?P<library>\w+)    # Library name
        \s*                 # Optional whitespace
        ;                   # Terminator
        """, re.IGNORECASE | re.VERBOSE,
    )

    # Find any binding indications which indicate which unit to use for a
    # given instantiation.
    BINDING_INDICATION_RE = re.compile(
        r"""
        \b                                      # Word boundary
        for                                     # 'for' keyword
        \s+                                     # At least one whitespace
        (?P<instance_label>all|\w+)             # Instance label
        \s*                                     # Optional whitespace
        :                                       # ':' delimeter
        \s*                                     # Optional whitespace
        (?P<component_name>\w+)                 # Component name
        \s+                                     # At least one whitespace
        use                                     # 'use' keyword
        \s+                                     # At least one whitespace
        # Target spec (configuration or entity)
        (?P<target_spec>entity|configuration)
        \s*                                     # Optional whitespace
        # Either a library.entity(architecture) for 'entity' target spec
        # or a library.configuration for 'configuration' target spec
        (
            (?P<e_library>\w+)\.(?P<entity>\w+)\((?P<architecture>\w+)\) |
            (?P<c_library>\w+)\.(?P<configuration>\w+)
        )
        """, re.IGNORECASE | re.VERBOSE,
    )

    def __init__(self, file_object):
        """
        Parse the file object and initialise a ParsedVhdlFile instance
        """
        self.file_object = file_object
        self.path = self.file_object.path
        self.name = os.path.splitext(os.path.basename(self.path))[0]
        self.library = self.file_object.library
        self._parse(self.path, self.library)

    def __repr__(self):
        return "<ParsedVhdlFile {0} ({1})>".format(
            self.name,
            self.library
        )


    @classmethod
    def _get_libraries(cls, data):
        """Parse the input string as VHDL and return any library
        declarations and use-clauses"""
        # Initialise a set containing each unique library declaration found
        # in the input string.
        libraries = set(['work'])  # Work library is always included
        for match in ParsedVhdlFile.LIBRARY_RE.finditer(data):
            lib = match.group('library')
            libraries.add(lib)
        return libraries

    @classmethod
    def _get_binding_indications(cls, data):

        indications = {'all': {}}

        for match in cls.BINDING_INDICATION_RE.finditer(
            data
        ):
            instance_label = match.group('instance_label')
            component_name = match.group('component_name')
            target_spec = match.group('target_spec')
            entity_name = match.group('entity')
            configuration_name = match.group('configuration')

            if target_spec == 'configuration':
                library = match.group('c_library')
                target = Configuration(configuration_name, library=library)
            elif target_spec == 'entity':
                library = match.group('e_library')
                target = Entity(
                    entity_name,
                    library=library
                )
            else:
                log.error(
                    'Illegal configuration target: {0}'.format(
                        target_spec
                    )
                )
                target = None

            # Binding indications instruct the compiler to substitute
            # items with the given instance_label and entity with the given
            # target_spec, which can either be a configuration or an entity.
            # The instance_label can be 'all' or a specific instance label.
            if instance_label not in indications:
                indications[instance_label] = {}
            if component_name not in indications[instance_label]:
                indications[instance_label][component_name] = target

        return indications

    def _parse(self, path, library='work'):
        """
        Parse the supplied data string and initialise the class.
        """
        with open(path, 'r') as f:
            data = f.read()
            data = data.lower()  # VHDL is case insensitive

        # Get the file data with comments removed and ensure that it is lower
        # case.
        data = remove_comments(data.lower())

        # Get the libraries referenced by this file.
        self.libraries = self._get_libraries(data)

        # Get any binding indications used in this file.
        indications = self._get_binding_indications(data)

        # Get any package references and declarations
        self.package_refs = Package.get_all_references(data, self.libraries)
        self.package_defs = Package.get_all_definitions(data, library)

        # Get any embedded configurations
        self.configuration_defs = Configuration.get_all_definitions(
            data,
            library
        )

        # Get any component and entity references and declarations
        unit_references = Component.get_all_references(data, indications)
        self.component_refs = list(
            filter(lambda x: isinstance(x, Component), unit_references)
        )
        self.entity_refs = list(
            filter(lambda x: isinstance(x, Entity), unit_references)
        )
        self.component_defs = Component.get_all_definitions(data, library)
        self.entity_defs = Entity.get_all_definitions(data, library)

        # Get any function references and declarations
        self.function_defs = Function.get_all_definitions(data, library)

        # Get any procedure references and declarations
        self.procedure_defs = Procedure.get_all_definitions(data, library)

        self.definitions = []
        self.definitions += self.entity_defs
        self.definitions += self.package_defs
        self.definitions += self.component_defs
        self.definitions += self.configuration_defs
        self.definitions += self.function_defs
        self.definitions += self.procedure_defs

        self.references = []
        self.references += self.entity_refs
        self.references += self.package_refs
        self.references += self.component_refs

        self.children = []
        self.parents = []
