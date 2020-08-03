import os
import subprocess as sp
import collections
import copy
import pickle


class LocalDatabase():
    
    def __init__(self, project_id=None, local_basedir=''):

        self.local_basedir = local_basedir

        if not os.path.isdir(local_basedir):
            os.makedirs(local_basedir)

        if project_id is None:
            project_id = input("Please enter the project ID on the Local database"
                               " you want to use: ")
        self.project_id = project_id
        
        print('Local database information:')
        print('Local path: {}'.format(local_basedir))
        print('Project ID: {}'.format(project_id))

        self.local_path = '{0}/{1}'.format(local_basedir, project_id)
        
    def check_precomputed_outputs(self, outfields, sessions, sub_id):
        
        database = self.load_database(os.path.join(self.local_path, 'database.pickle'))
        to_process = []
        if database is not None:
            sub_db = database[sub_id]
            for session in sessions:
                session_db = sub_db[session]
                not_processed_scans = [x for x in outfields if x not in session_db]
                if not_processed_scans:
                    to_process.append(session)
        
        return to_process

    def put(self, sessions, sub_folder):
        
        basepath, folder_name = os.path.split(sub_folder)

        cmd = 'rsync -rtvu {0}/database.pickle {1}'.format(self.local_path, basepath)
        self.run_rsync(cmd, ignore_error=True)

        database = dict()
        database[folder_name] = collections.defaultdict(dict)
        scans = [os.path.join(folder_name, x, y) for x in sessions
                 for y in os.listdir(os.path.join(sub_folder, x))]

        for element in scans:
            _, sess, scan = element.split('/')
            scan_name = scan.split('.')[0].lower()
            database[folder_name][sess][scan_name] = element

        scan_file = os.path.join(sub_folder, 'files_to_save_local.txt')
        with open(scan_file, 'w') as f:
            for el in scans:
                f.write(el+'\n')
            f.write('database.pickle')

        self.update_database(basepath, database, folder_name)

        cmd = 'rsync -rtvu --files-from={0} {1} {2}'.format(
            scan_file, basepath, self.local_path)
        self.run_rsync(cmd)
    
    def get(self, cache_dir, subjects=[], needed_scans=[], skip_sessions=[]):

        if not os.path.isdir(cache_dir):
            os.mkdir(cache_dir)
        cmd = 'rsync -rtvu {0}/database.pickle {1}'.format(self.local_path, cache_dir)
        self.run_rsync(cmd)

        database = self.load_database(os.path.join(cache_dir, 'database.pickle'))
        to_get = []
        for sub_id in subjects:
            if sub_id in database.keys():
                print('Subject {} found in the database'.format(sub_id))
                sessions = list(database[sub_id])
                print('Found {} session(s)'.format(len(sessions)))
                if skip_sessions:
                    sessions = [x for x in sessions if x not in skip_sessions]
                for session in sessions:
                    scans = list(database[sub_id][session])
                    if needed_scans:
                        scans = [x for x in scans if x in needed_scans]
                    for scan in scans:
                        to_get.append(database[sub_id][session][scan])

        scan_file = os.path.join(cache_dir, 'files_to_get_from_local.txt')
        with open(scan_file, 'w') as f:
            for el in to_get:
                f.write(el+'\n')
        cmd = 'rsync -rtvu --files-from={0} {1} {2}'.format(
            scan_file, self.local_path, cache_dir)
        self.run_rsync(cmd)
      
    def load_database(self, db_path):

        if os.path.isfile(db_path):
            with open(db_path, 'rb') as f:
                database = pickle.load(f)
        else:
            database = None
        
        return database

    def update_database(self, basepath, new_db, folder_name):

        database = self.load_database(os.path.join(basepath, 'database.pickle'))

        if database is not None:
            if folder_name not in database.keys():
                database[folder_name] = collections.defaultdict(dict)
            for session_name in new_db[folder_name].keys():
                database[folder_name][session_name].update(
                    new_db[folder_name][session_name])
        else:
            database = copy.deepcopy(new_db)
        
        with open(os.path.join(basepath, 'database.pickle'), 'wb') as f:
            pickle.dump(database, f)

    def run_rsync(self, cmd, ignore_error=False):

        try:
            sp.check_output(cmd, shell=True)
        except sp.CalledProcessError:
            if not ignore_error:
                raise Exception('rsync failed to perform the requested action. '
                                'Please try again later.')

    def get_subject_list(self, basepath):

        if not os.path.isdir(basepath):
            os.makedirs(basepath)
        cmd = 'rsync -rtvu {0}/database.pickle {1}'.format(self.local_path, basepath)
        self.run_rsync(cmd, ignore_error=True)
        
        database = self.load_database(os.path.join(basepath, 'database.pickle'))
        if database is not None:
            sub_list = list(database.keys())
        else:
            sub_list = []

        return sub_list
