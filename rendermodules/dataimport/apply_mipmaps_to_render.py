#!/usr/bin/env python
import renderapi
from ..module.render_module import StackTransitionModule
from functools import partial
from six.moves import urllib
from rendermodules.dataimport.schemas import (
    AddMipMapsToStackParameters, AddMipMapsToStackOutput)

from rendermodules.utilities import uri_utils


if __name__ == "__main__" and __package__ is None:
    __package__ = "rendermodules.dataimport.apply_mipmaps_to_render"

example = {
    "render": {
        "host": "em-131fs",
        "port": 8998,
        "owner": "gayathri",
        "project": "MM2",
        "client_scripts": "/allen/programs/celltypes/workgroups/em-connectomics/gayathrim/nc-em2/Janelia_Pipeline/render_20170613/render-ws-java-client/src/main/scripts"
    },
    "input_stack": "mm2_acquire_8bit",
    "output_stack": "mm2_mipmap_test",
    "mipmap_dir": "/net/aidc-isi1-prd/scratch/aibs/scratch",
    "imgformat": "tif",
    "levels": 6,
    "zstart": 1015,
    "zend": 1015
}


def addMipMapsToRender(render, input_stack, mipmap_prefix, imgformat, levels, z):
    # tilespecPaths = []

    # tilespecs = render.run(renderapi.tilespec.get_tile_specs_from_z,
    #                        input_stack, z)
    resolvedtiles = render.run(
        renderapi.resolvedtiles.get_resolved_tiles_from_z,
        input_stack, z)

    for ts in resolvedtiles.tilespecs:
        mm1 = ts.ip[0]

        oldUrl = mm1.imageUrl
        filepath = urllib.parse.urlparse(oldUrl).path
        # filepath = urllib.parse.unquote(urllib.parse.urlparse(str(oldUrl)).path)

        # assumes that the mipmaps are stored in the way generated by the render's mipmap client
        # which adds the file extension in addition to the existing file extension from mipmap level 0
        if imgformat is "png":
            imgf = ".png"
        elif imgformat is "jpg":
            imgf = ".jpg"
        else:
            imgf = ".tif"

        for i in range(1, levels+1):
            # scUrl = 'file:' + os.path.join(
            #     mipmap_dir, str(i), filepath.lstrip(os.sep)) + imgf
            scUrl = uri_utils.uri_join(
                mipmap_prefix, str(i), "{}{}".format(
                    filepath.lstrip('/'), imgf))
            # print(scUrl)
            mm1 = renderapi.image_pyramid.MipMap(imageUrl=scUrl)
            ts.ip[i] = mm1
    return resolvedtiles
    # tilespecPaths.append(renderapi.utils.renderdump_temp(tilespecs))
    # return tilespecPaths


class AddMipMapsToStack(StackTransitionModule):
    default_schema = AddMipMapsToStackParameters
    default_output_schema = AddMipMapsToStackOutput

    def run(self):
        self.logger.debug('Applying mipmaps to stack')
        zvalues = self.get_overlapping_inputstack_zvalues()
        if len(zvalues) == 0:
            self.logger.error('No sections found for stack {}'.format(
                self.args['input_stack']))

        self.logger.debug("{}".format(zvalues))
        mypartial = partial(
            addMipMapsToRender, self.render, self.args['input_stack'],
            self.args['mipmap_prefix'], self.args['imgformat'],
            self.args['levels'])

        with renderapi.client.WithPool(self.args['pool_size']) as pool:
            #  tilespecs = [i for l in pool.map(mypartial, zvalues)
            #               for i in l]

            allresolved = pool.map(mypartial, zvalues)

        tilespecs = [i for l in (
            resolvedtiles.tilespecs for resolvedtiles in allresolved)
                     for i in l]
        identified_tforms = list({tform.transformId: tform for tform in (
            i for l in (resolvedtiles.transforms
                        for resolvedtiles in allresolved)
            for i in l)}.values())

        output_stack = (self.args['input_stack'] if
                        self.args['output_stack'] is None
                        else self.args['output_stack'])

        self.output_tilespecs_to_stack(tilespecs, output_stack,
                                       sharedTransforms=identified_tforms)

        missing_ts_zs = []
        for z in zvalues:
            job_success = self.validate_tilespecs(
                self.args['input_stack'], self.args['output_stack'], z)
            if not job_success:
                missing_ts_zs.append(z)
        self.output(
            {
                "output_stack": output_stack,
                "missing_tilespecs_zs": missing_ts_zs
            })


if __name__ == "__main__":
    # mod = AddMipMapsToStack(input_data=example)
    mod = AddMipMapsToStack(schema_type=AddMipMapsToStackParameters)
    mod.run()
