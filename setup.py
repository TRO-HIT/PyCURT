from setuptools import setup, find_packages

setup(name='PyCURT',
      version='1.0',
      description='Python-based automated data CUration Workflow for RadioTherapy data',
      url='https://github.com/TRO-HIT/PyCURT.git',
      python_requires='>=3.5',
      author='Francesco Sforazzini',
      author_email='f.sforazzini@dkfz.de',
      license='Apache 2.0',
      zip_safe=False,
      install_requires=[
      'matplotlib==3.0.2',
      'nibabel==2.3.3',
      'numpy==1.16.0',
      'pandas==0.24.0',
      'pydicom==1.2.2',
      'pynrrd==0.3.6',
      'nipype==1.2.0',
      'PySimpleGUI==4.26.0',
      'torch==1.4.0',
      'torchvision==0.5.0',
      'scikit-image==0.16.2',
      'opencv-python==4.2.0.34'
      ],
      packages=find_packages(exclude=['*.tests', '*.tests.*', 'tests.*', 'tests']),
      classifiers=[
          'Intended Audience :: Science/Research',
          'Programming Language :: Python',
          'Topic :: Scientific/Engineering',
          'Operating System :: Unix'
      ]
      )
