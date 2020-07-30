"Script to run the PyCURT GUI"
import PySimpleGUI as sg
import sys
import os
from pycurt.workflows.curation import DataCuration
from pycurt.utils.config import create_subject_list, download_mrclass_weights


data_sorting = False
sg.ChangeLookAndFeel('GreenTan')

input_layout = [
    [sg.Text('Input folder', size=(20, 1), auto_size_text=False, justification='right', font=("Courier 10 Pitch", 20)),
     sg.InputText('', key='in_path', tooltip=(
         'Folder containing DICOM files in any structure.'), font=("Courier 10 Pitch", 20)),
     sg.FolderBrowse(font=("Courier 10 Pitch", 20))],
    [sg.Text('Working directory', size=(20, 1), auto_size_text=False,
             justification='right', font=("Courier 10 Pitch", 20)),
     sg.InputText('', key='work_dir', tooltip=(
         'Path where to save the results. If the directory does not \n'
         'exist, it will be created.'), font=("Courier 10 Pitch", 20)),
     sg.FolderBrowse(font=("Courier 10 Pitch", 20))],
    [sg.Text('Number of cores', size=(20, 1), auto_size_text=False, justification='right',
            tooltip=('Number of cores to use to run PyCurt. Default is 0, which means \n'
                     'PyCurt will run linearly.'), font=("Courier 10 Pitch", 20)),
    sg.InputText(0, key='cores', size=(20, 10), font=("Courier 10 Pitch", 20))],
    [sg.Checkbox('Data sorting', change_submits = True, enable_events=True, size=(20, 1),
                 default=True, key='data_sorting', disabled=data_sorting, font=("Courier 10 Pitch", 20),
                 tooltip=('Whether or not to perform data sorting before curation.\n'
                 'Default is True. N.B. if this is set to False, then PyCurt expects \n'
                 'that the input folder has is the output of a previously ran data \n'
                 'sorting, i.e. the input folder cannot have a custom structure.')),
    sg.Checkbox('Renaming', change_submits = True, enable_events=True, font=("Courier 10 Pitch", 20),
                 default=False, key='renaming', disabled=data_sorting,
                 tooltip=('If "Data sorting" is selected, there is the option to rename \n'
                          'the subjects based on the information in the DICOM headers. \n'
                          'However this is not always accurate and if the field "PatientID" \n'
                          'is missing then there will be an error. Default it False.')),
    sg.Text('Subject name position', size=(25, 1), auto_size_text=False, justification='right',
            tooltip=('If "Data sorting" is selected, and "Renaming" is False, then you have \n'
                     ' to specify the position of the subject ID in the image path \n '
                     '(assuming it will be the same for all the files). For example, the \n'
                     'position in the file called /mnt/sdb/tosort/sub1/session1/image.dcm, \n'
                     'will be 3 (or -3, remember that in Python numbering starts from 0). \n'
                     'By default, it is the third position starting from the end of the path \n'
                     'i.e. -3.'), font=("Courier 10 Pitch", 20)),
    sg.InputText(-3, key='sn_pos', disabled = data_sorting,
                 size=(15, 10), font=("Courier 10 Pitch", 20))],
    [sg.Checkbox('Data curation', change_submits = True, enable_events=True, size=(20, 1),
                 default=True, key='data_curation', disabled=data_sorting, font=("Courier 10 Pitch", 20),
                 tooltip=('Whether or not to perform data curation after sorting.\n'
                 'This step converts and checks all the imaging data to NIFTI_GZ. \n')),
    sg.Checkbox('Run MR images classification', change_submits = True, enable_events=True, size=(30, 1),
                 default=True, key='mrclass', disabled=data_sorting, font=("Courier 10 Pitch", 20),
                 tooltip=('Whether or not to perform MR images classification into 6 possible \n'
                          'classes: T1, CT1, T2, FLAIR, ADC or SWI. All the images that cannot be\n'
                          'classified will be ignored.'))],
    ]
layout = [
    [sg.Text('PyCURT - Python-based automated data CUration Workflow for RadioTherapy data\n',
             size=(80, 1), font=("Courier 10 Pitch", 24, 'bold'), justification='l')],
    [sg.Frame('Workflow parameters', input_layout, font=("Courier 10 Pitch", 22), title_color='black')],
    [sg.Text('_'  * 150)],
    [sg.Submit(font=("Courier 10 Pitch", 20)), sg.Quit(font=("Courier 10 Pitch", 20))]
    ]

main_window = sg.Window('PyCurt - Main').Layout(layout)
while True:
    main_button, values = main_window.Read()
    if not values['data_sorting']:
        main_window['sn_pos'].Update(disabled = True)
        main_window['renaming'].Update(disabled = True)
    else:
        main_window['renaming'].Update(disabled = False)
        if values['renaming']:
            main_window['sn_pos'].Update(disabled = True)
        else:
            main_window['sn_pos'].Update(disabled = False)
    if main_button == 'Quit':
        sys.exit()
    elif main_button == 'Submit':
        BASE_DIR = values['in_path']
        
        sub_list, BASE_DIR = create_subject_list(BASE_DIR)
        
        if values['data_sorting']:
            if values['mrclass']:
                checkpoints, sub_checkpoints = download_mrclass_weights()
            else:
                checkpoints = None
                sub_checkpoints = None

            workflow = DataCuration(
                sub_id='', input_dir=BASE_DIR, work_dir=values['work_dir'],
                process_rt=True)
            wf = workflow.workflow_setup(
                data_sorting=True, subject_name_position=int(values['sn_pos']),
                renaming=values['renaming'], mr_classiffication=values['mrclass'],
                checkpoints=checkpoints, sub_checkpoints=sub_checkpoints)
            workflow.runner(wf, cores=int(values['cores']))
            BASE_DIR = os.path.join(values['work_dir'], 'workflows_output', 'Sorted_Data')
            sub_list = os.listdir(BASE_DIR)
        
        if values['data_curation']:
            for sub_id in sub_list:
            
                print('Processing subject {}'.format(sub_id))
            
                workflow = DataCuration(
                    sub_id=sub_id, input_dir=BASE_DIR, work_dir=values['work_dir'],
                    process_rt=True)
                wf = workflow.workflow_setup()
                workflow.runner(wf, cores=int(values['cores']))
        
        print('Done!')
