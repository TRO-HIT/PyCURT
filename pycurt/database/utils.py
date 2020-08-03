import os


def check_cache(sessions, xnat_scans, sub_id, base_dir):
    
    skip_sessions = []
    for session in sessions:
        avail_scan_names = list(set([x.split('.')[0] for x in 
                            os.listdir(os.path.join(base_dir, sub_id, session))]))
        not_downloaded = [x for x in xnat_scans if x not in avail_scan_names]
        if not not_downloaded:
            skip_sessions.append(session)
    
    return skip_sessions