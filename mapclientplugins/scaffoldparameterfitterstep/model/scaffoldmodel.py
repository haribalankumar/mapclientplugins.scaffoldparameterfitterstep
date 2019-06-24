from opencmiss.zinc.field import Field
from opencmiss.zinc.graphics import Graphics
from opencmiss.zinc.material import Material

from ..utils import maths


class ScaffoldModel(object):

    def __init__(self, context, region, material_module):

        self._context = context
        self._region = region
        self._material_module = material_module

        self._scene = None
        self._scaffold_coordinate_field = None
        self._initialise_surface_material()

    def _create_surface_graphics(self):
        surface = self._scene.createGraphicsSurfaces()
        surface.setCoordinateField(self._scaffold_coordinate_field)
        surface.setRenderPolygonMode(Graphics.RENDER_POLYGON_MODE_SHADED)
        surface_material = self._material_module.findMaterialByName('trans_blue')
        surface.setMaterial(surface_material)
        surface.setName('display_surfaces')
        return surface

    def _create_line_graphics(self):
        lines = self._scene.createGraphicsLines()
        fieldmodule = self._context.getMaterialmodule()
        lines.setCoordinateField(self._scaffold_coordinate_field)
        lines.setName('display_lines')
        black = fieldmodule.findMaterialByName('white')
        lines.setMaterial(black)
        return lines

    def create_scaffold_graphics(self):
        self._create_line_graphics()
        self._create_surface_graphics()

    def _get_node_coordinates_range(self):
        fm = self._scaffold_coordinate_field.getFieldmodule()
        fm.beginChange()
        nodes = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
        min_coordinates = fm.createFieldNodesetMinimum(self._scaffold_coordinate_field, nodes)
        max_coordinates = fm.createFieldNodesetMaximum(self._scaffold_coordinate_field, nodes)
        components_count = self._scaffold_coordinate_field.getNumberOfComponents()
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
        return self._scaffold_coordinate_field

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
        if self._scaffold_coordinate_field is not None:
            self._scaffold_coordinate_field = None
        self._scaffold_coordinate_field = field

    def set_scaffold_graphics_post_rotate(self, field):
        self._scene.beginChange()
        for name in ['display_lines', 'display_surfaces']:
            graphics = self._scene.findGraphicsByName(name)
            graphics.setCoordinateField(field)
        self._scene.endChange()
        self.set_coordinate_field(field)

    def set_scene(self, scene):
        self._scene = scene

    def write_model(self, filename):
        self._region.writeFile(filename)
