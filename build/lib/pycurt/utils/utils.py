import argparse
import getpass
import os
import pydicom
import glob
import re
import pydicom as pd


def check_dcm_dose(dcms):

    right_dcm = []
    for dcm in dcms:
        hd = pydicom.read_file(dcm)
        try:
            hd.GridFrameOffsetVector
            hd.pixel_array
            right_dcm.append(dcm)
        except:
            continue
    return right_dcm


def check_rtstruct(basedir, regex):

    data = []
    no_rt = []
    no_match = []
    for root, _, files in os.walk(basedir):
        for name in files:
            if (('RTDOSE' in name and name.endswith('.nii.gz'))
                    and os.path.isdir(os.path.join(root, 'RTSTRUCT_used'))):
                sub_name = root.split('/')[-2]
                try:
                    rts = glob.glob(os.path.join(root, 'RTSTRUCT_used', '*.dcm'))[0]
                    matching = check_rts(rts, regex)
                    if matching:
                        data.append(sub_name)
                    else:
                        no_match.append(sub_name)
                except IndexError:
                    print('No RTSTRUCT for {}'.format(root.split('/')[-2]))
                    no_rt.append(sub_name)
    return list(set(data))


def check_rts(rts, regex):

    ds = pd.read_file(rts)
    reg_expression = re.compile(regex)
    matching_regex = False
    for i in range(len(ds.StructureSetROISequence)):
        match = reg_expression.match(ds.StructureSetROISequence[i].ROIName)
        if match is not None:
            matching_regex = True
            break
    return matching_regex
