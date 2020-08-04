import os
import pandas as pd
import math
import glob
import shutil
from pathlib import Path


ALLOWED_EXT = ['.xlsx', '.csv']
ILLEGAL_CHARACTERS = ['/', '(', ')', '[', ']', '{', '}', ' ', '-']


def split_filename(fname):
    """Split a filename into parts: path, base filename and extension.
    Parameters
    ----------
    fname : str
        file or path name
    Returns
    -------
    pth : str
        base path from fname
    fname : str
        filename from fname, without extension
    ext : str
        file extension from fname
    """

    special_extensions = [".nii.gz", ".tar.gz", ".niml.dset"]

    pth = os.path.dirname(fname)
    fname = os.path.basename(fname)

    ext = None
    for special_ext in special_extensions:
        ext_len = len(special_ext)
        if (len(fname) > ext_len) and \
                (fname[-ext_len:].lower() == special_ext.lower()):
            ext = fname[-ext_len:]
            fname = fname[:-ext_len]
            break
    if not ext:
        fname, ext = os.path.splitext(fname)

    return pth, fname, ext


def batch_processing(input_data, key_col1='subjects', key_col2='masks', root=''):
    """Function to process the data in batch mode. It will take a .csv or .xlsx file with
    two columns. The first one called 'subjects' contains all the paths to the raw_data folders
    (one path per raw); the second one called 'masks' contains all the corresponding paths to 
    the segmented mask folders. 
    Parameters
    ----------
    input_data : str
        Excel or CSV file
    root : str
        (optional) root path to pre-pend to each subject and mask in the input_data file
    Returns
    -------
    raw_data : list
        list with all the subjects to process
    masks : list
        list with the corresponding mask to use to extract the features
    """
    if os.path.isfile(input_data):
        _, _, ext = split_filename(input_data)
        if ext not in ALLOWED_EXT:
            raise Exception('The file extension of the specified input file ({}) is not supported.'
                            ' The allowed extensions are: .xlsx or .csv')
        if ext == '.xlsx':
            files = pd.read_excel(input_data)
        elif ext == '.csv':
            files = pd.read_csv(input_data)
        files=files.dropna()
        try:
            masks = [os.path.join(root, str(x)) for x in list(files[key_col2])]
        except KeyError:
            print('No "masks" column found in the excel sheet. The cropping, if selected, will be performed without it.')
            masks = None
        raw_data = [os.path.join(root, str(x)) for x in list(files[key_col1])] 

        return raw_data, masks


def mergedict(a, b):
    a.update(b)
    return a


def extract_middleSlice(image):
    
    x, y, z = image.shape
    s = smallest(x,y,z)
    if s == z:
        ms = math.ceil(image.shape[2]/2)-1
        return image[:, :, ms].astype('float32')
    elif s == y:
        ms = math.ceil(image.shape[1]/2)-1
        return image[:, ms, :].astype('float32')
    else:
        ms = math.ceil(image.shape[0]/2)-1
        return image[ms, :, :].astype('float32')


def smallest(num1, num2, num3):
    
    if (num1 < num2) and (num1 < num3):
        smallest_num = num1
    elif (num2 < num1) and (num2 < num3):
        smallest_num = num2
    else:
        smallest_num = num3
    return smallest_num


def label_move_image(image, modality, out_dir, renaming=True):

    sub_name, tp = image.split('/')[-3:-1]
    base_dir_path = os.path.join(out_dir, sub_name, tp)
    dir_name = os.path.join(base_dir_path, modality)
    if not os.path.isdir(dir_name):
        os.makedirs(dir_name)
    if renaming:
        new_name = file_rename(image)
    else:
        new_name = image
    try:
        shutil.copytree(new_name, os.path.join(dir_name, new_name.split('/')[-1]))
        outname = os.path.join(dir_name, new_name.split('/')[-1])
    except:
        files = [item for item in glob.glob(dir_name+'/*')
                 if new_name.split('/')[-1] in item ]
        if len(files) == 1:
            new_name1 = new_name+'_1'
        else:
            new_name1 = new_name+'_'+ str(int(len(files)))
        # Renaming old directory
        shutil.move(new_name, new_name1)  
        # Copy to the sorting location  
        shutil.copytree(new_name1, os.path.join(dir_name, new_name1.split('/')[-1]))
        outname = os.path.join(dir_name, new_name1.split('/')[-1])
        new_name = new_name1
    
    return outname, new_name

def file_rename(image):

    base_dir_path = os.path.split(image)[0]
    name = image.split('/')[-1]
    name_parts = name.split('-')
    if not name_parts[0]:
        new_name = os.path.join(base_dir_path, 'image')
        shutil.move(image, new_name)
    elif len(name_parts) > 1:
        if os.path.isdir(os.path.join(base_dir_path, name_parts[0])):
            new_name = os.path.join(base_dir_path, name_parts[0][:-1])
        else:
            new_name = os.path.join(base_dir_path, name_parts[0])
        shutil.move(image, new_name)
    else:
        new_name = image
    return new_name


def create_move_toDir(fileName, dirName, actRange):
    
    folderName=Path(fileName[0:-7])
    indices = [i for i, x in enumerate(folderName.parts[-1]) if x == "-"]
    indices2=[i for i, x in enumerate(dirName) if x == "/"]
    
    if not os.path.exists(dirName) and not os.path.isdir(dirName):
        os.makedirs(dirName)
        print(folderName)
        print(indices)
        try:
            newName = os.path.join(dirName[0:indices2[-1]],
                                   '1-'+ folderName.parts[-1][0:indices[0]]+'-'+str(actRange))
        except IndexError:
            newName = os.path.join(dirName[0:indices2[-1]],
                                   '1-'+ folderName.parts[-1]+'-'+str(actRange))
       
    else:
        f = [item for item in os.listdir(dirName) if '1-' in item]
        if len(f) > 1:
            [f.remove(x) for x in f if len(x.split('-')) != 3]
        if len(f) > 1:
            for ff in f[1:]:
                if os.path.isfile(ff):
                    os.remove(ff)
        indices3 = [i for i, x in enumerate(f[0]) if x == "-"]
        actRange_f = float(f[0][indices3[-1]+1:])
#         actRange_f = sorted([float(x[indices3[-1]+1:]) for x in f])[0]

        if actRange>actRange_f:
            try:
                newName=os.path.join(dirName[0:indices2[-1]],
                                     '1-'+ folderName.parts[-1][0:indices[0]]+'-'+str(actRange))
            except:
                newName=os.path.join(dirName[0:indices2[-1]],
                                     '1-'+ folderName.parts[-1]+'-'+str(actRange))
            if not os.path.isdir(os.path.join(dirName,f[0][indices3[0]+1:])):
                shutil.move(os.path.join(dirName,f[0]),
                            os.path.join(dirName,f[0][indices3[0]+1:]))
            else:
                shutil.move(os.path.join(dirName,f[0]),
                            os.path.join(dirName,f[0][indices3[0]+1:]+'_1'))
          
        elif actRange <= actRange_f:
            try:
                newName=os.path.join(dirName[0:indices2[-1]],
                                     folderName.parts[-1][0:indices[0]]+'-'+str(actRange))
            except IndexError:
                newName=os.path.join(dirName[0:indices2[-1]],
                                     folderName.parts[-1]+'-'+str(actRange))
#     shutil.move(fileName[0:-7],newName)
    shutil.copytree(fileName[0:-7], newName)
    try:
        shutil.move(newName, dirName)
    except:
        files=[item for item in glob.glob(dirName+'/*') if newName.split('/')[-1] in item ]
        if len(files) == 1:
            newName1=newName+'_1'
        else:
            newName1=newName+'_'+ str(int(len(files)))
            
        shutil.move(newName, newName1)    
        shutil.move(newName1, dirName)
