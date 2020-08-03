import nipype
import os
from pycurt.interfaces.utils import DicomCheck, ConversionCheck, GetRefRTDose,\
     FileCheck, FolderMerge
from nipype.interfaces.dcm2nii import Dcm2niix
from pycurt.interfaces.plastimatch import DoseConverter
from pycurt.workflows.base import BaseWorkflow
from pycurt.interfaces.utils import FolderPreparation, FolderSorting, CheckRTStructures
from pycurt.interfaces.custom import RTDataSorting, MRClass
from nipype.interfaces.utility import Merge


class DataCuration(BaseWorkflow):
    
    def sorting_workflow(self, subject_name_position=-3, renaming=False,
                         mr_classiffication=True, checkpoints=None,
                         sub_checkpoints=None):

        nipype_cache = os.path.join(self.nipype_cache, 'data_sorting')
        result_dir = self.result_dir

        workflow = nipype.Workflow('sorting_workflow', base_dir=nipype_cache)
        datasink = nipype.Node(nipype.DataSink(base_directory=result_dir),
                               "datasink")

#         prep = nipype.Node(interface=FolderPreparation(), name='prep')
#         prep.inputs.input_dir = self.base_dir
#         create_list = nipype.Node(interface=CreateSubjectsList(), name='cl')
#         create_list.inputs.input_dir = self.base_dir
        file_check = nipype.Node(interface=FileCheck(),
                                    name='fc')
        file_check.inputs.input_dir = self.base_dir
        file_check.inputs.subject_name_position = subject_name_position
        file_check.inputs.renaming = renaming
        prep = nipype.MapNode(interface=FolderPreparation(), name='prep',
                              iterfield=['input_list'])
        sort = nipype.MapNode(interface=FolderSorting(), name='sort',
                              iterfield=['input_dir'])
        mr_rt_merge = nipype.MapNode(interface=Merge(2), name='mr_rt_merge',
                                    iterfield=['in1', 'in2'])
        mr_rt_merge.inputs.ravel_inputs = True
        merging = nipype.Node(interface=FolderMerge(), name='merge')
        if mr_classiffication:
            if checkpoints is None or sub_checkpoints is None:
                raise Exception('MRClass weights were not provided, MR image '
                                'classification cannot be performed!')
            mrclass = nipype.MapNode(interface=MRClass(), name='mrclass',
                                     iterfield=['mr_images'])
            mrclass.inputs.checkpoints = checkpoints
            mrclass.inputs.sub_checkpoints = sub_checkpoints
        else:
            mr_rt_merge.inputs.in1 = None
        rt_sorting = nipype.MapNode(interface=RTDataSorting(), name='rt_sorting',
                                    iterfield=['input_dir'])

#         workflow.connect(create_list, 'file_list', file_check, 'input_file')
        workflow.connect(file_check, 'out_list', prep, 'input_list')
        workflow.connect(prep, 'out_folder', sort, 'input_dir')
        workflow.connect(sort, 'out_folder', rt_sorting, 'input_dir')
        if mr_classiffication:
            workflow.connect(sort, 'mr_images', mrclass, 'mr_images')
            workflow.connect(mrclass, 'out_folder', mr_rt_merge, 'in1')

        workflow.connect(rt_sorting, 'out_folder', mr_rt_merge, 'in2')
        workflow.connect(mr_rt_merge, 'out', merging, 'input_list')
        workflow.connect(merging, 'out_folder', datasink, '@rt_sorted')
#         workflow.connect(rt_sorting, 'out_folder', datasink, '@rt_sorted')
        
        return workflow

    def convertion_workflow(self):
        
        self.datasource()

        datasource = self.data_source
        ref_sequence = self.ref_sequence
        t10 = self.t10
        sub_id = self.sub_id
        result_dir = self.result_dir
        nipype_cache = self.nipype_cache
        sequences = self.sequences
        reference = self.reference
        rt_data = self.rt
        if rt_data is not None:
            rt_session = rt_data['session']

        workflow = nipype.Workflow('data_convertion_workflow', base_dir=nipype_cache)
    
        datasink = nipype.Node(nipype.DataSink(base_directory=result_dir), "datasink")
        substitutions = [('subid', sub_id)]
        substitutions += [('results/', '{}/'.format(self.workflow_name))]
        if type(ref_sequence) == list:
            to_convert = sequences+ref_sequence
        else:
            to_convert = sequences+[ref_sequence]
        if rt_data is not None:
            rt_sequences = [x for x in rt_data.keys() if rt_data[x] and x != 'session'
                            and x != 'labels']
            workflow.connect(datasource, 'rt', datasink, 'results.subid.@rt')  
            to_convert = to_convert + rt_sequences
        else:
            rt_sequences = []
    
        if reference:
            to_convert.append('reference')
        if t10:
            to_convert.append('t1_0')
        if self.ct_sessions:
            to_convert.append('ct')
    
        for seq in to_convert:
            if seq not in rt_sequences:
                dc = nipype.MapNode(interface=DicomCheck(),
                                    iterfield=['dicom_dir'],
                                    name='dc{}'.format(seq))
                workflow.connect(datasource, seq, dc, 'dicom_dir')
                converter = nipype.MapNode(interface=Dcm2niix(),
                                           iterfield=['source_dir', 'out_filename'],
                                           name='converter{}'.format(seq))
                converter.inputs.compress = 'y'
                converter.inputs.philips_float = False
                if seq == 'reference' or seq == 'ct':
                    converter.inputs.merge_imgs = True
                else:
                    converter.inputs.merge_imgs = False
                check = nipype.MapNode(interface=ConversionCheck(),
                                       iterfield=['in_file', 'file_name'],
                                       name='check_conversion{}'.format(seq))
    
                workflow.connect(dc, 'outdir', converter, 'source_dir')
                workflow.connect(dc, 'scan_name', converter, 'out_filename')
                workflow.connect(dc, 'scan_name', check, 'file_name')
                workflow.connect(converter, 'converted_files', check, 'in_file')
                if seq == 'reference':
                    workflow.connect(check, 'out_file', datasink,
                                     'results.subid.REF.@{}_converted'.format(seq))
                elif seq == 't1_0':
                    workflow.connect(check, 'out_file', datasink,
                                     'results.subid.T10.@{}_converted'.format(seq))
                else:
                    workflow.connect(check, 'out_file', datasink,
                                     'results.subid.@{}_converted'.format(seq))
                    for i, session in enumerate(self.session_names[seq]):
                        substitutions += [(('_converter{0}{1}/'.format(seq, i), session+'/'))]
            else:
                if seq != 'rtstruct':
                    if seq == 'rtct':
                        converter = nipype.MapNode(
                            interface=Dcm2niix(),
                            iterfield=['source_dir', 'out_filename'],
                            name='converter{}'.format(seq))
                        converter.inputs.compress = 'y'
                        converter.inputs.philips_float = False
                        converter.inputs.merge_imgs = True
                    else:
                        converter = nipype.MapNode(interface=DoseConverter(),
                                               iterfield=['input_dose', 'out_name'],
                                               name='converter{}'.format(seq))
                    if seq == 'doses':
                        converter = nipype.MapNode(interface=DoseConverter(),
                                               iterfield=['input_dose'],
                                               name='converter{}'.format(seq))
                        get_dose = nipype.MapNode(interface=GetRefRTDose(),
                                                  iterfield=['doses'],
                                                  name='get_doses')
                        workflow.connect(datasource, 'doses', get_dose, 'doses')
                        workflow.connect(get_dose, 'dose_file', converter, 'input_dose')
                        converter.inputs.out_name = 'Unused_RTDOSE.nii.gz'
                        workflow.connect(
                                converter, 'out_file', datasink,
                                'results.subid.@{}_converted'.format(seq))
                    else:
                        dc = nipype.MapNode(interface=DicomCheck(),
                                            iterfield=['dicom_dir'],
                                            name='dc{}'.format(seq))
                        workflow.connect(datasource, seq, dc, 'dicom_dir')
                        if seq == 'rtct':
                            check = nipype.MapNode(interface=ConversionCheck(),
                                                   iterfield=['in_file', 'file_name'],
                                                   name='check_conversion{}'.format(seq))
                
                            workflow.connect(dc, 'outdir', converter, 'source_dir')
                            workflow.connect(dc, 'scan_name', converter, 'out_filename')
                            workflow.connect(dc, 'scan_name', check, 'file_name')
                            workflow.connect(converter, 'converted_files', check, 'in_file')
                            workflow.connect(
                                check, 'out_file', datasink,
                                'results.subid.@{}_converted'.format(seq))
                        else:
                            workflow.connect(dc, 'dose_file', converter, 'input_dose')
                            workflow.connect(dc, 'scan_name', converter, 'out_name')
                            workflow.connect(
                                converter, 'out_file', datasink,
                                'results.subid.@{}_converted'.format(seq))
                else:
                    dc = nipype.MapNode(interface=DicomCheck(),
                                        iterfield=['dicom_dir'],
                                        name='dc{}'.format(seq))
                    workflow.connect(datasource, seq, dc, 'dicom_dir')
                    workflow.connect(dc, 'outdir', datasink,
                                     'results.subid.@rtstruct')
                    for i, session in enumerate(rt_session):
                        substitutions += [(('_dc{0}{1}/checked_dicoms'.format(seq, i),
                                            session+'/RTSTRUCT_used'))]
                for i, session in enumerate(rt_session):
                    substitutions += [(('_converter{0}{1}/'.format(seq, i), session+'/'))]
    
        substitutions += [('_converterreference0/', '')]
        substitutions += [('_convertert1_00/', '')]
    
        datasink.inputs.substitutions =substitutions
    
        return workflow

    def workflow_setup(self, data_sorting=False, subject_name_position=-3,
                       renaming=False, mr_classiffication=True, checkpoints=None,
                       sub_checkpoints=None):

        if data_sorting:
            workflow = self.sorting_workflow(
                subject_name_position=subject_name_position,
                renaming=renaming, mr_classiffication=mr_classiffication,
                checkpoints=checkpoints, sub_checkpoints=sub_checkpoints)
#             sorting_workflow.run()
        else:
            workflow = self.convertion_workflow()

        return workflow
