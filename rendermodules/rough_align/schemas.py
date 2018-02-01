from argschema import InputFile, InputDir
import marshmallow as mm
from argschema.fields import Bool, Float, Int, Nested, Str, InputFile
from argschema.schemas import DefaultSchema
from ..module.schemas import RenderParameters
from marshmallow import validates_schema, post_load, ValidationError
import argschema




class ApplyRoughAlignmentTransformParameters(RenderParameters):
    montage_stack = mm.fields.Str(
        required=True,
        metadata={'description':'stack to make a downsample version of'})
    prealigned_stack = mm.fields.Str(
        required=False,
        default=None,
        missing=None,
        metadata={'description':'stack with dropped tiles corrected for stitching errors'})
    lowres_stack = mm.fields.Str(
        required=True,
        metadata={'description':'montage scape stack with rough aligned transform'})
    output_stack = mm.fields.Str(
        required=True,
        metadata={'description':'output high resolution rough aligned stack'})
    tilespec_directory = mm.fields.Str(
        required=True,
        metadata={'description':'path to save section images'})
    set_new_z = mm.fields.Boolean(
        required=False,
        default=False,
        missing=False,
        metadata={'description':'set to assign new z values starting from 0 (default - False)'})
    consolidate_transforms = mm.fields.Boolean(
        required=False,
        default=True,
        missing=True,
        metadata={'description':'should the transforms be consolidated? (default - True)'})
    scale = mm.fields.Float(
        required=True,
        metadata={'description':'scale of montage scapes'})
    pool_size = mm.fields.Int(
        require=False,
        default=10,
        missing=10,
        metadata={'description':'pool size for parallel processing'})
    minZ = mm.fields.Int(
        required=True,
        metadata={'description':'Minimum Z value'})
    maxZ = mm.fields.Int(
        required=True,
        metadata={'description':'Maximum Z value'})

    @post_load
    def validate_data(self, data):
        if data['prealigned_stack'] is None:
            data['prealigned_stack'] = data['montage_stack']


class LowresStackParameters(DefaultSchema):
    stack = Str(
        required=True,
        description="Input downsample images section stack")
    owner = Str(
        required=False,
        default=None,
        missing=None,
        description="Owner of the input lowres stack")
    project = Str(
        required=False,
        default=None,
        missing=None,
        description="Project of the input lowres stack")
    service_host = Str(
        required=False,
        default=None,
        missing=None,
        description="Service host for the input stack Render service")
    baseURL = Str(
        required=False,
        default=None,
        missing=None,
        description="Base URL of the Render service for the source stack")
    renderbinPath = Str(
        required=False,
        default=None,
        missing=None,
        description="Client scripts location")
    verbose = Int(
        required=False,
        default=0,
        missing=0,
        description="Want the output to be verbose?")


class OutputLowresStackParameters(DefaultSchema):
    stack = Str(
        required=True,
        description="Input downsample images section stack")
    owner = Str(
        required=False,
        default=None,
        missing=None,
        description="Owner of the input lowres stack")
    project = Str(
        required=False,
        default=None,
        missing=None,
        description="Project of the input lowres stack")
    service_host = Str(
        required=False,
        default=None,
        missing=None,
        description="Service host for the input stack Render service")
    baseURL = Str(
        required=False,
        default=None,
        missing=None,
        description="Base URL of the Render service for the source stack")
    renderbinPath = Str(
        required=False,
        default=None,
        missing=None,
        description="Client scripts location")
    verbose = Int(
        required=False,
        default=0,
        missing=0,
        description="Want the output to be verbose?")


class PointMatchCollectionParameters(DefaultSchema):
    owner = Str(
        required=False,
        default=None,
        missing=None,
        description="Point match collection owner (defaults to render owner")
    match_collection = Str(
        required=True,
        description="Point match collection name")
    server = Str(
        required=False,
        default=None,
        missing=None,
        description="baseURL of the Render service holding the point match collection")
    verbose = Int(
        required=False,
        default=0,
        missing=0,
        description="Verbose output flag")


class PointMatchParameters(DefaultSchema):
    NumRandomSamplingsMethod = Str(
        required=False,
        default="Desired confidence",
        missing="Desired confidence",
        description='Numerical Random sampling method')
    MaximumRandomSamples = Int(
        required=False,
        default=5000,
        missing=5000,
        description='Maximum number of random samples')
    DesiredConfidence = Float(
        required=False,
        default=99.9,
        missing=99.9,
        description='Desired confidence level')
    PixelDistanceThreshold = Float(
        required=False,
        default=0.1,
        missing=0.1,
        description='Pixel distance threshold for filtering')
    Transform = Str(
        required=False,
        default="AFFINE",
        missing="AFFINE",
        description='Transformation type parameter for point match filtering (default AFFINE)')


class PastixParameters(DefaultSchema):
    ncpus = Int(
        required=False,
        default=8,
        missing=8,
        allow_none=True,
        description="No. of cpu cores. Default = 8")
    parms_fn = InputFile(
        required=False,
        default=None,
        missing=None,
        description="Path to parameters pastix parameters file")
    split = Int(
        required=False,
        default=1,
        missing=1,
        allow_none=True,
        description="set to either 0 (no split) or 1 (split)")


class SolverParameters(DefaultSchema):
    # NOTE: Khaled's EM_aligner needs some of the boolean variables as Integers
    # Hence providing the input as Integers
    degree = Int(
        required=True,
        default=1,
        description="Degree of transformation 1 - affine, 2 - second order polynomial, maximum is 3")
    solver = Str(
        required=False,
        default='backslash',
        missing='backslash',
        description="Solver type - default is backslash")
    transfac = Float(
        required=False,
        default=1e-15,
        missing=1e-15,
        description='Translational factor')
    lambda_value = Float(
        required=True,
        description="regularization parameter")
    edge_lambda = Float(
        required=True,
        description="edge lambda regularization parameter")
    nbrs = Int(
        required=False,
        default=3,
        missing=3,
        description="No. of neighbors")
    nbrs_step = Int(
        required=False,
        default=1,
        missing=1,
        description="Step value to increment the # of neighbors")
    xs_weight = Float(
        required=True,
        description="Weight ratio for cross section point matches")
    min_points = Int(
        required=True,
        default=8,
        description="Minimum no. of point matches per tile pair defaults to 8")
    max_points = Int(
        required=True,
        default=100,
        description="Maximum no. of point matches")
    filter_point_matches = Int(
        required=False,
        default=1,
        missing=1,
        description='set to a value 1 if point matches must be filtered')
    outlier_lambda = Float(
        required=True,
        default=100,
        description="Outlier lambda - large numbers result in fewer tiles excluded")
    min_tiles = Int(
        required=False,
        default=2,
        missing=2,
        description="minimum number of tiles")
    Width = Int(
        required=False,
        default=3840,
        missing=3840,
        description='Width of the tiles (default = 3840)')
    Height = Int(
        required=False,
        default=3840,
        missing=3840,
        description='Height of the tiles (default= 3840)')
    outside_group = Int(
        required=False,
        default=0,
        missing=0,
        description='Outside group parameter (default = 0)')
    matrix_only = Int(
        required=False,
        default=0,
        missing=0,
        description="0 - solve (default), 1 - only generate the matrix. For debugging only")
    distribute_A = Int(
        required=False,
        default=1,
        missing=1,
        description="Shards of A matrix")
    dir_scratch = InputDir(
        required=True,
        description="Scratch directory")
    distributed = Int(
        required=False,
        default=0,
        missing=0,
        description="distributed or not?")
    disableValidation = Int(
        required=False,
        default=1,
        missing=1,
        description="Disable validation while ingesting tiles?")
    use_peg = Int(
        required=False,
        default=0,
        missing=0,
        description="use pegs or not")
    complete = Int(
        required=False,
        default=0,
        missing=0,
        description="Set stack state to complete after processing?")
    verbose = Int(
        required=False,
        default=0,
        missing=0,
        description="want verbose output?")
    debug = Int(
        required=False,
        default=0,
        missing=0,
        description="Debug mode?")
    constrain_by_z = Int(
        required=False,
        default=0,
        missing=0,
        description='Contrain by z')
    sandwich = Int(
        required=False,
        default=0,
        missing=0,
        description='Sandwich parameter for solver')
    constraint_fac = Float(
        required=False,
        default=1e+15,
        missing=1e+15,
        description='Constraint factor')
    pmopts = Nested(
        PointMatchParameters,
        required=True,
        description='Point match filtering parameters')
    pastix = Nested(
        PastixParameters,
        required=False,
        default=None,
        missing=None,
        description="Pastix parameters if solving using Pastix")


class SolveRoughAlignmentParameters(RenderParameters):
    first_section = Int(
        required=True,
        description="Min Z value")
    last_section = Int(
        required=True,
        description="Max Z value")
    verbose = Int(
        required=False,
        default=0,
        missing=0,
        description='Is verbose output required')
    source_collection = Nested(
        LowresStackParameters,
        required=True)
    target_collection = Nested(
        OutputLowresStackParameters,
        required=True)
    solver_options = Nested(
        SolverParameters,
        required=True)
    source_point_match_collection = Nested(
        PointMatchCollectionParameters,
        required=True)
    solver_executable = Str(
        required=True,
        description="Rough alignment solver executable file with full path")
    

    @post_load
    def add_missing_values(self, data):
        # cannot create "lambda" as a variable name in SolverParameters. So, adding it here
        data['solver_options']['lambda'] = data['solver_options']['lambda_value']
        data['solver_options'].pop('lambda_value', None)
        if data['solver_options']['pastix'] is None:
            data['solver_options'].pop('pastix', None)

        host = ""
        if data['render']['host'].find('http://') == 0:
            host = data['render']['host']
        else:
            host = "http://%s"%(data['render']['host'])

        if data['source_collection']['owner'] is None:
            data['source_collection']['owner'] = data['render']['owner']
        if data['source_collection']['project'] is None:
            data['source_collection']['project'] = data['render']['project']
        if data['source_collection']['service_host'] is None:
            if data['render']['host'].find('http://') == 0:
                data['source_collection']['service_host'] = data['render']['host'][7:] + ":" + str(data['render']['port'])
            else:
                data['source_collection']['service_host'] = data['render']['host'] + ":" + str(data['render']['port'])
        if data['source_collection']['baseURL'] is None:
            data['source_collection']['baseURL'] = host + ":" + str(data['render']['port']) + '/render-ws/v1'
        if data['source_collection']['renderbinPath'] is None:
            data['source_collection']['renderbinPath'] = data['render']['client_scripts']

        if data['target_collection']['owner'] is None:
            data['target_collection']['owner'] = data['render']['owner']
        if data['target_collection']['project'] is None:
            data['target_collection']['project'] = data['render']['project']
        if data['target_collection']['service_host'] is None:
            if data['render']['host'].find('http://') == 0:
                data['target_collection']['service_host'] = data['render']['host'][7:] + ":" + str(data['render']['port'])
            else:
                data['target_collection']['service_host'] = data['render']['host'] + ":" + str(data['render']['port'])
        if data['target_collection']['baseURL'] is None:
            data['target_collection']['baseURL'] = host + ":" + str(data['render']['port']) + '/render-ws/v1'
        if data['target_collection']['renderbinPath'] is None:
            data['target_collection']['renderbinPath'] = data['render']['client_scripts']

        if data['source_point_match_collection']['server'] is None:
            data['source_point_match_collection']['server'] = data['source_collection']['baseURL']
        if data['source_point_match_collection']['owner'] is None:
            data['source_point_match_collection']['owner'] = data['render']['owner']

        # if solver is "pastix" then data['solver_options']['pastix'] is required
        if data['solver_options']['solver'] is "pastix":
            pastix = data['solver_options']['pastix']
            if pastix['ncpus'] is None:
                data['solver_options']['pastix']['ncpus'] = 8
            if pastix['split'] is None:
                data['solver_options']['pastix']['split'] = 1