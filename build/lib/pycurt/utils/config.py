import os


def create_subject_list(base_dir, xnat_source=False, cluster_source=False,
                        subjects_to_process=[]):
    
    if ((os.path.isdir(base_dir) and xnat_source) or
            (os.path.isdir(base_dir) and cluster_source) or
            os.path.isdir(base_dir)):
        sub_list = [x for x in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, x))]
        if subjects_to_process:
            sub_list = [x for x in sub_list if x in subjects_to_process]

    return sub_list, base_dir
