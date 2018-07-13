if __name__ == "__main__" and __package__ is None:
    __package__ = "rendermodules.intensity_correction.calculate_multiplicative_correction"
import os
import renderapi
from functools import partial
import numpy as np
import tifffile
from scipy.ndimage.filters import gaussian_filter
from rendermodules.intensity_correction.apply_multiplicative_correction import getImage
from rendermodules.intensity_correction.schemas import MakeMedianParams
from rendermodules.module.render_module import RenderModule

example_input = {
    "render": {
        "host": "ibs-forrestc-ux1",
        "port": 8080,
        "owner": "M246930_Scnn1a",
        "project": "M246930_Scnn1a_4",
        "client_scripts": "/var/www/render/render-ws-java-client/src/main/scripts"
    },
    "input_stack": "Acquisition_DAPI_1",
    "file_prefix": "Median",
    "output_stack": "Median_TEST_DAPI_1",
    "output_directory": "/nas/data/M246930_Scnn1a_4/processed/Medians",
    "minZ": 100,
    "maxZ": 103,
    "pool_size": 20
}


def getImageFromTilespecs(alltilespecs, index):
    N, M, img = getImage(alltilespecs[index])
    return img

def randomly_subsample_tilespecs(alltilespecs,numtiles):
    np.random.shuffle(alltilespecs)
    return alltilespecs[:numtiles]

class MakeMedian(RenderModule):
    default_schema = MakeMedianParams

    def run(self):

        # inits
        alltilespecs = []
        numtiles = 0
        firstts = []
        render = self.render
        outtilespecs = []
        ind = 0

        # get tilespecs for z

        for z in range(self.args['minZ'], self.args['maxZ'] + 1):
            tilespecs = self.render.run(
                renderapi.tilespec.get_tile_specs_from_z, self.args['input_stack'], z)
            alltilespecs.extend(tilespecs)
            # used for easy creation of tilespecs for output stack
            firstts.append(tilespecs[0])
            numtiles += len(tilespecs)

        #subsample in the case where the number of tiles is too large
        if self.args['num_images'] > 0:
            alltilespecs = randomly_subsample_tilespecs(alltilespecs,self.args['num_images'])

        # read images and create stack
        N, M, img0 = getImage(alltilespecs[0])
        stack = np.zeros((N, M, numtiles), dtype=img0.dtype)
        mypartial = partial(getImageFromTilespecs, alltilespecs)
        indexes = range(0, numtiles)
        with renderapi.client.WithPool(self.args['pool_size']) as pool:
            images = pool.map(mypartial, indexes)

        # calculate median
        for i in range(0, len(images)):
            stack[:, :, i] = images[i]
        np.median(stack, axis=2, overwrite_input=True)
        (A, B, C) = stack.shape
        if (numtiles % 2 == 0):
            med1 = stack[:, :, numtiles / 2 - 1]
            med2 = stack[:, :, numtiles / 2 + 1]
            med = (med1 + med2) / 2
        else:
            med = stack[:, :, (numtiles - 1) / 2]
        med = gaussian_filter(med, 10)

        # save image and create output tilespecs
        outdir = self.args['output_directory']
        if not os.path.exists(outdir):
            os.makedirs(outdir)

        for ind, z in enumerate(range(self.args['minZ'], self.args['maxZ'] + 1)):
            outImage = outdir + \
                "/%s_%s_%d.tif" % (self.args['file_prefix'],
                                   self.args['output_stack'], z)
            tifffile.imsave(outImage, med)
            ts = firstts[ind]
            ts.z = z
            mml_o = ts.ip[0]
            mml = renderapi.image_pyramid.MipMap(
                 imageUrl=outImage, maskUrl=mml_o.maskUrl)
            ts.ip[0] = mml
            outtilespecs.append(ts)

        # upload to render
        renderapi.stack.create_stack(
            self.args['output_stack'], cycleNumber=2, cycleStepNumber=1, render=self.render)
        renderapi.stack.set_stack_state(
            self.args['output_stack'], "LOADING", render=self.render)
        renderapi.client.import_tilespecs_parallel(
            self.args['output_stack'], outtilespecs,
            poolsize=self.args['pool_size'],render=self.render,close_stack=self.args['close_stack'])
        #renderapi.stack.set_stack_state(
        #    self.args['output_stack'], "COMPLETE", render=self.render)


if __name__ == "__main__":
    mod = MakeMedian(input_data=example_input)
    mod.run()
