from opencmiss.zinc.field import Field
from opencmiss.zinc.graphics import Graphics
from opencmiss.zinc.material import Material
from opencmiss.zinc.streamregion import StreaminformationRegion
from opencmiss.utils.zinc import create_finite_element_field

from ..utils import maths


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


class ScaffoldModel(object):

    def __init__(self, context, region, coordinates, material_module, parameters):

        self._context = context
        self._parent_region = region
        self._region = region
        self._coordinate_field = None
        self._material_module = material_module
        self._parameters = parameters.keys()

        # self._sir = _read_aligner_description(self._region, scaffold_description)

        self._scaffold = None
        self._scaffold_options = None
        self._temp_region = None
        self._scene = None
        self._scaffold_is_time_aware = None
        self._scaffold_fit_parameters = None
        self._initialise_surface_material()

    # def initialise_region(self):
    #     self.clear()
        # if self._region is not None:
        #     self._region = None
        # if self._coordinate_field is not None:
            # self._coordinate_field = None
        # self._region = self._parent_region.createChild('scaffold_region')
        # self._coordinate_field = create_finite_element_field(self._region)

    # def clear(self):
    #     if self._region:
    #         self._parent_region.removeChild(self._region)

    def get_region(self):
        return self._region

    def _create_surface_graphics(self):
        surface = self._scene.createGraphicsSurfaces()
        surface.setCoordinateField(self._coordinate_field)
        surface.setRenderPolygonMode(Graphics.RENDER_POLYGON_MODE_SHADED)
        surface_material = self._material_module.findMaterialByName('trans_blue')
        surface.setMaterial(surface_material)
        surface.setName('display_surfaces')
        return surface

    def _create_line_graphics(self):
        lines = self._scene.createGraphicsLines()
        fieldmodule = self._context.getMaterialmodule()
        lines.setCoordinateField(self._coordinate_field)
        lines.setName('display_lines')
        black = fieldmodule.findMaterialByName('white')
        lines.setMaterial(black)
        return lines

    def create_scaffold_graphics(self):
        self._create_line_graphics()
        self._create_surface_graphics()

    def _get_mesh(self):
        fm = self._region.getFieldmodule()
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

    # def _generate_mesh(self, options):
    #     self.initialise_region()
    #     field_module = self._region.getFieldmodule()
    #     field_module.beginChange()
    #     self._scaffold.generateMesh(self._region, options)
    #     field_module.defineAllFaces()
    #     field_module.endChange()

    def set_scaffold_options(self, options):
        self._scaffold_options = options
        parameters = []
        for option in self._parameters:
            parameters.append(self._scaffold_options[option])
        self._scaffold_fit_parameters = parameters

    def initialise_scene(self):
        if self._region.getScene():
            self._region.getScene().removeAllGraphics()
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
