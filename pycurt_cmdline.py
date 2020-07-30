"Script to run the PyCURT from command line"
import os
import argparse
from pycurt.workflows.curation import DataCuration
from pycurt.utils.config import create_subject_list, download_mrclass_weights


if __name__ == "__main__":

    PARSER = argparse.ArgumentParser()
    
    PARSER.add_argument('--input_dir', '-i', type=str,
                        help=('Exisisting directory with the subject(s) to process'))
    PARSER.add_argument('--work_dir', '-w', type=str,
                        help=('Directory where to store the results.'))
    PARSER.add_argument('--num-cores', '-nc', type=int, default=0,
                        help=('Number of cores to use to run the registration workflow '
                              'in parallel. Default is 0, which means the workflow '
                              'will run linearly.'))
    PARSER.add_argument('--data_sorting', '-ds', action='store_true',
                        help=('Whether or not to sort the data before convertion. '
                              'Default is False'))
    PARSER.add_argument('--no-data_curation', '-ndc', action='store_true',
                        help=('Whether or not to run data curation after sorting. '
                              'By default it will run.'))
    PARSER.add_argument('--no-mrclass', '-nmc', action='store_true',
                        help=('Whether or not to classify MR images using MRClass. '
                              'By default it will run.'))
    PARSER.add_argument('--renaming', action='store_true', 
                        help='Whether or not to use the information stored'
                           'in the DICOM header to rename the subject and sessions '
                           'folders. If False, the file path will be splitted '
                           'and the subject name will be taken from there. In this '
                           'case, the subject-name-position must be provided.'
                           'Default is False.')
    PARSER.add_argument('--subject-name-position', '-np', type=int, default=-3,
                        help=('If renaming is False, the position of the subject ID '
                              'in the image path has to be specified (assuming it will'
                              ' be the same for all the files). For example, '
                              'the position in the file called /mnt/sdb/tosort/sub1/'
                              'session1/image.dcm, will be 3 (or -3, remember that in Python'
                              ' numbering starts from 0). By default, is the third'
                              ' position starting from the end of the path.'))

    ARGS = PARSER.parse_args()

    BASE_DIR = ARGS.input_dir

    sub_list, BASE_DIR = create_subject_list(BASE_DIR, ARGS.xnat_source,
                                             ARGS.cluster_source,
                                             subjects_to_process=[])

    if ARGS.data_sorting:
        if not ARGS.no_mrclass:
            checkpoints, sub_checkpoints = download_mrclass_weights()
        else:
            checkpoints = None
            sub_checkpoints = None

        workflow = DataCuration(
            sub_id='', input_dir=BASE_DIR, work_dir=ARGS.work_dir,
            process_rt=True)
        wf = workflow.workflow_setup(
            data_sorting=True, subject_name_position=ARGS.subject_name_position,
            renaming=ARGS.renaming, mr_classiffication=not ARGS.no_mrclass,
            checkpoints=checkpoints, sub_checkpoints=sub_checkpoints)
        workflow.runner(wf, cores=ARGS.num_cores)
        BASE_DIR = os.path.join(ARGS.work_dir, 'workflows_output', 'Sorted_Data')
        sub_list = os.listdir(BASE_DIR)

    if not ARGS.no_data_curation:
        for sub_id in sub_list:
    
            print('Processing subject {}'.format(sub_id))
    
            workflow = DataCuration(
                sub_id=sub_id, input_dir=BASE_DIR, work_dir=ARGS.work_dir,
                process_rt=True)
            wf = workflow.workflow_setup()
            workflow.runner(wf, cores=ARGS.num_cores)

    print('Done!')
