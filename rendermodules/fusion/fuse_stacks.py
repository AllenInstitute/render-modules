#!/usr/bin/env python
'''
fuse overlapping render stacks registered by an Affine Homography transform
    similar to Parallel Elastic Alignment
'''
import copy
import os

import renderapi
from ..module.render_module import RenderModule
from .schemas import FuseStacksParameters, FuseStacksOutput

example_parameters = {
    "render": {
        "host": "em-131fs",
        "port": 8080,
        "owner": "testuser",
        "project": "test",
        "client_scripts": ""
    },
    "stacks": {
        "stack": "PARENTSTACK",
        "transform": {
            "className": "mpicbg.trakem2.transform.AffineModel2D",
            "dataString": "1.0 0.0 0.0 1.0 0.0 0.0",
            "type": "leaf"},
        "children": [{"stack": "CHILDSTACK1",
                      "transform": {
                          "className": "mpicbg.trakem2.transform.AffineModel2D",
                          "dataString": "1.0 0.0 0.0 1.0 0.0 0.0",
                          "type": "leaf"},
                      "children": [{"stack": "CHILDSTACK2",
                                    "transform": {
                                        "className": "mpicbg.trakem2.transform.AffineModel2D",
                                        "dataString": "1.0 0.0 0.0 1.0 0.0 0.0",
                                        "type": "leaf"},
                                    "children": []}]}]},
    "pool_size": 12,
    "interpolate_transforms": True,  # False is notimplemented
    "output_stack": "FUSEDOUTSTACK"
}


class FuseStacksModule(RenderModule):
    default_schema = FuseStacksParameters
    default_output_schema = FuseStacksOutput

    def fusetoparent(self, parent, child, transform=None):
        transform = (renderapi.transform.AffineModel()
                     if transform is None else transform)
        parent = child if parent is None else parent

        # get overlapping zs
        parent_zs = set(self.render.run(
            renderapi.stack.get_z_values_for_stack, parent))
        child_zs = set(self.render.run(
            renderapi.stack.get_z_values_for_stack, child))
        z_intersection = sorted(parent_zs.intersection(child_zs))

        # can check order relation of child/parent stack
        positive = max(child_zs) > z_intersection[-1]
        self.logger.debug("positive concatenation? {}".format(positive))

        # generate jsonfiles representing interpolated overlapping tiles
        jsonfiles = []
        for i, z in enumerate((
                z_intersection if positive else z_intersection[::-1])):
            section_tiles = []
            lambda_ = float(i / float(len(z_intersection)))

            atiles = {ts.tileId: ts for ts
                      in renderapi.tilespec.get_tile_specs_from_z(
                          parent, z, render=self.render)}
            btiles = {ts.tileId: ts for ts
                      in renderapi.tilespec.get_tile_specs_from_z(
                          child, z, render=self.render)}
            # generate interpolated tiles for intersection of set of tiles
            for tileId in atiles.viewkeys() & btiles.viewkeys():
                a = atiles[tileId]
                interp_tile = copy.copy(a)
                b = btiles[tileId]
                b.tforms.append(transform)

                interp_tile.tforms = [
                    renderapi.transform.InterpolatedTransform(
                        a=renderapi.transform.TransformList(a.tforms),
                        b=renderapi.transform.TransformList(b.tforms),
                        lambda_=lambda_)]
                section_tiles.append(interp_tile)
            jsonfiles.append(renderapi.utils.renderdump_temp(section_tiles))
        return jsonfiles

    def fuse_graph(self, node, parentstack=None, inputtransform=None):
        inputtransform = (renderapi.transform.AffineModel()
                          if inputtransform is None else inputtransform)
        node_edge = (renderapi.transform.AffineModel()
                     if node.get('transform') is None
                     else renderapi.transform.load_transform_json(
                         node['transform']))
        # concatenate edge and input transform -- expected to work for Aff Hom
        node_tform = node_edge.concatenate(inputtransform)

        # generate and upload interpolated tiles
        jfiles = self.fusetoparent(
            parentstack, node['stack'], transform=node_tform)
        renderapi.stack.create_stack(
            self.args['output_stack'], render=self.render)
        renderapi.client.import_jsonfiles_parallel(
            self.args['output_stack'], jfiles,
            pool_size=self.args['pool_size'],
            close_stack=False, render=self.render)

        # clean up temporary files
        for jfile in jfiles:
            os.remove(jfile)

        # recurse through depth of graph
        for child in node['children']:
            self.fuse_graph(
                child, parentstack=node['stack'], inputtransform=node_tform)

    def run(self):
        self.fuse_graph(self.args['stacks'])
        d = {'stack': self.args['output_stack']}
        self.output(d)


if __name__ == "__main__":
    mod = FuseStacksModule(input_data=example_parameters)
    mod.run()