import json
import pytest
import renderapi
import os

from rendermodules.mesh_lens_correction.do_mesh_lens_correction import MeshLensCorrection
from rendermodules.mesh_lens_correction.LensPointMatches import generate_point_matches
from test_data import render_params, TEST_DATA_ROOT

example = {
  "render": {
     "host": "em-131snb1",
     "port": 8080,
     "owner": "gayathrim",
     "project": "lens_corr",
     "client_scripts": "/allen/aibs/pipeline/image_processing/volume_assembly/render-jars/production/scripts",
     "memGB": "2G"
  },
  "z_index": 100,
  "overwrite_zlayer": True,
  "input_stack": "raw_lens_stack",
  "close_stack": "True",
  "metafile": "/allen/aibs/pipeline/image_processing/volume_assembly/em_modules_test_data/mesh_lens_correction_2/mesh_lens_metafile_2.json",
  "match_collection": "raw_lens_matches",
  "nfeature_limit": 20000,
  "regularization": {
        "default_lambda": 1e5,
        "translation_factor": 1e-5,
        "lens_lambda": 1e-5
  },
  "output_stack": "lens_corrected_stack",
  "outfile": "/allen/aibs/pipeline/image_processing/volume_assembly/scratch/lens_out.json"
}

render_params['project'] = "mesh_lens_correction_test"


@pytest.fixture(scope='module')
def render():
    render = renderapi.connect(**render_params)
    return render


def test_mesh_lens_correction(render, tmpdir_factory):
    outdir = str(tmpdir_factory.mktemp("mesh_lens"))
    out_html_dir = outdir
    example['render'] = render_params
    example['metafile'] = os.path.join(TEST_DATA_ROOT,
                                       "em_modules_test_data",
                                       "mesh_lens_correction_2",
                                       "mesh_lens_metafile_2.json")
    example['output_dir'] = outdir
    example['out_html_dir'] = out_html_dir
    example['z_index'] = 100

    mod = MeshLensCorrection(
            input_data=example,
            args=['--output_json', 'mesh_lens_out.json'])
    mod.run()

    with open('mesh_lens_out.json', 'r') as f:
        js = json.load(f)

    with open(js['output_json'], 'r') as f:
        new_tform_dict = json.load(f)

    with open(js['qc_json'], 'r') as f:
        qc = json.load(f)

    assert(
            new_tform_dict['className'] ==
            "mpicbg.trakem2.transform.ThinPlateSplineTransform")

    # run again for code coverage
    mod.run()

    # more code coverage due,
    # code coverage software not detecting parallel processes

    generate_point_matches(mod.render,
                           mod.args['pairJson'],
                           mod.args['input_stack'],
                           mod.args['match_collection'],
                           mod.args['matchMax'])
