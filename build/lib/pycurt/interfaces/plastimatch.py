from nipype.interfaces.base import (
    TraitedSpec, traits, File, CommandLineInputSpec, CommandLine)
import os.path as op
from nipype.interfaces.base import isdefined


class DoseConverterInputSpecs(CommandLineInputSpec):
    
    input_dose = File(mandatory=True, exists=True, argstr='--input %s',
                      desc='Dose DICOM file.')
    out_name = traits.Str('dose.nii.gz', usedefault=True,
                          argstr='--output-dose-img %s', desc='Output name. '
                          'Default is dose.nii.gz.')


class DoseConverterOutputSpec(TraitedSpec):
    
    out_file = File(exists=True, desc='Converted dose file.')


class DoseConverter(CommandLine):
    
    _cmd = 'plastimatch convert'
    input_spec = DoseConverterInputSpecs
    output_spec = DoseConverterOutputSpec
    
    def _list_outputs(self):
        outputs = self._outputs().get()
        if isdefined(self.inputs.out_name):
            outputs['out_file'] = op.abspath(self.inputs.out_name)

        return outputs