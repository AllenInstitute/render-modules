import json
import logging
import os
from six.moves import urllib
import pytest
import numpy as np

import renderapi

from test_data import (render_params, 
                       cons_ex_tilespec_json, 
                       cons_ex_transform_json,
                       swap_z_tspecs1,
                       swap_z_tspecs2)
from rendermodules.module.render_module import RenderModuleException
from rendermodules.stack.consolidate_transforms import ConsolidateTransforms, process_z, consolidate_transforms
from rendermodules.stack import redirect_mipmaps, remap_zs, swap_zs

EPSILON = .001
render_params['project'] = "consolidate_test"

@pytest.fixture(scope='module')
def render():
    render = renderapi.connect(**render_params)
    return render

@pytest.fixture(scope='module')
def render_example_tilespec_and_transforms():
    tilespecs = [renderapi.tilespec.TileSpec(json=ts) for ts in cons_ex_tilespec_json]
    tforms = [renderapi.transform.load_transform_json(td) for td in cons_ex_transform_json]
    print(tforms)
    return (tilespecs, tforms)

@pytest.fixture(scope='module')
def source_tspecs():
    source_ts = [renderapi.tilespec.TileSpec(json=d)
                for d in swap_z_tspecs1]
    return source_ts

@pytest.fixture(scope='module')
def target_tspecs():
    target_ts = [renderapi.tilespec.TileSpec(json=d)
                for d in swap_z_tspecs2]
    return target_ts

@pytest.fixture(scope='module')
def source_stack(render, source_tspecs):
    source_stack_name = "source_stack"
    renderapi.stack.create_stack(source_stack_name, render=render)
    renderapi.client.import_tilespecs(source_stack_name, source_tspecs, render=render)
    renderapi.stack.set_stack_state(source_stack_name, 'COMPLETE', render=render)

    yield source_stack_name
    render.run(renderapi.stack.delete_stack, source_stack_name)

@pytest.fixture(scope='module')
def target_stack(render, target_tspecs):
    target_stack_name = "target_stack"
    renderapi.stack.create_stack(target_stack_name, render=render)
    renderapi.client.import_tilespecs(target_stack_name, target_tspecs, render=render)
    renderapi.stack.set_stack_state(target_stack_name, 'COMPLETE', render=render)

    yield target_stack_name
    render.run(renderapi.stack.delete_stack, target_stack_name)


@pytest.fixture(scope='module')
def test_stack(render,render_example_tilespec_and_transforms):
    (tilespecs, tforms) = render_example_tilespec_and_transforms
    new_affine = renderapi.transform.AffineModel(3.0,0.0,0.0,3.0,0,0)
    [ts.tforms.append(new_affine) for ts in tilespecs]
    stack = 'test_stack'
    renderapi.stack.create_stack(stack, render=render)
    renderapi.client.import_tilespecs('test_stack',tilespecs,tforms,render=render)
    yield stack
    renderapi.stack.delete_stack(stack, render=render)

#@pytest.fixture(scope='module')
def test_consolidate_module(render,test_stack):
    output_stack = test_stack + "_CONS"
    input_z = np.array(renderapi.stack.get_z_values_for_stack(test_stack,render=render))
    print(input_z)
    params = {
        "render":render_params,
        "stack": test_stack,
        "output_stack": output_stack,
        "transforms_slice" : "1:",
        "pool_size": 2,
        "minZ":input_z[1],
        "maxZ":np.max(input_z),
        "output_json":"test.json",
        "overwrite_zlayer": True
    }

    mod = ConsolidateTransforms(input_data = params,args=[])
    mod.run()

    output_z = np.array(renderapi.stack.get_z_values_for_stack(output_stack,render=render))
    assert(input_z[0] not in output_z)
    assert(len(output_z)==len(input_z)-1)

    #make sure the input_tilespecs are correct
    input_tilespecs = renderapi.tilespec.get_tile_specs_from_stack(test_stack, render=render)
    # 2lens correction, 2 affines
    assert all([len(ts.tforms)==4 for ts in input_tilespecs])

    #make sure the output_tilespecs have the right number of transforms
    output_tilespecs = renderapi.tilespec.get_tile_specs_from_stack(output_stack, render=render)
    #2 lens correction, 1 combined affine
    assert all([len(ts.tforms)==3 for ts in output_tilespecs])

    input_tilespec = renderapi.tilespec.get_tile_spec(test_stack,output_tilespecs[0].tileId, render=render)
    orig_tform = input_tilespec.tforms[2]
    cons_tform = output_tilespecs[0].tforms[2]
    expected_new=renderapi.transform.AffineModel(3.0,0,0,3.0,0,0).concatenate(orig_tform)
    print(input_tilespec.tforms)
    print(orig_tform.M)
    print(cons_tform.M)
    for orig_elem,new_elem in zip(np.ravel(expected_new.M),np.ravel(cons_tform.M)):
        assert(np.abs(orig_elem - new_elem)<EPSILON)

    return mod

# def test_consolidate_single(render,test_stack,test_consolidate_module):
#     input_z = np.array(renderapi.stack.get_z_values_for_stack(test_stack,render=render))
#     print input_z,type(input_z)
#     print len(input_z)
#     outputs=process_z(render,
#               test_consolidate_module.logger,
#               test_consolidate_module.args['stack'],
#               test_consolidate_module.args['output_stack'],
#               test_consolidate_module.args['transforms_slice'],
#               input_z[1])

def test_consolidate_transforms_function(render,test_stack):
    input_z = np.array(renderapi.stack.get_z_values_for_stack(test_stack,render=render))

    resolved_tiles = renderapi.resolvedtiles.get_resolved_tiles_from_z(
        test_stack, input_z[1], render=render)

    tile0 = resolved_tiles.tilespecs[0]
    new_tforms=consolidate_transforms(tile0.tforms, resolved_tiles.transforms)

    assert(len(new_tforms)==2)

    with pytest.raises(RenderModuleException) as e:
        new_tforms=consolidate_transforms(tile0.tforms)


def test_redirect_mipMapLevels(render, test_stack, tmpdir):
    output_stack = "redirect_mipmaps_test"
    out_fn = 'redirectmipmapsout.json'

    z = renderapi.stack.get_z_values_for_stack(test_stack, render=render)[0]
    input_d = dict(redirect_mipmaps.example_input, **{
        "input_stack": test_stack,
        "output_stack": output_stack,
        "render": render.DEFAULT_KWARGS,
        "z": z,
        "new_mipmap_directories": [{
            "level": 0,
            "directory": str(tmpdir)
        }]
    })

    mod = redirect_mipmaps.RedirectMipMapsModule(
        input_data=input_d, args=['--output_json', out_fn])
    mod.run()

    modified_tspecs = renderapi.tilespec.get_tile_specs_from_z(
        output_stack, z, render=render)

    assert all([os.path.abspath(urllib.parse.unquote(urllib.parse.urlparse(
        ts.ip[0].imageUrl).path)).startswith(
            os.path.abspath(str(tmpdir)))
                for ts in modified_tspecs])


@pytest.mark.parametrize("remap_sectionId", [True, False])
def test_remap_zs(render, test_stack, remap_sectionId):
    output_stack = "remap_zs_test"
    out_fn = "remapzsout.json"
    zValues = renderapi.stack.get_z_values_for_stack(test_stack, render=render)
    new_zValues = [z + 25 for z in zValues]
    input_d = dict(remap_zs.example_input, **{
        "input_stack": test_stack,
        "output_stack": output_stack,
        "zValues": zValues,
        "new_zValues": new_zValues,
        "remap_sectionId": remap_sectionId,
        "render": render.DEFAULT_KWARGS
    })

    in_tspecs = renderapi.tilespec.get_tile_specs_from_stack(
        test_stack, render=render)
    mod = remap_zs.RemapZsModule(
        input_data=input_d, args=['--output_json', out_fn])
    mod.run()

    out_tspecs = renderapi.tilespec.get_tile_specs_from_stack(
        output_stack, render=render)

    assert new_zValues == renderapi.stack.get_z_values_for_stack(
        output_stack, render=render)

    # tileIds should be preserved
    assert not ({ts.tileId for ts in in_tspecs} ^
                {ts.tileId for ts in out_tspecs})

    if remap_sectionId:
        # should be symmetric difference
        assert ({ts.layout.sectionId for ts in in_tspecs} ^
                {ts.layout.sectionId for ts in out_tspecs})

        assert ({ts.layout.sectionId for ts in out_tspecs} ==
                {mod.sectionId_from_z(ts.z) for ts in out_tspecs})
    else:
        assert ({ts.layout.sectionId for ts in in_tspecs} ==
                {ts.layout.sectionId for ts in out_tspecs})

def test_swap_z_module(render, source_stack, target_stack, source_tspecs, target_tspecs):
    ex = {
        "render": render_params,
        "source_stack": [source_stack],
        "target_stack": [target_stack],
        "zValues": [[1015]],
        "delete_source_stack": "False"
    }

    mod = swap_zs.SwapZsModule(input_data=ex, args=['--output_json', 'output.json'])
    mod.run()

    # assert that both the stack exist
    list_of_stacks = renderapi.render.get_stacks_by_owner_project(host=render.DEFAULT_HOST,
                                                                  port=render.DEFAULT_PORT,
                                                                  owner=render.DEFAULT_OWNER,
                                                                  project=render.DEFAULT_PROJECT,
                                                                  render=render)
    
    assert(source_stack in list_of_stacks and target_stack in list_of_stacks)

    source_tileids = [ts.tileId for ts in source_tspecs]
    target_tileids = [ts.tileId for ts in target_tspecs]

    tspecs1 = renderapi.stack.get_stack_tileIds(source_stack, render=render)
    tspecs2 = renderapi.stack.get_stack_tileIds(target_stack, render=render)

    assert(ts.tileId in target_tileids for ts in tspecs1)
    assert(ts.tileId in source_tileids for ts in tspecs2)

    ex['source_stack'] = [source_stack, target_stack]
    ex['target_stack'] = [target_stack]

    mod = swap_zs.SwapZsModule(input_data=ex, args=['--output_json', 'output.json'])
    
    with pytest.raises(RenderModuleException) as e:
        mod.run()
    
    ex['target_stack'] = [target_stack, source_stack]
    ex['zValues'] = [[1015], [1015]]

    mod = swap_zs.SwapZsModule(input_data=ex, args=['--output_json', 'output.json'])
    mod.run()

    assert(ts.tileId in source_tileids for ts in tspecs1)
    assert(ts.tileId in target_tileids for ts in tspecs2)