from nipype.interfaces.base import (
    BaseInterface, TraitedSpec, Directory, File,
    traits, BaseInterfaceInputSpec, InputMultiPath)
import pydicom
import numpy as np
from pycurt.utils.dicom import dcm_check, dcm_info
from pathlib import Path
import shutil
import os
import nibabel as nib
import glob
from pycurt.utils.filemanip import split_filename, label_move_image
from skimage.transform import resize
import pydicom as pd
import re
from collections import defaultdict
from nipype.interfaces.base import isdefined
from pycurt.converters.dicom import DicomConverter
from . import logging


iflogger = logging.getLogger('nipype.interface')


RT_NAMES = ['RTSTRUCT', 'RTDOSE', 'RTPLAN', 'RTCT']
POSSIBLE_NAMES = ['RTSTRUCT', 'RTDOSE', 'RTPLAN', 'T1KM', 'FLAIR',
                  'CT', 'ADC', 'T1', 'SWI', 'T2', 'T2KM', 'CT1',
                  'RTCT']
ExplicitVRLittleEndian = '1.2.840.10008.1.2.1'
ImplicitVRLittleEndian = '1.2.840.10008.1.2'
DeflatedExplicitVRLittleEndian = '1.2.840.10008.1.2.1.99'
ExplicitVRBigEndian = '1.2.840.10008.1.2.2'
NotCompressedPixelTransferSyntaxes = [ExplicitVRLittleEndian,
                                      ImplicitVRLittleEndian,
                                      DeflatedExplicitVRLittleEndian,
                                      ExplicitVRBigEndian]

class DicomCheckInputSpec(BaseInterfaceInputSpec):

    dicom_dir = Directory(exists=True, desc='Directory with the DICOM files to check')
    working_dir = Directory('checked_dicoms', usedefault=True,
                            desc='Base directory to save the corrected DICOM files')


class DicomCheckOutputSpec(TraitedSpec):

    outdir = Directory(exists=True, desc='Path to the directory with the corrected DICOM files')
    scan_name = traits.Str(desc='Scan name')
    dose_file = File(desc='Dose file, if any')
    dose_output = File()


class DicomCheck(BaseInterface):

    input_spec = DicomCheckInputSpec
    output_spec = DicomCheckOutputSpec

    def _run_interface(self, runtime):

        dicom_dir = self.inputs.dicom_dir
        wd = os.path.abspath(self.inputs.working_dir)
        self.dose_file = None

        img_paths = dicom_dir.split('/')
        scan_name = list(set(POSSIBLE_NAMES).intersection(img_paths))[0]
        name_index = img_paths.index(scan_name)
        tp = img_paths[name_index-1]
        sub_name = img_paths[name_index-2]
        if scan_name in RT_NAMES:
            if scan_name == 'RTDOSE':
                scan_name = scan_name+'_{}.nii.gz'.format(img_paths[-1])
            dicoms = sorted(os.listdir(dicom_dir))
            if not os.path.isdir(wd):
                os.makedirs(wd)
            for item in dicoms:
                curr_item = os.path.join(dicom_dir, item)
                if os.path.isdir(curr_item):
                    shutil.copytree(curr_item, wd)
                else:
                    shutil.copy2(curr_item, os.path.join(wd, item))
                if scan_name == 'RTSTRUCT':
                    rt_dcm = glob.glob(wd+'/*.dcm')[0]
                    ds = pd.read_file(rt_dcm)
                    regex = re.compile('[^a-zA-Z]')
                    for i in range(len(ds.StructureSetROISequence)):
                        new_roiname=regex.sub('', ds.StructureSetROISequence[i].ROIName)
                        ds.StructureSetROISequence[i].ROIName = new_roiname
                    ds.save_as(rt_dcm)
        else:
            dicoms, im_types, series_nums = dcm_info(dicom_dir)
            dicoms = dcm_check(dicoms, im_types, series_nums)
            if dicoms:
                if not os.path.isdir(wd):
                    os.makedirs(wd)
                    for d in dicoms:
                        shutil.copy2(d, wd)
        self.outdir = wd
        self.scan_name = scan_name
        if 'RTDOSE' in scan_name:
            self.dose_file = glob.glob(os.path.join('/'.join(img_paths), '*.dcm'))[0]
            self.dose_output = os.path.join(wd, sub_name, tp, '{}.nii.gz'.format(scan_name))

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['outdir'] = self.outdir
        outputs['scan_name'] = self.scan_name
        if self.dose_file is not None:
            outputs['dose_file'] = self.dose_file
            outputs['dose_output'] = self.dose_output
        else:
            outputs['dose_file'] = self.scan_name
            outputs['dose_output'] = self.scan_name

        return outputs


class ConversionCheckInputSpec(BaseInterfaceInputSpec):

    in_file = InputMultiPath(File(), desc='(List of) file that'
                             ' needs to be checked after DICOM to NIFTI conversion')
    file_name = traits.Str(desc='Name that the converted file has to match'
                           ' in order to be considered correct.')


class ConversionCheckOutputSpec(TraitedSpec):

    out_file = traits.Str()


class ConversionCheck(BaseInterface):

    input_spec = ConversionCheckInputSpec
    output_spec = ConversionCheckOutputSpec

    def _run_interface(self, runtime):

        converted = self.inputs.in_file
        scan_name = self.inputs.file_name
        
        converted_old = converted[:]
        to_remove = []
        base_dir = os.path.dirname(converted[0])
        extra = [x for x in converted if x.split('/')[-1]!='{}.nii.gz'.format(scan_name)]
        if len(extra) == len(converted):
            if len(extra) == 2 and scan_name == 'T2':
                to_remove += extra
                if not os.path.isfile(os.path.join(base_dir, 'T2.nii.gz')):
                    shutil.copy2(extra[1], os.path.join(base_dir, 'T2.nii.gz'))
                converted_old.append(os.path.join(base_dir, 'T2.nii.gz'))
            else:
                to_remove += extra
                converted = None
        else:
            to_remove += extra

        if to_remove:
            for f in to_remove:
                if os.path.isfile(f):
                    converted_old.remove(f)
        if converted_old:
            self.converted = converted_old[0]
            try:
                ref = nib.load(self.converted)
                data = ref.get_data()
                if len(data.squeeze().shape) == 2 or len(data.squeeze().shape) > 4:
                    if os.path.isfile(self.converted):
                        self.converted = None
                elif len(data.squeeze().shape) == 4:
                    im2save = nib.Nifti1Image(data[:, :, :, 0], affine=ref.affine)
                    nib.save(im2save, self.converted)
                elif len(data.dtype) > 0:
                    iflogger.info('{} is not a greyscale image. It will'
                                  ' be deleted.'.format(self.converted))
                    if os.path.isfile(self.converted):
                        self.converted = None
            except:
                iflogger.info('{} failed to save with nibabel. '
                              'It will be deleted.'.format(self.converted))
                if os.path.isfile(self.converted):
                    self.converted = None
        else:
            self.converted = None

        if self.inputs.in_file and self.converted is None:
            outfile = self.inputs.in_file[0].split('.nii')[0]+'_WRONG_CONVERTION.nii.gz'
            shutil.copy2(self.inputs.in_file[0], outfile)
            self.converted = outfile

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        if self.converted is not None:
            outputs['out_file'] = self.converted

        return outputs


class RemoveRTFilesInputSpec(BaseInterfaceInputSpec):

    source_dir = traits.List()
    out_filename = traits.List()
    output_dir = traits.List()


class RemoveRTFilesOutputSpec(TraitedSpec):

    source_dir = traits.List()
    out_filename = traits.List()
    output_dir = traits.List()


class RemoveRTFiles(BaseInterface):
    
    input_spec = RemoveRTFilesInputSpec
    output_spec = RemoveRTFilesOutputSpec
    
    def _run_interface(self, runtime):
        
        source_dir = self.inputs.source_dir
        out_filename = self.inputs.out_filename
        output_dir = self.inputs.output_dir
        
        indexes = [i for i, x in enumerate(out_filename) if 'RTSTRUCT' not in x]
        self.source_dir = [source_dir[x] for x in indexes]
        self.out_filename = [out_filename[x] for x in indexes]
        self.output_dir = [output_dir[x] for x in indexes]
        
        return runtime
    
    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['source_dir'] = self.source_dir
        outputs['out_filename'] = self.out_filename
        outputs['output_dir'] = self.output_dir

        return outputs


class NNUnetPreparationInputSpec(BaseInterfaceInputSpec):

    images = traits.List(mandatory=True, desc='List of images to be prepared before'
                         ' running the nnUNet inference.')


class NNUnetPreparationOutputSpec(TraitedSpec):

    output_folder = Directory(exists=True, desc='Output folder prepared for nnUNet.')


class NNUnetPreparation(BaseInterface):

    input_spec = NNUnetPreparationInputSpec
    output_spec = NNUnetPreparationOutputSpec

    def _run_interface(self, runtime):

        images = self.inputs.images
        if images:
            new_dir = os.path.abspath('data_prepared')
            os.mkdir(os.path.abspath('data_prepared'))
            for i, image in enumerate(images):
                _, _, ext = split_filename(image)
                shutil.copy2(image, os.path.join(
                    new_dir,'subject1_{}'.format(str(i).zfill(4))+ext))
        else:
            raise Exception('No images provided!Please check.')

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['output_folder'] = os.path.abspath('data_prepared')

        return outputs


class CheckRTStructuresInputSpec(BaseInterfaceInputSpec):
    
    rois = InputMultiPath(File(exists=True), desc='RT structures to check')
    dose_file = File(exists=True, desc='Dose file.')


class CheckRTStructuresOutputSpec(TraitedSpec):
    
    checked_roi = File(exists=True, desc='ROI with the maximum overlap with the dose file.')


class CheckRTStructures(BaseInterface):
    
    input_spec = CheckRTStructuresInputSpec
    output_spec = CheckRTStructuresOutputSpec

    def _run_interface(self, runtime):
    
        rois = self.inputs.rois
        dose_nii = self.inputs.dose_file
        rois1 = [x for x in rois if 'gtv' in x.split('/')[-1].lower()]
        if not rois1:
            rois1 = [x for x in rois if 'ptv' in x.split('/')[-1].lower()]
        if not rois1:
            rois1 = [x for x in rois if 'ctv' in x.split('/')[-1].lower()]
        if not rois:
            raise Exception('No GTV, PTV or CTV found in the rois! Please check')

        if len(rois1) > 1:
            roi_dict = {}
            dose = nib.load(dose_nii).get_data()
            dose_vector = dose[dose > 0]
            dose_maxvalue = np.percentile(dose_vector, 99)
            ref_roi = nib.load(rois1[0]).get_data()
            if dose.shape != ref_roi.shape:
                dose = resize(dose, ref_roi.shape, order=0, mode='edge',
                                   cval=0, anti_aliasing=False)

            dose_bool = dose >= dose_maxvalue
            
            for f in rois1:
                roi = nib.load(f).get_data()
                roi_bool = roi > 0
                nr_andvoxel = np.logical_and(dose_bool, roi_bool)
                roi_dict[f] = np.sum(nr_andvoxel)/np.sum(roi_bool)
            roi_tokeep = max(roi_dict, key=lambda key: roi_dict[key])
            for key in roi_dict.keys():
                if key == roi_tokeep:
                    self.checked_roi = key
        elif len(rois1) == 1:
            self.checked_roi = rois1[0]

        return runtime
    
    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['checked_roi'] = self.checked_roi

        return outputs


class GetRefRTDoseInputSpec(BaseInterfaceInputSpec):
    
    doses = InputMultiPath(Directory(exists=True), desc='RT doses to check')


class GetRefRTDoseOutputSpec(TraitedSpec):
    
    dose_file = File(exists=True, desc='Dose file to be converted.')


class GetRefRTDose(BaseInterface):
    
    input_spec = GetRefRTDoseInputSpec
    output_spec = GetRefRTDoseOutputSpec

    def _run_interface(self, runtime):
    
        doses = self.inputs.doses
        phys = [x for y in doses for x in glob.glob(y+'/*/*.dcm') if 'PHY' in x]
        rbe = [x for y in doses for x in glob.glob(y+'/*/*.dcm') if 'RBE' in x]
        if phys:
#             dcms = glob.glob(phys[0]+'/*.dcm')
            dcms = phys
        elif rbe:
            dcms = rbe
        elif doses: 
            dcms = [x for y in doses for x in glob.glob(y+'/*/*.dcm')]

        right_dcm = []
        for dcm in dcms:
            hd = pydicom.read_file(dcm)
            try:
                hd.GridFrameOffsetVector
                right_dcm.append(dcm)
            except:
                continue

        dcms = right_dcm[:]
        if dcms and len(dcms)==1: 
            dose_file = dcms[0]
        elif dcms and len(dcms) > 1: 
            iflogger.info('More than one dose file') 
            processed = False 
            for dcm in dcms: 
                hd = pydicom.read_file(dcm) 
                dose_tp = hd.DoseSummationType 
                if not 'BEAM' in dose_tp and not processed: 
                    dose_file = dcm
                    processed = True 
                    break 
            if not processed:
                iflogger.info('No PLAN in any dose file')
                dose_file = dcms[0]
        self.dose_file = dose_file
        return runtime
    
    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['dose_file'] = self.dose_file

        return outputs


class FileCheckInputSpec(BaseInterfaceInputSpec):
    
    input_dir = Directory(exists=True, desc='Input directory to prepare properly.')
    renaming = traits.Bool(False, desc='Whether or not to use the information stored'
                           'in the DICOM header to rename the subject and sessions '
                           'folders. If False, the file path will be splitted '
                           'and the subject name will be taken from there. In this '
                           'case, the subject_name_position must be provided.'
                           'Default is False.', usedefault=True)
    subject_name_position = traits.Int(
        -3, usedefault=True, desc='The position of the subject name in the splitted '
        'file path (file_path.split("/")). Default is -3, so it assumes that the subject '
        'name is in the third position starting from the end of the file path.')


class FileCheckOutputSpec(TraitedSpec):
    
    out_list = traits.List(desc='Prepared folder.')


class FileCheck(BaseInterface):
    
    input_spec = FileCheckInputSpec
    output_spec = FileCheckOutputSpec
    
    def _run_interface(self, runtime):

        input_dir = self.inputs.input_dir
        renaming = self.inputs.renaming
        out_list = []
        if not renaming:
            sub_name_position = self.inputs.subject_name_position

        scans = defaultdict(list)
        patient_names = defaultdict(list)
        scan_dates = defaultdict(list)
        z = 0
        for path, _, files in os.walk(input_dir):
            for f in files:
                if '.dcm' in f:
                    filename = os.path.join(path, f)
                    iflogger.info('Process number: {}\n File: {}'.format(z, filename))
                    try:
                        ds = pydicom.dcmread(filename, force = True)
                    except:
                        iflogger.info('{} could not be read, dicom '
                              'file may be corrupted'.format(filename))
                    try:
                        seriesDescription=ds.SeriesDescription.upper().replace('_','')
                    except:
                        try:
                            seriesDescription=ds.Modality.upper().replace('_','')
                        except:
                            seriesDescription='NONE'
                    try:
                        studyInstance = ds.StudyInstanceUID
                    except:
                        studyInstance='NONE'
                    try:
                        seriesInstance = ds.SeriesInstanceUID
                    except:
                        seriesInstance='NONE'
                    key = seriesDescription +'_' + seriesInstance + '_' + studyInstance
                    key = self.strip_non_ascii(re.sub(r'[^\w]', '', key))
                    key = key.replace('_','-')
                    scans[key].append(filename)
                    if renaming:
                        try:
                            patient_names[key].append(ds.PatientID)
                        except AttributeError:
                            iflogger.info('No patient ID for {}'.format(filename))
                            patient_names[key].append('Corrupted')
                    else:
                        sub_name = filename.split('/')[sub_name_position]
                        patient_names[key].append(sub_name)
                    try:
                        scan_dates[key].append(ds.StudyDate)
                    except:
                        iflogger.info('No study date for {}'.format(filename))
                        scan_dates[key].append('Corrupted')
                    z += 1
        names = [patient_names[x][0] for x in patient_names.keys()]
        scans_tot = []
        pn_tot = []
        sd_tot = []
        for s in set(names):
            temp_scan = {}
            temp_pn = {}
            temp_sd = {}
            for key in patient_names.keys():
                if patient_names[key][0] == s:
                    temp_scan[key] = scans[key]
                    temp_pn[key] = patient_names[key]
                    temp_sd[key] = scan_dates[key]
            out_list.append([temp_scan, temp_pn, temp_sd])
#             scans_tot.append(temp_scan)
#             pn_tot.append(temp_pn)
#             sd_tot.append(temp_sd)
        self.out_list = out_list
#         self.out_list = [scans, patient_names, scan_dates]
#         self.out_list = [scans_tot, pn_tot, sd_tot]

        return runtime

    def strip_non_ascii(self, string):
        ''' Returns the string without non ASCII characters'''
        stripped = (c for c in string if 0 < ord(c) < 127)
        return ''.join(stripped)

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs['out_list'] = self.out_list

        return outputs

# class CreateSubjectsListInputSpec(BaseInterfaceInputSpec):
# 
#     input_dir = Directory(exists=True, desc='Input directory to prepare properly.')
# 
# 
# class CreateSubjectsListOutputSpec(TraitedSpec):
#     
#     file_list = traits.List()
# 
# 
# class CreateSubjectsList(BaseInterface):
# 
#     input_spec = CreateSubjectsListInputSpec
#     output_spec = CreateSubjectsListOutputSpec
#     
#     def _run_interface(self, runtime):
#         input_dir = self.inputs.input_dir
#         file_list = []
#         for path, _, files in os.walk(input_dir):
#             for f in files:
#                 if '.dcm' in f:
#                     file_list.append(os.path.join(path, f))
#         self.file_list = file_list
#         
#         return runtime
#     
#     def _list_outputs(self):
#         outputs = self._outputs().get()
#         outputs['file_list'] = self.file_list
# 
#         return outputs
# 
# 
# class FileCheckInputSpec(BaseInterfaceInputSpec):
#     
#     input_file = File(exists=True, desc='Input file to check.')
#     renaming = traits.Bool(False, desc='Whether or not to use the information stored'
#                            'in the DICOM header to rename the subject and sessions '
#                            'folders. If False, the file path will be splitted '
#                            'and the subject name will be taken from there. In this '
#                            'case, the subject_name_position must be provided.'
#                            'Default is False.', usedefault=True)
#     subject_name_position = traits.Int(
#         -3, usedefault=True, desc='The position of the subject name in the splitted '
#         'file path (file_path.split("/")). Default is -3, so it assumes that the subject '
#         'name is in the third position starting from the end of the file path.')
# 
# 
# class FileCheckOutputSpec(TraitedSpec):
#     
#     out_list = traits.List(desc='Prepared folder.')
# 
# 
# class FileCheck(BaseInterface):
#     
#     input_spec = FileCheckInputSpec
#     output_spec = FileCheckOutputSpec
#     
#     def _run_interface(self, runtime):
#         
#         filename = self.inputs.input_file
#         renaming = self.inputs.renaming
#         if not renaming:
#             sub_name_position = self.inputs.subject_name_position
# 
#         scans = defaultdict(list)
#         patient_names = defaultdict(list)
#         scan_dates = defaultdict(list)
# 
#         try:
#             ds = pydicom.dcmread(filename,force = True)
#         except:
#             print('{} could not be read, dicom '
#                   'file may be corrupted'.format(filename))
#         try:
#             seriesDescription=ds.SeriesDescription.upper().replace('_','')
#         except:
#             try:
#                 seriesDescription=ds.Modality.upper().replace('_','')
#             except:
#                 seriesDescription='NONE'
#         try:
#             studyInstance = ds.StudyInstanceUID
#         except:
#             studyInstance='NONE'
#         try:
#             seriesInstance = ds.SeriesInstanceUID
#         except:
#             seriesInstance='NONE'
#         key = seriesDescription +'_' + seriesInstance + '_' + studyInstance
#         key = self.strip_non_ascii(re.sub(r'[^\w]', '', key))
#         key = key.replace('_','-')
#         scans[key].append(filename)
#         if renaming:
#             try:
#                 patient_names[key].append(ds.PatientID)
#             except AttributeError:
#                 print('No patient ID for {}'.format(filename))
#                 patient_names[key].append('Corrupted')
#         else:
#             sub_name = filename.split('/')[sub_name_position]
#             patient_names[key].append(sub_name)
#         try:
#             scan_dates[key].append(ds.StudyDate)
#         except:
#             print('No study date for {}'.format(filename))
#             scan_dates[key].append('Corrupted')
# 
#         self.out_list = [scans, patient_names, scan_dates]
# 
#         return runtime
# 
#     def strip_non_ascii(self, string):
#         ''' Returns the string without non ASCII characters'''
#         stripped = (c for c in string if 0 < ord(c) < 127)
#         return ''.join(stripped)
# 
#     def _list_outputs(self):
#         outputs = self._outputs().get()
#         outputs['out_list'] = self.out_list
# 
#         return outputs


class FolderPreparationInputSpec(BaseInterfaceInputSpec):
    
    input_list = traits.List(desc='Input directory to prepare properly.')
    out_folder = Directory('prepared_dir', usedefault=True,
                           desc='Prepared folder.')


class FolderPreparationOutputSpec(TraitedSpec):
    
#     out_folder = traits.List(desc='Prepared folder.')
    out_folder = Directory(exists=True, desc='Prepared folder.')


class FolderPreparation(BaseInterface):
    
    input_spec = FolderPreparationInputSpec
    output_spec = FolderPreparationOutputSpec
    
    def _run_interface(self, runtime):
        
        input_list = self.inputs.input_list
        output_dir = os.path.abspath(self.inputs.out_folder)
        
        scans = input_list[0]
        patient_names = input_list[1]
        scan_dates = input_list[2]
#         scans = defaultdict(list)
#         patient_names = defaultdict(list)
#         scan_dates = defaultdict(list)
#         
#         for el in input_list:
#             key = list(el[0].keys())[0]
#             scans[key].append(el[0][key][0])
#             patient_names[key].append(el[1][key][0])
#             scan_dates[key].append(el[2][key][0])

        for key in scans.keys():
            for file in scans[key]:
                out_basename = os.path.join(patient_names[key][0],
                                            scan_dates[key][0])
                dir_name= os.path.join(output_dir, out_basename, key)
                if not os.path.isdir(dir_name):
                    os.makedirs(dir_name)
                shutil.copy2(Path(file), dir_name)

        return runtime

    def strip_non_ascii(self, string):
        ''' Returns the string without non ASCII characters'''
        stripped = (c for c in string if 0 < ord(c) < 127)
        return ''.join(stripped)

    def _list_outputs(self):
        outputs = self._outputs().get()
        if isdefined(self.inputs.out_folder):
            outputs['out_folder'] = os.path.abspath(
                self.inputs.out_folder)
#         if isdefined(self.inputs.out_folder):
#             outputs['out_folder'] = sorted(glob.glob(os.path.abspath(
#                 self.inputs.out_folder+'/*')))

        return outputs


class FolderSortingInputSpec(BaseInterfaceInputSpec):
    
    input_dir = Directory(exists=True, help='Input directory to sort.')
    out_folder = Directory('sorted_dir', usedefault=True,
                           desc='Prepared folder.')
    


class FolderSortingOutputSpec(TraitedSpec):
    
    out_folder = Directory(help='Sorted folder.')
    mr_images = traits.List(help='List of MR images to be classified using MRCLASS')


class FolderSorting(BaseInterface):
    
    input_spec = FolderSortingInputSpec
    output_spec = FolderSortingOutputSpec
    
    def _run_interface(self, runtime):
        
        input_dir = self.inputs.input_dir
        out_dir = os.path.abspath(self.inputs.out_folder)

        modality_List = ['RTDOSE','CT','RTSTRUCT','RTPLAN', 'PET']
        
        images=glob.glob(input_dir+'/*/*/*')
        for_inference=[]

        for i in images:
            if os.path.isdir(i):
                dcm_files = [os.path.join(i, item) for item in os.listdir(i)
                             if ('.dcm' in item)]
            else:
                continue
            try:
                ds = pydicom.dcmread(dcm_files[0], force=True)
                modality_check = ds.Modality
            except:
                modality_check = ''
            if modality_check == 'RTSS':
                modality_check = 'RTSTRUCT'
            if modality_check in modality_List:
                label_move_image(i, modality_check, out_dir)
            elif modality_check=='MR' or modality_check=='OT':
                #checking for duplicates or localizer
                new_image, i = label_move_image(i, '', out_dir,
                                                renaming=False)
                dicoms, im_types, series_nums = dcm_info(new_image)
                dicoms_fl = dcm_check(dicoms, im_types, series_nums)
#                 corrupted = [f for f in dicoms if str(f) not in dicoms_fl]
                [os.remove(f) for f in dicoms if str(f) not in dicoms_fl]
                good = [f for f in dicoms if str(f) in dicoms_fl]
#                 [os.remove(f) for f in dicoms if str(f) not in dicoms_fl]
                if good:
                    converter = DicomConverter(new_image)
                    nifti_image = converter.convert(rename_dicom=True)
                    if nifti_image is not None:
                        for_inference.append(nifti_image)
                    else:
                        label_move_image(i, 'error_converting', out_dir)
                        iflogger.info('Error converting', str(new_image))
            else:
                label_move_image(i, 'Unknown_modality', out_dir)
        self.for_inference = for_inference

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        if isdefined(self.inputs.out_folder):
            outputs['out_folder'] = os.path.abspath(
                self.inputs.out_folder)
        outputs['mr_images'] = self.for_inference

        return outputs


class FolderMergeInputSpec(BaseInterfaceInputSpec):
    
    input_list = traits.List(help='Input directory to sort.')
    out_folder = Directory('Sorted_Data', usedefault=True,
                           desc='Prepared folder.')


class FolderMergeOutputSpec(TraitedSpec):
    
    out_folder = Directory(help='Sorted folder.')


class FolderMerge(BaseInterface):
    
    input_spec = FolderMergeInputSpec
    output_spec = FolderMergeOutputSpec
    
    def _run_interface(self, runtime):
        
        input_list = self.inputs.input_list
        out_dir = os.path.abspath(self.inputs.out_folder)
        
        for directories in input_list:
            mr_dir = directories[0]
            rt_dir = directories[1]
            if mr_dir is None or not os.path.isdir(mr_dir):
                iflogger.info('No MRI data found')
                mr_tocopy = []
                mr_sub_name = None
            else:
                mr_sub_name = os.listdir(mr_dir)[0]
                mr_tocopy = sorted(glob.glob(os.path.join(mr_dir, mr_sub_name, '*')))
            if not os.path.isdir(rt_dir):
                iflogger.info('No RT or CT data found')
                rt_tocopy = []
                rt_sub_name = None
            else:
                rt_sub_name = os.listdir(rt_dir)[0]
                rt_tocopy = sorted(glob.glob(os.path.join(rt_dir, rt_sub_name, '*')))
#             mr_sub_name = os.listdir(mr_dir)[0]
            if (rt_sub_name is not None and mr_sub_name is not None) and rt_sub_name != mr_sub_name:
                raise Exception('Subject name is different between MR and RT '
                                'result folder. Something went wrong.')
            if mr_sub_name is not None:
                sub_name = mr_sub_name
            elif rt_sub_name is not None:
                sub_name = rt_sub_name
            else:
                sub_name = None

            if sub_name is not None:
                if not os.path.isdir(os.path.join(out_dir, sub_name)):
                    os.makedirs(os.path.join(out_dir, sub_name))
                for folder in mr_tocopy+rt_tocopy:
                    folder_name = folder.split('/')[-1]
                    shutil.copytree(folder, os.path.join(
                        out_dir, sub_name,folder_name))

        return runtime

    def _list_outputs(self):
        outputs = self._outputs().get()
        if isdefined(self.inputs.out_folder):
            outputs['out_folder'] = os.path.abspath(
                self.inputs.out_folder)

        return outputs
