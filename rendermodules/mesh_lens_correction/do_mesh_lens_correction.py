import json
import renderapi
import tempfile
import numpy as np
import cv2
import os
from shutil import copyfile

from ..module.render_module import RenderModule

from .schemas \
        import MeshLensCorrectionSchema, DoMeshLensCorrectionOutputSchema
from rendermodules.dataimport.generate_EM_tilespecs_from_metafile \
        import GenerateEMTileSpecsModule
from rendermodules.pointmatch.create_tilepairs \
        import TilePairClientModule
from rendermodules.mesh_lens_correction.MeshAndSolveTransform \
        import MeshAndSolveTransform, approx_snap_contour
from rendermodules.em_montage_qc.detect_montage_defects \
        import DetectMontageDefectsModule
from rendermodules.pointmatch.generate_point_matches_opencv \
        import GeneratePointMatchesOpenCV
from rendermodules.pointmatch.schemas \
        import PointMatchOpenCVParameters

example = {
    "render": {
        "host": "em-131db.corp.alleninstitute.org",
        "port": 8080,
        "owner": "danielk",
        "project": "lens_corr",
        "client_scripts": "/allen/aibs/pipeline/image_processing/volume_assembly/render-jars/production/scripts",
        "memGB": "2G"
    },
    "regularization": {
        "default_lambda": 1e5,
        "translation_factor": 1e-5,
        "lens_lambda": 1e-5
    },
    "input_stack": "raw_lens_stack",
    "output_stack": "lens_corrected_stack",
    "overwrite_zlayer": True,
    "close_stack": True,
    "z_index": 100,
    "metafile": "/allen/programs/celltypes/workgroups/em-connectomics/danielk/em_lens_correction/test_data/_metadata_20180220175645_247488_8R_tape070A_05_20180220175645_reference_0_.json",
    "match_collection": "raw_lens_matches",
    "nfeature_limit": 20000,
    "output_dir": "/allen/programs/celltypes/workgroups/em-connectomics/danielk/tmp",
    "outfile": "lens_out.json",
    "output_json": "./mesh_lens_output.json",
    "mask_coords": [[0, 100], [100, 0], [3840, 0], [3840, 3840], [0, 3840]],
    "mask_dir": "/allen/programs/celltypes/workgroups/em-connectomics/danielk/masks_for_stacks"
}


def delete_matches_if_exist(render, owner, collection, sectionId):
    collections = renderapi.pointmatch.get_matchcollections(
            render=render,
            owner=owner)
    collection_names = [c['collectionId']['name'] for c in collections]
    if collection in collection_names:
        groupids = renderapi.pointmatch.get_match_groupIds(
                collection,
                render=render)
        if sectionId in groupids:
            renderapi.pointmatch.delete_point_matches_between_groups(
                    collection,
                    sectionId,
                    sectionId,
                    render=render)


def make_mask_from_coords(w, h, coords):
    cont = np.array(coords).astype('int32')
    cont = np.reshape(cont, (cont.shape[0], 1, cont.shape[1]))
    mask = np.zeros((h, w)).astype('uint8')
    mask = cv2.fillConvexPoly(mask, cont, color=255)
    return mask


def make_mask(args):
    maskUrl = None

    if args['mask_file'] is not None:
        # copy the provided file directly over
        maskUrl = os.path.join(
                args['mask_dir'],
                os.path.basename(args['mask_file']))
        copyfile(args['mask_file'], maskUrl)

    if (maskUrl is None) & (args['mask_coords'] is not None):
        # make the mask from the coordinates
        with open(args['metafile'], 'r') as f:
                metafile = json.load(f)
        mask = make_mask_from_coords(
                metafile[0]['metadata']['camera_info']['width'],
                metafile[0]['metadata']['camera_info']['height'],
                args['mask_coords'])

        def get_mask_url(i):
            mask_basename = os.path.basename(
                args['metafile'].replace(
                    '.json',
                    '_%d.png' % i))
            return os.path.join(
                    args['mask_dir'],
                    mask_basename)
        i = 0
        maskUrl = get_mask_url(i)
        while os.path.isfile(maskUrl):
            i += 1
            maskUrl = get_mask_url(i)
        cv2.imwrite(maskUrl, mask)

    return maskUrl


class MeshLensCorrection(RenderModule):
    default_schema = MeshLensCorrectionSchema
    default_output_schema = DoMeshLensCorrectionOutputSchema

    @staticmethod
    def get_sectionId_from_z(z):
        return str(float(z))

    @staticmethod
    def get_sectionId_from_metafile(metafile):
        j = json.load(open(metafile, 'r'))
        sectionId = j[0]['metadata']['grid']
        return sectionId

    def generate_ts_example(self, maskUrl):
        ex = {}
        ex['render'] = {}
        ex['render']['host'] = self.render.DEFAULT_HOST
        ex['render']['port'] = self.render.DEFAULT_PORT
        ex['render']['owner'] = self.render.DEFAULT_OWNER
        ex['render']['project'] = self.render.DEFAULT_PROJECT
        ex['render']['client_scripts'] = self.render.DEFAULT_CLIENT_SCRIPTS
        ex['metafile'] = self.args['metafile']
        ex['stack'] = self.args['input_stack']
        ex['overwrite_zlayer'] = self.args['overwrite_zlayer']
        ex['close_stack'] = self.args['close_stack']
        ex['output_stack'] = self.args['input_stack']
        ex['z'] = self.args['z_index']
        ex['sectionId'] = self.args['sectionId']
        ex['maskUrl'] = maskUrl
        return ex

    def generate_tilepair_example(self):
        ex = {}
        ex['render'] = {}
        ex['render']['host'] = self.render.DEFAULT_HOST
        ex['render']['port'] = self.render.DEFAULT_PORT
        ex['render']['owner'] = self.render.DEFAULT_OWNER
        ex['render']['project'] = self.render.DEFAULT_PROJECT
        ex['render']['client_scripts'] = self.render.DEFAULT_CLIENT_SCRIPTS
        ex['minZ'] = self.args['z_index']
        ex['maxZ'] = self.args['z_index']
        ex['zNeighborDistance'] = 0
        ex['stack'] = self.args['input_stack']
        ex['xyNeighborFactor'] = 0.1
        ex['excludeCornerNeighbors'] = False
        ex['excludeSameLayerNeighbors'] = False
        ex['excludeCompletelyObscuredTiles'] = True
        ex['output_dir'] = self.args['output_dir']

        ex['outfile'] = self.args['outfile']
        return ex

    def get_qc_example(self):
        ex = {}
        ex['render'] = {}
        ex['render']['host'] = self.render.DEFAULT_HOST
        ex['render']['port'] = self.render.DEFAULT_PORT
        ex['render']['owner'] = self.render.DEFAULT_OWNER
        ex['render']['project'] = self.render.DEFAULT_PROJECT
        ex['render']['client_scripts'] = self.render.DEFAULT_CLIENT_SCRIPTS
        ex['match_collection'] = self.args['match_collection']
        ex['prestitched_stack'] = self.args['input_stack']
        ex['poststitched_stack'] = self.args['output_stack']
        ex['out_html_dir'] = self.args['output_dir']
        ex['minZ'] = self.args['z_index']
        ex['maxZ'] = self.args['z_index']
        return ex

    def get_pm_args(self):
        args_for_pm = dict(self.args)
        args_for_pm['render'] = self.args['render']
        args_for_pm['pairJson'] = self.args['pairJson']
        args_for_pm['input_stack'] = self.args['input_stack']
        args_for_pm['match_collection'] = self.args['match_collection']
        return args_for_pm

    def run(self):
        self.args['sectionId'] = self.get_sectionId_from_metafile(
                self.args['metafile'])

        if self.args['output_dir'] is None:
            self.args['output_dir'] = tempfile.mkdtemp()

        if self.args['outfile'] is None:
            outfile = tempfile.NamedTemporaryFile(suffix=".json",
                                                  delete=False,
                                                  dir=self.args['output_dir'])
            outfile.close()
            self.args['outfile'] = outfile.name

        out_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        out_file.close()

        args_for_input = dict(self.args)

        self.maskUrl = make_mask(args_for_input)
        # argshema doesn't like the NumpyArray after processing it once
        # we don't need it after mask creation
        self.args['mask_coords'] = None
        args_for_input['mask_coords'] = None

        # create a stack with the lens correction tiles
        ts_example = self.generate_ts_example(self.maskUrl)
        mod = GenerateEMTileSpecsModule(input_data=ts_example,
                                        args=['--output_json', out_file.name])
        mod.run()

        # generate tile pairs for this section in the input stack
        tp_example = self.generate_tilepair_example()
        tp_mod = TilePairClientModule(input_data=tp_example,
                                      args=['--output_json', out_file.name])
        tp_mod.run()

        with open(tp_mod.args['output_json'], 'r') as f:
            js = json.load(f)
        self.args['pairJson'] = js['tile_pair_file']

        self.logger.setLevel(self.args['log_level'])

        if self.args['rerun_pointmatch']:
            delete_matches_if_exist(
                    self.render,
                    self.args['render']['owner'],
                    self.args['match_collection'],
                    self.args['sectionId'])

            args_for_pm = self.get_pm_args()
            pmgen = GeneratePointMatchesOpenCV(
                    input_data=args_for_pm,
                    args=['--output_json', out_file.name])
            pmgen.run()

        self.logger.setLevel(self.args['log_level'])

        meshclass = MeshAndSolveTransform(
                input_data=args_for_input,
                args=['--output_json', out_file.name])
        # find the lens correction, write out to new stack
        meshclass.run()

        # run montage qc on the new stack
        qc_example = self.get_qc_example()
        qc_mod = DetectMontageDefectsModule(
                input_data=qc_example,
                args=['--output_json', out_file.name])
        qc_mod.run()

        try:
            self.output(
                    {'output_json': meshclass.args['outfile'],
                     'qc_json': out_file.name})
        except AttributeError as e:
            self.logger.error(e)


if __name__ == "__main__":
    mod = MeshLensCorrection(input_data=example)
    mod.run()
