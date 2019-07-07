from opencmiss.zinc.field import Field
from opencmiss.zinc.graphics import Graphics
from opencmiss.zinc.glyph import Glyph
from opencmiss.zinc.material import Material
from opencmiss.zinc.node import Node
from opencmiss.zinc.streamregion import StreaminformationRegion
from opencmiss.utils.zinc import create_finite_element_field

from scaffoldmaker.scaffolds import Scaffolds
from scaffoldmaker.scaffoldpackage import ScaffoldPackage

from ..utils import maths


class ScaffoldModel(object):

    def __init__(self, context, region, generator_model, parameters, material_module, scaffold_package,
                 scaffold_package_class):

        self._context = context
        self._region = region

        self._generator_model = generator_model
        self._material_module = material_module
        self._parameters = parameters.keys()
        self._coordinate_field = None
        _scaffold_package = scaffold_package
        _scaffold_package_class = scaffold_package_class

        scaffolds = Scaffolds()
        self._all_scaffold_types = scaffolds.getScaffoldTypes()

        for x in self._all_scaffold_types:
            if x == _scaffold_package[-1].getScaffoldType():
                scaffold_type = x
        scaffold_package = ScaffoldPackage(scaffold_type)
        self._parameterSetName = scaffold_type.getParameterSetNames()[0]
        self._scaffold_package = scaffold_package

        self._scaffold = None
        self._scaffold_options = None
        self._temp_region = None
        self._annotation_groups = None
        self._scene = None
        self._scaffold_is_time_aware = None
        self._scaffold_fit_parameters = None
        self._initialise_surface_material()

    def get_region(self):
        return self._region

    def _create_surface_graphics(self):
        self._scene.beginChange()
        surface = self._scene.createGraphicsSurfaces()
        surface.setCoordinateField(self._coordinate_field)
        surface.setRenderPolygonMode(Graphics.RENDER_POLYGON_MODE_SHADED)
        surface_material = self._material_module.findMaterialByName('trans_blue')
        surface.setMaterial(surface_material)
        surface.setName('display_surfaces')
        self._scene.endChange()
        return surface

    def _create_node_graphics(self):
        self._scene.beginChange()
        self._node_derivative_labels = ['D1', 'D2', 'D3', 'D12', 'D13', 'D23', 'D123']
        fm = self._region.getFieldmodule()
        fm.beginChange()
        cmiss_number = fm.findFieldByName('cmiss_number')

        node_points = self._scene.createGraphicsPoints()
        node_points.setFieldDomainType(Field.DOMAIN_TYPE_NODES)
        node_points.setCoordinateField(self._coordinate_field)
        point_attr = node_points.getGraphicspointattributes()
        point_attr.setBaseSize([500, 500, 500])
        point_attr.setGlyphShapeType(Glyph.SHAPE_TYPE_SPHERE)
        node_points.setMaterial(self._material_module.findMaterialByName('white'))
        node_points.setName('display_node_points')

        node_numbers = self._scene.createGraphicsPoints()
        node_numbers.setFieldDomainType(Field.DOMAIN_TYPE_NODES)
        node_numbers.setCoordinateField(self._coordinate_field)
        point_attr = node_numbers.getGraphicspointattributes()
        point_attr.setLabelField(cmiss_number)
        point_attr.setGlyphShapeType(Glyph.SHAPE_TYPE_NONE)
        node_numbers.setMaterial(self._material_module.findMaterialByName('green'))
        node_numbers.setName('display_node_numbers')

        node_derivative_fields = [
            fm.createFieldNodeValue(self._coordinate_field, Node.VALUE_LABEL_D_DS1, 1),
            fm.createFieldNodeValue(self._coordinate_field, Node.VALUE_LABEL_D_DS2, 1),
            fm.createFieldNodeValue(self._coordinate_field, Node.VALUE_LABEL_D_DS3, 1),
            fm.createFieldNodeValue(self._coordinate_field, Node.VALUE_LABEL_D2_DS1DS2, 1),
            fm.createFieldNodeValue(self._coordinate_field, Node.VALUE_LABEL_D2_DS1DS3, 1),
            fm.createFieldNodeValue(self._coordinate_field, Node.VALUE_LABEL_D2_DS2DS3, 1),
            fm.createFieldNodeValue(self._coordinate_field, Node.VALUE_LABEL_D3_DS1DS2DS3, 1)
        ]

        node_derivative_material_names = ['gold', 'silver', 'green', 'cyan', 'magenta', 'yellow', 'blue']
        derivative_scales = [1.0, 1.0, 1.0, 0.5, 0.5, 0.5, 0.25]
        for i in range(len(self._node_derivative_labels)):
            node_derivative_label = self._node_derivative_labels[i]
            node_derivatives = self._scene.createGraphicsPoints()
            node_derivatives.setFieldDomainType(Field.DOMAIN_TYPE_NODES)
            node_derivatives.setCoordinateField(self._coordinate_field)
            point_attr = node_derivatives.getGraphicspointattributes()
            point_attr.setGlyphShapeType(Glyph.SHAPE_TYPE_ARROW_SOLID)
            point_attr.setOrientationScaleField(node_derivative_fields[i])
            point_attr.setBaseSize([0.0, 50, 50])
            point_attr.setScaleFactors([derivative_scales[i], 0.0, 0.0])
            material = self._material_module.findMaterialByName(node_derivative_material_names[i])
            node_derivatives.setMaterial(material)
            node_derivatives.setSelectedMaterial(material)
            node_derivatives.setName('display_node_derivatives' + node_derivative_label)
        fm.endChange()
        self._scene.endChange()
        return

    def _create_line_graphics(self):
        self._scene.beginChange()
        lines = self._scene.createGraphicsLines()
        fieldmodule = self._context.getMaterialmodule()
        lines.setCoordinateField(self._coordinate_field)
        lines.setName('display_lines')
        black = fieldmodule.findMaterialByName('white')
        lines.setMaterial(black)
        self._scene.endChange()
        return lines

    def create_scaffold_graphics(self):
        # self._create_node_graphics()
        self._create_line_graphics()
        self._create_surface_graphics()

    def _get_mesh(self):
        parent_region = self._region
        fm = parent_region.getFieldmodule()
        for dimension in range(3, 0, -1):
            mesh = fm.findMeshByDimension(dimension)
            if mesh.getSize() > 0:
                return mesh
        raise ValueError('Model contains no mesh')

    def get_model_coordinate_field(self):
        mesh = self._get_mesh()
        element = mesh.createElementiterator().next()
        if not element.isValid():
            raise ValueError('Model contains no elements')
        fm = self._region.getFieldmodule()
        cache = fm.createFieldcache()
        cache.setElement(element)
        field_iter = fm.createFielditerator()
        field = field_iter.next()
        while field.isValid():
            if field.isTypeCoordinate() and (field.getNumberOfComponents() <= 3):
                if field.isDefinedAtLocation(cache):
                    return field
            field = field_iter.next()
        raise ValueError('Could not determine model coordinate field')

    def _get_node_coordinates_range(self):
        fm = self._coordinate_field.getFieldmodule()
        fm.beginChange()
        nodes = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
        min_coordinates = fm.createFieldNodesetMinimum(self._coordinate_field, nodes)
        max_coordinates = fm.createFieldNodesetMaximum(self._coordinate_field, nodes)
        components_count = self._coordinate_field.getNumberOfComponents()
        cache = fm.createFieldcache()
        result, min_x = min_coordinates.evaluateReal(cache, components_count)
        result, max_x = max_coordinates.evaluateReal(cache, components_count)
        fm.endChange()
        return min_x, max_x

    def get_range(self):
        return self._get_node_coordinates_range()

    def get_scale(self):
        minimums, maximums = self._get_node_coordinates_range()
        return maths.sub(minimums, maximums)

    def get_coordinate_field(self):
        return self._coordinate_field

    def get_scaffold_options(self):
        return self._scaffold_options

    def initialise_scaffold(self):
        self._coordinate_field = self.get_model_coordinate_field()

    def _update(self):
        self._scene.beginChange()
        for name in ['display_lines', 'display_surfaces']:
            graphics = self._scene.findGraphicsByName(name)
            graphics.setCoordinateField(self._coordinate_field)
        self._scene.endChange()

    def get_scaffold_package(self):
        return self._scaffold_package

    def _get_scaffold_package_settings(self):
        return self._scaffold_package.getScaffoldSettings()

    def _get_scaffold_package_type(self):
        return self._scaffold_package.getScaffoldType()

    def get_edit_scaffold_settings(self):
        return self._scaffold_package.getScaffoldSettings()

    def get_edit_scaffold_option(self, key):
        # print(self.get_edit_scaffold_settings()[key])
        return self.get_edit_scaffold_settings()[key]

    def generate_mesh_for_fitting(self):
        scaffold_package = self._scaffold_package
        # if self._region:
        #     self._region.removeChild(self._region)
        # self._region = self._region.createChild('fitting_region')
        scaffold_package.getScaffoldType().generateMesh(self._region, self.get_edit_scaffold_settings())
        self._update()

    def _initialise_surface_material(self):
        self._material_module = self._context.getMaterialmodule()
        self._material_module.beginChange()

        solid_blue = self._material_module.createMaterial()
        solid_blue.setName('solid_blue')
        solid_blue.setManaged(True)
        solid_blue.setAttributeReal3(Material.ATTRIBUTE_AMBIENT, [0.0, 0.2, 0.6])
        solid_blue.setAttributeReal3(Material.ATTRIBUTE_DIFFUSE, [0.0, 0.7, 1.0])
        solid_blue.setAttributeReal3(Material.ATTRIBUTE_EMISSION, [0.0, 0.0, 0.0])
        solid_blue.setAttributeReal3(Material.ATTRIBUTE_SPECULAR, [0.1, 0.1, 0.1])
        solid_blue.setAttributeReal(Material.ATTRIBUTE_SHININESS, 0.2)
        trans_blue = self._material_module.createMaterial()

        trans_blue.setName('trans_blue')
        trans_blue.setManaged(True)
        trans_blue.setAttributeReal3(Material.ATTRIBUTE_AMBIENT, [0.0, 0.2, 0.6])
        trans_blue.setAttributeReal3(Material.ATTRIBUTE_DIFFUSE, [0.0, 0.7, 1.0])
        trans_blue.setAttributeReal3(Material.ATTRIBUTE_EMISSION, [0.0, 0.0, 0.0])
        trans_blue.setAttributeReal3(Material.ATTRIBUTE_SPECULAR, [0.1, 0.1, 0.1])
        trans_blue.setAttributeReal(Material.ATTRIBUTE_ALPHA, 0.3)
        trans_blue.setAttributeReal(Material.ATTRIBUTE_SHININESS, 0.2)
        glyph_module = self._context.getGlyphmodule()
        glyph_module.defineStandardGlyphs()

        self._material_module.defineStandardMaterials()
        solid_tissue = self._material_module.createMaterial()
        solid_tissue.setName('heart_tissue')
        solid_tissue.setManaged(True)
        solid_tissue.setAttributeReal3(Material.ATTRIBUTE_AMBIENT, [0.913, 0.541, 0.33])
        solid_tissue.setAttributeReal3(Material.ATTRIBUTE_EMISSION, [0.0, 0.0, 0.0])
        solid_tissue.setAttributeReal3(Material.ATTRIBUTE_SPECULAR, [0.2, 0.2, 0.3])
        solid_tissue.setAttributeReal(Material.ATTRIBUTE_ALPHA, 1.0)
        solid_tissue.setAttributeReal(Material.ATTRIBUTE_SHININESS, 0.6)

        self._material_module.endChange()

    def set_coordinate_field(self, field):
        if self._coordinate_field is not None:
            self._coordinate_field = None
        self._coordinate_field = field

    def set_scaffold_graphics_post_rotate(self, field):
        self._scene.beginChange()
        for name in ['display_lines', 'display_surfaces']:
            graphics = self._scene.findGraphicsByName(name)
            graphics.setCoordinateField(field)
        self._scene.endChange()
        self.set_coordinate_field(field)

    def transfer_temp_into_main(self, time):
        node_descriptions = _extract_node_descriptions(self._temp_region)
        if not self._scaffold_is_time_aware:
            self._undefine_scaffold_nodes()
            self._scaffold_is_time_aware = True
        _read_node_descriptions(self._region, node_descriptions, time)

    def generate_temp_mesh(self, fit_options_array=None):
        fit_options = {}
        if fit_options_array is not None:
            for index in range(len(self._parameters)):
                fit_options[self._parameters[index]] = fit_options_array[index]

        temp_options = self.get_scaffold_options().copy()
        temp_options.update(fit_options)
        self._temp_region = self._region.createRegion()
        self._scaffold.generateMesh(self._temp_region, temp_options)

    def set_scaffold_options(self, options):
        self._scaffold_options = options
        parameters = []
        for option in self._parameters:
            parameters.append(self._scaffold_options[option])
        self._scaffold_fit_parameters = parameters

    def initialise_scene(self):
        self._scene = self._region.getScene()

    def set_scaffold(self, scaffold):
        self._scaffold = scaffold

    def _undefine_scaffold_nodes(self):
        field_module = self._region.getFieldmodule()

        field_module.beginChange()
        node_set = field_module.findNodesetByName('nodes')
        node_template = node_set.createNodetemplate()
        node_template.undefineField(self._coordinate_field)
        node_iterator = node_set.createNodeiterator()
        node = node_iterator.next()
        while node.isValid():
            node.merge(node_template)
            node = node_iterator.next()

        field_module.endChange()

    def write_model(self, filename):
        self._region.writeFile(filename)


def _extract_node_descriptions(region):
    stream_information = region.createStreaminformationRegion()
    memory_resource = stream_information.createStreamresourceMemory()
    stream_information.setResourceDomainTypes(memory_resource, Field.DOMAIN_TYPE_NODES)
    region.write(stream_information)
    _, buffer_contents = memory_resource.getBuffer()
    return buffer_contents


def _read_node_descriptions(region, buffer, time):
    stream_information = region.createStreaminformationRegion()
    memory_resource = stream_information.createStreamresourceMemoryBuffer(buffer)
    stream_information.setResourceDomainTypes(memory_resource, Field.DOMAIN_TYPE_NODES)
    stream_information.setResourceAttributeReal(memory_resource, StreaminformationRegion.ATTRIBUTE_TIME, time)
    region.read(stream_information)


def _read_aligner_description(scaffold_region, scaffold_description):
    scaffold_stream_information = scaffold_region.createStreaminformationRegion()
    memory_resource = scaffold_stream_information.createStreamresourceMemoryBuffer(scaffold_description['elements3D'])
    scaffold_stream_information.setResourceDomainTypes(memory_resource, Field.DOMAIN_TYPE_MESH3D)
    memory_resource = scaffold_stream_information.createStreamresourceMemoryBuffer(scaffold_description['elements2D'])
    scaffold_stream_information.setResourceDomainTypes(memory_resource, Field.DOMAIN_TYPE_MESH2D)
    memory_resource = scaffold_stream_information.createStreamresourceMemoryBuffer(scaffold_description['elements1D'])
    scaffold_stream_information.setResourceDomainTypes(memory_resource, Field.DOMAIN_TYPE_MESH1D)
    memory_resource = scaffold_stream_information.createStreamresourceMemoryBuffer(scaffold_description['nodes'])
    scaffold_stream_information.setResourceDomainTypes(memory_resource, Field.DOMAIN_TYPE_NODES)
    return scaffold_stream_information
