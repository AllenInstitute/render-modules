
import os
import json
import renderapi
import glob
import numpy as np
from ..module.render_module import RenderModule
from rendermodules.rough_align.schemas import ApplyRoughAlignmentTransformParameters
from rendermodules.stack.consolidate_transforms import *
from functools import partial
from renderapi.transform import AffineModel
from renderapi.transform import Polynomial2DTransform


if __name__ == "__main__" and __package__ is None:
    __package__ = "rendermodules.rough_align.apply_rough_alignment_transform_to_montage_stack"

example = {
    "render": {
        "host": "http://em-131fs",
        "port": 8080,
        "owner": "russelt",
        "project": "Reflections",
        "client_scripts": "/allen/programs/celltypes/workgroups/em-connectomics/gayathrim/nc-em2/Janelia_Pipeline/render_latest/render-ws-java-client/src/main/scripts"
    },
    "montage_stack": "Secs_1015_1099_5_reflections_mml6_montage",
    "prealigned_stack": "Secs_1015_1099_5_reflections_mml6_montage",
    "lowres_stack": "Secs_1015_1099_5_reflections_mml6_ds_rough_rigid",
    "output_stack": "Secs_1015_1099_5_reflections_mml6_rough_rigid",
    "tilespec_directory": "/allen/programs/celltypes/workgroups/em-connectomics/gayathrim/nc-em2/Janelia_Pipeline/scratch/rough/jsonFiles",
    "set_new_z": "False",
    "consolidate_trasnforms": "True",
    "minZ": 1015,
    "maxZ": 1020,
    "scale": 1,
    "pool_size": 20
}

# Another way is to use ConsolidateTransforms module
def consolidate_transforms(tforms, verbose=False, makePolyDegree=0):
    # Adapted from consolidate_transforms module

    tform_total = AffineModel()
    start_index = 0
    total_affines = 0
    new_tform_list = []

    for i,tform in enumerate(tforms):
        #print tform.className
        if 'AffineModel2D' in tform.className:
            total_affines+=1
            tform_total = tform.concatenate(tform_total)
            #tform_total.M=tform.M.dot(tform_total.M)
        else:
            if total_affines>0:
                if makePolyDegree>0:
                    polyTform = Polynomial2DTransform()._fromAffine(tform_total)
                    polyTform=polyTform.asorder(makePolyDegree)
                    new_tform_list.append(polyTform)
                else:
                    new_tform_list.append(tform_total)
                tform_total = AffineModel()
                total_affines =0
            new_tform_list.append(tform)
    if total_affines>0:
        if makePolyDegree>0:
            polyTform = Polynomial2DTransform()._fromAffine(tform_total)
            polyTform=polyTform.asorder(makePolyDegree)
            new_tform_list.append(polyTform)
        else:
            new_tform_list.append(tform_total)

    return new_tform_list




def apply_rough_alignment(render, input_stack, prealigned_stack, lowres_stack, output_dir, scale, Z):
    z = Z[0]
    newz = Z[1]

    try:
        print z
        # get lowres stack tile specs
        lowres_ts = render.run(
                            renderapi.tilespec.get_tile_specs_from_z,
                            lowres_stack,
                            newz)

        # get input stack tile specs (for the first tile)
        highres_ts = render.run(
                            renderapi.tilespec.get_tile_specs_from_z,
                            input_stack,
                            z)[0]

        # get the lowres stack rough alignment transformation
        tforms = lowres_ts[0].tforms
        d = tforms[-1].to_dict()
        #print(d['dataString'])
        dsList = d['dataString'].split()
        v0 = float(dsList[0])*scale
        v1 = float(dsList[1])*scale
        v2 = float(dsList[2])*scale
        v3 = float(dsList[3])*scale
        v4 = float(dsList[4])
        v5 = float(dsList[5])
        d['dataString'] = "%f %f %f %f %s %s"%(v0, v1, v2, v3, v4, v5)
        tforms[-1].from_dict(d)
        stackbounds = render.run(
                            renderapi.stack.get_bounds_from_z,
                            input_stack,
                            z)
        prestackbounds = render.run(
                            renderapi.stack.get_bounds_from_z,
                            prealigned_stack,
                            z)
        tx =  int(stackbounds['minX']) - int(prestackbounds['minX'])
        ty =  int(stackbounds['minY']) - int(prestackbounds['minY'])
        tforms1 = highres_ts.tforms
        d = tforms1[-1].to_dict()
        #print d
        dsList = d['dataString'].split()
        v0 = 1.0
        v1 = 0.0
        v2 = 0.0
        v3 = 1.0
        v4 = tx
        v5 = ty
        d['dataString'] = "%f %f %f %f %s %s"%(v0,v1,v2,v3,v4,v5)
        tforms1[-1].from_dict(d)
        # delete the lens correction transform
        if len(tforms1) > 1:
            del tforms1[0]

        ftform = tforms1 + tforms
        #newt = consolidate_transforms(ftform)

        allts = []
        highres_ts1 = render.run(
                            renderapi.tilespec.get_tile_specs_from_z,
                            input_stack,
                            z)

        for t in highres_ts1:
            for f in ftform:
                t.tforms.append(f)
            newt = consolidate_transforms(t.tforms)
            t.tforms = newt
            d1 = t.to_dict()
            d1['z'] = newz
            allts.append(d1)

        tilespecfilename = os.path.join(output_dir,'tilespec_%04d.json'%newz)
        print(tilespecfilename)
        fp = open(tilespecfilename,'w')
        json.dump([ts for ts in allts], fp, indent=4)
        fp.close()
    except:
        print "This z has not been aligned!"



class ApplyRoughAlignmentTransform(RenderModule):
    def __init__(self, schema_type=None, *args, **kwargs):
        if schema_type is None:
            schema_type = ApplyRoughAlignmentTransformParameters
        super(ApplyRoughAlignmentTransform, self).__init__(
            schema_type=schema_type, *args, **kwargs)


    def run(self):
        allzvalues = self.render.run(
            renderapi.stack.get_z_values_for_stack,
            self.args['montage_stack'])
        allzvalues = np.array(allzvalues)
        zvalues = allzvalues[(allzvalues >= self.args['minZ']) & (allzvalues <= self.args['maxZ'])]

        if self.args['set_new_z']:
            newzvalues = range(0, len(zvalues))
        else:
            newzvalues = zvalues

        # the old and new z values are required for the AT team
        Z = [[a,b] for a,b in zip(zvalues, newzvalues)]

        # delete existing json files in the tilespec directory
        jsonfiles = glob.glob("%s/*.json"%self.args['tilespec_directory'])
        for js in jsonfiles:
            if os.path.exists(js):
                cmd = "rm %s"%js
                os.system(cmd)

        mypartial = partial(
                        apply_rough_alignment,
                        self.render,
                        self.args['montage_stack'],
                        self.args['prealigned_stack'],
                        self.args['lowres_stack'],
                        self.args['tilespec_directory'],
                        self.args['scale'])

        with renderapi.client.WithPool(self.args['pool_size']) as pool:
            pool.map(mypartial, Z)

        jsonfiles = glob.glob("%s/*.json"%self.args['tilespec_directory'])
        # Create the output stack if it doesn't exist
        if self.args['output_stack'] not in self.render.run(renderapi.render.get_stacks_by_owner_project):
            # stack does not exist
            self.render.run(
                renderapi.stack.create_stack,
                self.args['output_stack'])

        # import tilespecs to render
        self.render.run(
            renderapi.client.import_jsonfiles_parallel,
            self.args['output_stack'],
            jsonfiles)

        # set stack state to complete
        self.render.run(
            renderapi.stack.set_stack_state,
            self.args['output_stack'],
            state='COMPLETE')


if __name__ == "__main__":
    mod = ApplyRoughAlignmentTransform(input_data=example)
    #mod = ApplyRoughAlignmentTransform(schema_type=ApplyRoughAlignmentTransformParameters)
    mod.run()
