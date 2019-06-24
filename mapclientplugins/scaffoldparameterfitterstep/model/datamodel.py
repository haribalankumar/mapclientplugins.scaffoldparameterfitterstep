from opencmiss.zinc.field import Field
from opencmiss.zinc.glyph import Glyph
from opencmiss.zinc.status import OK as ZINC_OK

from ..utils import maths


class DataModel(object):

    def __init__(self, context, region, material_module):

        self._context = context
        self._region = region
        self._material_module = material_module
        self._scene = None
        self._data_coordinate_field = None

    def _create_data_point_graphics(self, is_temporal):
        # self._timekeeper.setTime(0.0)
        points = self._scene.createGraphicsPoints()
        points.setFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
        points.setCoordinateField(self._data_coordinate_field)
        point_attr = points.getGraphicspointattributes()
        if is_temporal:
            point_size = self._get_auto_point_size()
            point_size = point_size / 0.5
            point_attr.setGlyphShapeType(Glyph.SHAPE_TYPE_SPHERE)
        else:
            point_size = self._get_auto_point_size()
            point_attr.setGlyphShapeType(Glyph.SHAPE_TYPE_CROSS)
        point_attr.setBaseSize(point_size)
        points.setMaterial(self._material_module.findMaterialByName('silver'))
        points.setName('display_points')

    def create_data_graphics(self, is_temporal):
        self._create_data_point_graphics(is_temporal)

    def get_coordinate_field(self):
        return self._data_coordinate_field

    def _get_data_range(self):
        fm = self._region.getFieldmodule()
        data_points = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
        minimums, maximums = self._get_nodeset_minimum_maximum(data_points, self._data_coordinate_field)
        return minimums, maximums

    def get_range(self):
        return self._get_data_range()

    def _get_auto_point_size(self):
        minimums, maximums = self._get_data_range()
        data_size = maths.magnitude(maths.sub(maximums, minimums))
        return 0.005 * data_size

    @staticmethod
    def _get_nodeset_minimum_maximum(nodeset, field):
        fm = field.getFieldmodule()
        count = field.getNumberOfComponents()
        minimums_field = fm.createFieldNodesetMinimum(field, nodeset)
        maximums_field = fm.createFieldNodesetMaximum(field, nodeset)
        cache = fm.createFieldcache()
        result, minimums = minimums_field.evaluateReal(cache, count)
        if result != ZINC_OK:
            minimums = None
        result, maximums = maximums_field.evaluateReal(cache, count)
        if result != ZINC_OK:
            maximums = None
        del minimums_field
        del maximums_field
        return minimums, maximums

    def get_scale(self):
        minimums, maximums = self._get_data_range()
        return maths.sub(minimums, maximums)

    def set_coordinate_field(self, field):
        if self._data_coordinate_field is not None:
            self._data_coordinate_field = None
        self._data_coordinate_field = field

    def set_scene(self, scene):
        self._scene = scene
