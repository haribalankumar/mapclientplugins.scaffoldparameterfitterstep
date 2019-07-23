from opencmiss.zinc.field import Field
from opencmiss.zinc.glyph import Glyph
from opencmiss.zinc.status import OK as ZINC_OK
from opencmiss.zinc.streamregion import StreaminformationRegion

from ..utils import maths


def _read_aligner_description(data_region, data_description, is_temporal):
    data_stream_information = data_region.createStreaminformationRegion()
    for key in data_description:
        if key != 'elements3D' and key != 'elements2D' and key != 'elements1D' and key != 'nodes':
            if is_temporal:
                if isinstance(key, float):
                    time = key
                else:
                    time = float(key)
                memory_resource = data_stream_information.createStreamresourceMemoryBuffer(data_description[key])
                data_stream_information.setResourceDomainTypes(memory_resource, Field.DOMAIN_TYPE_DATAPOINTS)
                data_stream_information.setResourceAttributeReal(memory_resource, StreaminformationRegion.ATTRIBUTE_TIME,
                                                                 time)
            else:
                memory_resource = data_stream_information.createStreamresourceMemoryBuffer(data_description[key])
                data_stream_information.setResourceDomainTypes(memory_resource, Field.DOMAIN_TYPE_DATAPOINTS)
    return data_stream_information


class DataModel(object):

    def __init__(self, context, region, data_description, material_module, is_temporal):

        self._context = context
        self._region = region
        self._sir = _read_aligner_description(self._region, data_description, is_temporal)

        self._material_module = material_module
        self._scene = None
        self._timekeeper = None
        self._current_time = None
        self._maximum_time = None
        self._time_sequence = None

        self._coordinate_field = None

    def _create_data_point_graphics(self, is_temporal):
        # self._timekeeper.setTime(0.0)
        points = self._scene.createGraphicsPoints()
        points.setFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
        points.setCoordinateField(self._coordinate_field)
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

    def get_data_coordinate_field(self):
        parent_region = self._region
        fm = parent_region.getFieldmodule()
        data_point_set = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
        data_point = data_point_set.createNodeiterator().next()
        if not data_point.isValid():
            raise ValueError('Data cloud is empty')
        cache = fm.createFieldcache()
        cache.setNode(data_point)
        field_iter = fm.createFielditerator()
        field = field_iter.next()
        while field.isValid():
            if field.isTypeCoordinate() and (field.getNumberOfComponents() <= 3):
                if field.isDefinedAtLocation(cache):
                    return field
            field = field_iter.next()
        raise ValueError('Could not determine data coordinate field')

    def get_coordinate_field(self):
        return self._coordinate_field

    def get_region(self):
        return self._region

    def set_time(self, time):
        self._current_time = time
        self._timekeeper.setTime(time)

    def _get_data_range(self, time=0):
        fm = self._region.getFieldmodule()
        data_points = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
        minimums, maximums = self._get_nodeset_minimum_maximum(data_points, self._coordinate_field, time=time)
        return minimums, maximums

    def get_range(self, time=0):
        return self._get_data_range(time=time)

    def _get_auto_point_size(self):
        minimums, maximums = self._get_data_range()
        data_size = maths.magnitude(maths.sub(maximums, minimums))
        return 0.005 * data_size

    @staticmethod
    def _get_nodeset_minimum_maximum(nodeset, field, time=0):
        fm = field.getFieldmodule()
        count = field.getNumberOfComponents()
        minimums_field = fm.createFieldNodesetMinimum(field, nodeset)
        maximums_field = fm.createFieldNodesetMaximum(field, nodeset)
        cache = fm.createFieldcache()
        cache.setTime(time)
        result, minimums = minimums_field.evaluateReal(cache, count)
        if result != ZINC_OK:
            minimums = None
        result, maximums = maximums_field.evaluateReal(cache, count)
        if result != ZINC_OK:
            maximums = None
        del minimums_field
        del maximums_field
        return minimums, maximums

    def get_scale(self, time):
        minimums, maximums = self._get_data_range(time)
        return maths.sub(minimums, maximums)

    def initialise_data(self):
        if self._coordinate_field is not None:
            self._coordinate_field = None
        result = self._region.read(self._sir)
        if result != ZINC_OK:
            raise ValueError('Failed to read and initialise data cloud.')
        self._coordinate_field = self.get_data_coordinate_field()

    def initialise_scene(self):
        self._scene = self._region.getScene()
        self._timekeeper = self._scene.getTimekeepermodule().getDefaultTimekeeper()

    def set_coordinate_field(self, field):
        if self._coordinate_field is not None:
            self._coordinate_field = None
        self._coordinate_field = field
