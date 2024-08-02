from setuptools import setup, find_packages

setup(name='PyCURT',
      version='1.0',
      description='Python-based automated data CUration Workflow for RadioTherapy data',
      url='https://github.com/TRO-HIT/PyCURT.git',
      python_requires='>=3.9',
      author='Francesco Sforazzini',
      author_email='f.sforazzini@dkfz.de',
      license='Apache 2.0',
      zip_safe=False,
      include_package_data=True,
      install_requires=[
      'matplotlib>=3.9',
      'nibabel>=5.2',
      'numpy>=1.26',
      'pandas>=2.2',
      'pydicom>=2.4',
      'pynrrd>=1.0',
      'FreeSimpleGUI>=5.1',
      'torch>=2.3',
      'torchvision>=0.18',
      'scikit-image>=0.24',
      'opencv-python>=4.10',
      'requests>=2.32',
      'SimpleITK>=2.3',
      'nipype>=1.8'],
      data_files=[('resources', ['resources/random.nii.gz'])],
      dependency_links=['git+https://github.com/TRO-HIT/nipype.git@c453eac5d7efdd4e19a9bcc8a7f3d800026cc125#egg=nipype-9876543210'],
      entry_points={
          'console_scripts': ['pycurt_gui = scripts.pycurt_gui:main',
			      'pycurt = scripts.pycurt_cmdline:main']},
      packages=find_packages(exclude=['*.tests', '*.tests.*', 'tests.*', 'tests']),
      classifiers=[
          'Intended Audience :: Science/Research',
          'Programming Language :: Python',
          'Topic :: Scientific/Engineering',
          'Operating System :: Unix'
      ]
      )
