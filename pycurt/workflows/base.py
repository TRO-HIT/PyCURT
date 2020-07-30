from pycurt.database.base import BaseDatabase

class BaseWorkflow(BaseDatabase):

    def datasource(self):

        self.database()
        self.data_source = self.create_datasource()

    def workflow(self):
        raise NotImplementedError
    
    def workflow_setup(self):
        return self.workflow()

    def runner(self, workflow, cores=0):

        if cores == 0:
            print('Workflow will run linearly')
            workflow.run()
        else:
            print('Workflow will run in parallel using {} cores'.format(cores))
            workflow.run(plugin='MultiProc', plugin_args={'n_procs' : cores})
    