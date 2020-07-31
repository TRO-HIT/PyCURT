import os
import glob
import nipype
from nipype.interfaces.utility import Split
from pycurt.utils.utils import check_dcm_dose


POSSIBLE_SEQUENCES = ['t1', 'ct1', 't1km', 't2', 'flair', 'adc', 'swi']


class BaseDatabase():

    def __init__(self, sub_id, input_dir, work_dir, process_rt=False):

        self.sub_id = sub_id
        self.base_dir = input_dir
        self.process_rt = process_rt
        self.nipype_cache = os.path.join(work_dir, 'nipype_cache', sub_id)
        self.result_dir = os.path.join(work_dir, 'workflows_output')
        self.workflow_name = self.__class__.__name__
        self.outdir = os.path.join(self.result_dir, self.workflow_name)
    
    def database(self):
        
        base_dir = self.base_dir
        sub_id = self.sub_id
        sequences = []

        sessions = [x for x in os.listdir(os.path.join(base_dir, sub_id))
                    if 'REF' not in x and 'T10' not in x and 'RT_' not in x
                    and 'CT_' not in x
                    and os.path.isdir(os.path.join(base_dir, sub_id, x))]
        ref_session = [x for x in os.listdir(os.path.join(base_dir, sub_id))
                       if x == 'REF' and os.path.isdir(os.path.join(base_dir, sub_id, x))]
        t10_session = [x for x in os.listdir(os.path.join(base_dir, sub_id))
                       if x == 'T10' and os.path.isdir(os.path.join(base_dir, sub_id, x))]
        rt_sessions = [x for x in os.listdir(os.path.join(base_dir, sub_id))
                       if 'RT_' in x and os.path.isdir(os.path.join(base_dir, sub_id, x))]
        ct_sessions = [x for x in os.listdir(os.path.join(base_dir, sub_id))
                       if 'CT_' in x and os.path.isdir(os.path.join(base_dir, sub_id, x))
                       and glob.glob(os.path.join(base_dir, sub_id, x, 'CT/1-*'))]

        if sessions:
            sequences = list(set([y.split('.nii.gz')[0].lower() for x in sessions
                                  for y in os.listdir(os.path.join(base_dir, sub_id, x))
                                  if y.endswith('.nii.gz')]))
            if not sequences:
                sequences = list(set([y.lower() for x in sessions
                                  for y in os.listdir(os.path.join(base_dir, sub_id, x))
                                  if os.path.isdir(os.path.join(base_dir, sub_id, x, y))]))
                ext = ''
            else:
                ext = '.nii.gz'
        else:
            ext = ''
        sequences = [x for x in sequences if x in POSSIBLE_SEQUENCES]
#         sequences = list(set([x for y in POSSIBLE_SEQUENCES for x in sequences if y in x]))
        self.session_names = {}
        for seq in sequences:
            sess = [x for x in sessions
                    for y in sorted(os.listdir(os.path.join(base_dir, sub_id, x)))
                    if y.lower() == seq]
            self.session_names[seq] = sess

        if 'ct1' in sequences:
            ref_sequence = 'ct1'
        elif 't1km' in sequences:
            ref_sequence = 't1km'
        elif 't1' in sequences:
            ref_sequence = 't1'
        elif ext == '':
            ref_sequence = []
        else:
            raise Exception('Nor T1 neither T1KM were found in {}. You need at least one of them '
                            'in order to perform registration.'.format(sub_id))
        self.add_subfolder = False
        if ext == '' and sessions:
            dcms = [y for x in sessions for y in glob.glob(os.path.join(base_dir, sub_id, x, '*/*.dcm'))
                    if 'CT_' not in y]
            if not dcms:
                dcms = [y for x in sessions for y in glob.glob(
                    os.path.join(base_dir, sub_id, x, '*/1-*', '*.dcm'))]
                if dcms:
                    self.add_subfolder = True
#                 else:
#                     raise Exception('It seems that there are no DICOM files in any '
#                                     'session. Please check.')
        if sequences and ref_sequence:
            sequences.remove(ref_sequence)
        if ref_session:
            reference = True
        else:
            print('NO REFERENCE CT!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
            reference = False
    
        if t10_session:
            t10 = True
        else:
            t10 = False
    
        rt = {}
        if rt_sessions and self.process_rt:
            rt['physical'] = []
            rt['rbe'] = []
            rt['doses'] = []
            rt['rtstruct'] = []
            rt['rtct'] = []
            rt['session'] = []
#             rt['labels'] = []
            for rt_session in rt_sessions:
                if os.path.isdir(os.path.join(base_dir, sub_id, rt_session, 'RTDOSE')):
                    physical = [x for x in os.listdir(os.path.join(
                        base_dir, sub_id, rt_session, 'RTDOSE')) if '1-PHY' in x]
                    if physical:
                        dcms = [x for y in physical for x in glob.glob(os.path.join(
                                base_dir, sub_id, rt_session, 'RTDOSE', y, '*.dcm'))]
                        right_dcm = check_dcm_dose(dcms)
                        if not right_dcm:
                            physical = []
                        else:
                            physical = ['PHYS']
                    rbe = [x for x in os.listdir(os.path.join(
                        base_dir, sub_id, rt_session, 'RTDOSE')) if '1-RBE' in x]
                    if rbe:
                        dcms = [x for y in rbe for x in glob.glob(os.path.join(
                                base_dir, sub_id, rt_session, 'RTDOSE', y, '*.dcm'))]
                        right_dcm = check_dcm_dose(dcms)
                        if not right_dcm:
                            rbe = []
                        else:
                            rbe = ['RBE']
#                     if not physical and not rbe:
                    doses = [x for x in os.listdir(os.path.join(
                        base_dir, sub_id, rt_session, 'RTDOSE')) if '1-RBE' not in x
                        and '1-PHY' not in x]
                    if doses:
                        dcms = [x for y in doses for x in glob.glob(os.path.join(
                            base_dir, sub_id, rt_session, 'RTDOSE', y, '*.dcm'))]
                        right_dcm = check_dcm_dose(dcms)
                        if not right_dcm:
                            doses = []
                        else:
                            doses = ['RTDOSE']
#                     else:
#                         doses = []
                    rt['physical'] = rt['physical']+physical
                    rt['rbe'] = rt['rbe'] + rbe
                    rt['doses'] = rt['doses'] + doses
                if os.path.isdir(os.path.join(base_dir, sub_id, rt_session, 'RTSTRUCT')):
                    rtstruct = [x for x in os.listdir(os.path.join(
                        base_dir, sub_id, rt_session, 'RTSTRUCT')) if '1-' in x]
                    rt['rtstruct'] = rt['rtstruct'] + rtstruct
                if os.path.isdir(os.path.join(base_dir, sub_id, rt_session, 'RTCT')):
                    rtct = [x for x in os.listdir(os.path.join(
                        base_dir, sub_id, rt_session, 'RTCT')) if '1-' in x]
                    rt['rtct'] = rt['rtct'] + rtct
                if [rt[x] for x in rt if rt[x]]:
#                     rt['labels'].append(rt_session)
                    rt['session'].append(rt_session)
        elif rt_sessions and not self.process_rt:
            rt['session'] = []
            for rt_session in rt_sessions:
                rt['session'].append(rt_session)
        else:
            rt = None
        
        if rt is not None and not [rt[x] for x in rt if rt[x]]:
            rt = None
        if rt is not None:
            len_rt_sessions = len(rt['session'])
            for key in rt:
                if len(rt[key]) != len_rt_sessions:
                    rt[key] = []
        self.sessions = sessions
        self.reference = reference
        self.t10 = t10
        self.sequences = sequences
        self.ref_sequence = ref_sequence
        self.rt = rt
        self.ext = ext
        self.ct_sessions = ct_sessions

        field_template, template_args, outfields = self.define_datasource_inputs()

        self.field_template = field_template
        self.template_args = template_args
        self.outfields= outfields

    def define_datasource_inputs(self):
    
        sequences = self.sequences
        if type(self.ref_sequence) == list:
            ref_sequence = self.ref_sequence
        else:
            ref_sequence = [self.ref_sequence]
        t10 = self.t10
        reference = self.reference
        rt = self.rt
        ext = self.ext
        process_rt = self.process_rt
        ct_sessions = self.ct_sessions

        field_template = dict()
        template_args = dict()
        outfields = ref_sequence+sequences
        for seq in ref_sequence+sequences:
            if self.add_subfolder:
                field_template[seq] = '%s/%s/{0}/1-*'.format(seq.upper())
            else:
                field_template[seq] = '%s/%s/{0}{1}'.format(seq.upper(), ext)
            template_args[seq] = [['sub_id', 'sessions']]
        if t10:
            field_template['t1_0'] = '%s/%s/CT1{0}'.format(ext)
            template_args['t1_0'] = [['sub_id', 'ref_t1']]
            outfields.append('t1_0')
        if reference:
            field_template['reference'] = '%s/%s/CT{0}'.format(ext)
            template_args['reference'] = [['sub_id', 'ref_ct']]
            outfields.append('reference')
        if ct_sessions:
            field_template['ct'] = '%s/%s/CT/1-*'
            template_args['ct'] = [['sub_id', 'ct_session']]
            outfields.append('ct')
        if rt and process_rt:
            physical = rt['physical']
            rbe = rt['rbe']
            doses = rt['doses']
            rtstruct = rt['rtstruct']
            rtct = rt['rtct']
            field_template['rt'] = '%s/%s'
            template_args['rt'] = [['sub_id', 'rt']]
            outfields.append('rt')
            if physical:
                field_template['physical'] = '%s/%s/RTDOSE/1-PHY*'
                template_args['physical'] = [['sub_id', 'rt']]
                outfields.append('physical')
            if rbe:
                field_template['rbe'] = '%s/%s/RTDOSE/1-RBE*'
                template_args['rbe'] = [['sub_id', 'rt']]
                outfields.append('rbe')
            if doses:
                field_template['doses'] = '%s/%s/RTDOSE'
                template_args['doses'] = [['sub_id', 'rt']]
                outfields.append('doses')
            if rtstruct:
                field_template['rtstruct'] = '%s/%s/RTSTRUCT/1-*'
                template_args['rtstruct'] = [['sub_id', 'rt']]
                outfields.append('rtstruct')
            if rtct:
                field_template['rtct'] = '%s/%s/RTCT/1-*'
                template_args['rtct'] = [['sub_id', 'rt']]
                outfields.append('rtct')
        elif rt and not process_rt:
            field_template['rt'] = '%s/%s'
            template_args['rt'] = [['sub_id', 'rt']]
            outfields.append('rt')
    
        return field_template, template_args, outfields

    def create_datasource(self):
        
        datasource = nipype.Node(
            interface=nipype.DataGrabber(
                infields=['sub_id', 'sessions', 'ref_ct', 'ref_t1'],
                outfields=self.outfields),
                name='datasource')
        datasource.inputs.base_directory = self.base_dir
        datasource.inputs.template = '*'
        datasource.inputs.sort_filelist = True
        datasource.inputs.raise_on_empty = False
        datasource.inputs.field_template = self.field_template
        datasource.inputs.template_args = self.template_args
        datasource.inputs.sub_id = self.sub_id
        datasource.inputs.sessions = self.sessions
        datasource.inputs.ref_ct = 'REF'
        datasource.inputs.ref_t1 = 'T10'
        if self.rt is not None:
            datasource.inputs.rt = self.rt['session']
        if self.ct_sessions:
            datasource.inputs.ct_session = self.ct_sessions
        
        return datasource

    def datasink(self, workflow, workflow_datasink):

        datasource = self.data_source
        sequences1 = [x for x in datasource.inputs.field_template.keys()
                      if x!='t1_0' and x!='reference' and x!='rt' and x!='rt_dose'
                      and x!='doses' and x!='rts_dcm' and x!='rtstruct'
                      and x!='physical' and x!='rbe' and x!='rtct' and x!='rtct_nifti']
        rt = [x for x in datasource.inputs.field_template.keys()
              if x=='rt']
    
        split_ds_nodes = []
        for i in range(len(sequences1)):
            sessions_wit_seq = [
                x for y in self.sessions for x in glob.glob(os.path.join(
                    self.base_dir, self.sub_id, y, sequences1[i].upper()+'.nii.gz'))]
            split_ds = nipype.Node(interface=Split(), name='split_ds{}'.format(i))
            split_ds.inputs.splits = [1]*len(sessions_wit_seq)
            split_ds_nodes.append(split_ds)

            if len(sessions_wit_seq) > 1:
                workflow.connect(datasource, sequences1[i], split_ds,
                                 'inlist')
                for j, sess in enumerate(sessions_wit_seq):
                    sess_name = sess.split('/')[-2]
                    workflow.connect(split_ds, 'out{}'.format(j+1),
                                     workflow_datasink, 'results.subid.{0}.@{1}'
                                     .format(sess_name, sequences1[i]))
            elif len(sessions_wit_seq) == 1:
                workflow.connect(datasource, sequences1[i], workflow_datasink,
                                 'results.subid.{0}.@{1}'
                                 .format(sessions_wit_seq[0].split('/')[-2],
                                         sequences1[i]))
        if self.reference:
            workflow.connect(datasource, 'reference', workflow_datasink,
                             'results.subid.REF.@ref_ct')
        if self.t10:
            workflow.connect(datasource, 't1_0', workflow_datasink,
                             'results.subid.T10.@ref_t1')
        if rt:
            workflow.connect(datasource, 'rt', workflow_datasink,
                             'results.subid.@rt')
        return workflow
