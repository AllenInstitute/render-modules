from argschema.fields import (Bool, Float, Int, Nested, Str, InputDir,
                              InputFile, OutputDir)
from argschema.schemas import DefaultSchema
import marshmallow as mm
import argschema
from marshmallow import  post_load
from rendermodules.module.schemas import (
    RenderParameters, FeatureExtractionParameters, FeatureRenderParameters,
    FeatureStorageParameters, MatchDerivationParameters,
    RenderParametersMatchWebServiceParameters, SparkOptions, SparkParameters,
    FeatureRenderClipParameters)


class TilePairClientOutputParameters(DefaultSchema):
    tile_pair_file = InputFile(required=True,description="location of json file with tile pair inputs")

class TilePairClientParameters(RenderParameters):
    stack = Str(
        required=True,
        description="input stack to which tilepairs need to be generated")
    baseStack = Str(
        required=False,
        default=None,
        missing=None,
        description="Base stack")
    minZ = Int(
        required=False,
        default=None,
        missing=None,
        description="z min for generating tilepairs")
    maxZ = Int(
        required=False,
        default=None,
        missing=None,
        description="z max for generating tilepairs")
    xyNeighborFactor = Float(
        required=False,
        default=0.9,
        description="Multiply this by max(width, height) of each tile to determine radius for locating neighbor tiles")
    zNeighborDistance = Int(
        required=False,
        default=2,
        missing=2,
        description="Look for neighbor tiles with z values less than or equal to this distance from the current tile's z value")
    excludeCornerNeighbors = Bool(
        required=False,
        default=True,
        missing=True,
        description="Exclude neighbor tiles whose center x and y is outside the source tile's x and y range respectively")
    excludeSameLayerNeighbors = Bool(
        required=False,
        default=False,
        missing=False,
        description="Exclude neighbor tiles in the same layer (z) as the source tile")
    excludeCompletelyObscuredTiles = Bool(
        required=False,
        default=True,
        missing=True,
        description="Exclude tiles that are completely obscured by reacquired tiles")
    output_dir = OutputDir(
        required=True,
        description="Output directory path to save the tilepair json file")
    memGB = Str(
        required=False,
        default='6G',
        missing='6G',
        description="Memory for the java client to run")

    @post_load
    def validate_data(self, data):
        if data['baseStack'] is None:
            data['baseStack'] = data['stack']



class SIFTPointMatchParameters(argschema.ArgSchema,
        FeatureExtractionParameters, FeatureRenderParameters,
        FeatureRenderClipParameters,
        FeatureStorageParameters, MatchDerivationParameters,
        RenderParametersMatchWebServiceParameters):
    pairJson = InputFile(required=True, description=(
        "JSON file where tile pairs are stored (.json, .gz, .zip)"))


class PointMatchClientParametersSpark(SparkParameters,
                                      SIFTPointMatchParameters):
    pass


class CollectionId(mm.Schema):
    owner = Str(required=True,
                description="owner of collection")
    name = Str(required=True,
                description="name of collection")

class PointMatchClientOutputSchema(mm.Schema):
    collectionId = Nested(CollectionId,
        required= True,
        description= "collection identifying details")
    pairCount = Int(
        required=True,
        description = "number of tile pairs in collection")

class PointMatchClientParametersQsub(
        RenderParameters, SIFTPointMatchParameters, SparkOptions):
    sparkhome = InputDir(
        required=True,
        default="/allen/aibs/pipeline/image_processing/volume_assembly/utils/spark",
        missing="/allen/aibs/pipeline/image_processing/volume_assembly/utils/spark",
        description="Path to the spark home directory")
    pbs_template = InputFile(
        required=True,
        description="pbs template to wrap spark job")
    no_nodes = Int(
        required=False,
        default=30,
        missing=10,
        description='Number of nodes to run the pbs job')
    ppn = Int(
        required=False,
        default=30,
        missing=30,
        description='Number of processors per node (default = 30)')
    queue_name = Str(
        required=False,
        default='connectome',
        missing='connectome',
        description='Name of the queue to submit the job')
    logdir = OutputDir(
        required=True,
        description="location to set logging for qsub command"
    )


class ExtractFeaturesParameters(argschema.ArgSchema, SparkParameters,
        FeatureExtractionParameters, FeatureRenderParameters,
        FeatureRenderClipParameters):
    rootFeatureDirectory = OutputDir(required=True, description="")
    pairJson = InputFile(required=True, description="")
    baseDataUrl = Str(required=True, description="")


class ExtractFeaturesOutput(DefaultSchema):
    pass
