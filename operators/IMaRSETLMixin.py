from os import makedirs

import imars_etl

from imars_dags.util.etl_tools.tmp_file import tmp_filepath
from imars_dags.util.etl_tools.load import load_task
from imars_dags.util.etl_tools.cleanup import _cleanup_tmp_file


class IMaRSETLMixin(object):
    """
    # =========================================================================
    # === "Transform" operator that "Extracts" & "Loads" auto-magically.
    # =========================================================================
    Leverages IMaRS ETL tools (https://github.com/usf-imars/imars-etl) to:
        * find & "Extract" input files by metadata
        * "Load" & cleanup output files & autofill (some) metadata

    inputs, outputs, and tmpdirs get injected into context['params'] so you
    can template with them as if they were passed into params.

    __init__ parameters:
    -------------------
    inputs : dict of strings
        Mapping of input keys (use like tmp filenames) to metadata SQL queries.
        Files are automatically extracted from the database & injected into
        context['params'] so you can template with them. Downloaded files
        are automatically cleaned up.
    outputs : dict of dicts
        Mapping of output keys (use like tmp filenames) to output metdata to
        be loaded into the data warehouse. Output files are automatically
        loaded into the warehouse and cleaned up after load finishes.
        The following metadata is automatically added to the output product:
            {
                "filepath": "{{ the_given_output_key }}",
                # TODO: more?
            }
    tmpdirs : str[]
        List of tmp directories to be created before run. The tmp dirs are
        automatically created and cleaned up after the job is done.
    """
    # =================== subclass helper methods ============================
    def pre_init(self, inputs, outputs, tmpdirs, dag):
        """
        Does generic handling of args.
        Should be the first line in a subclass's __init__() definition.
        """
        self.inputs = inputs
        self.outputs = outputs
        self.tmpdirs = tmpdirs

        self.tmp_paths = {}
        self.tmp_dirs = []
        for inpf in self.inputs:
            self.tmp_paths[inpf] = tmp_filepath(dag.dag_id, inpf)
        for outkey in self.outputs:
            self.tmp_paths[outkey] = tmp_filepath(dag.dag_id, outkey)
        for tdir in self.tmpdirs:
            self.tmp_paths[tdir] = tmp_filepath(dag.dag_id, tdir)
            # NOTE: using tmp_filepath here instead of tmp_fildir because we do
            #   not want the auto-added mkdir operator.

    # =======================================================================
    # =================== BaseOperator Overrides ============================
    def render_template(self, attr, content, context):
        print("adding paths to context:\n\t{}".format(self.tmp_paths))
        # inject tmp_paths into context params so we can template with them
        # print("\n-----\nctx:\n\t{}\n----\n".format(context))
        for path_key, path_val in self.tmp_paths.items():
            context['params'].setdefault(
                path_key,
                # double-render the path_val (so we can use use macros like
                #   {{ts_nodash}} in the tmp_paths.
                super(IMaRSETLMixin, self).render_template(
                    attr, path_val, context
                )
            )
        return super(IMaRSETLMixin, self).render_template(
            attr, content, context
        )

    def pre_execute(self, context):
        # TODO: check metadta for output already exists?
        self.render_all_paths(context)
        super(IMaRSETLMixin, self).pre_execute(context)

    def execute(self, context):
        # TODO: use pre_execute and post_execute instead ?
        # https://airflow.apache.org/code.html#airflow.models.BaseOperator.post_execute
        try:
            self.create_tmpdirs()
            self.extract_inputs(context)
            super(IMaRSETLMixin, self).execute(context)
            self.load_outputs(context)
        finally:
            self.cleanup()

    # =======================================================================
    # ====================== "private" methods ==============================
    def render_all_paths(self, context):
        # basically double-renders the path_val (so we can use use macros like
        #   {{ts_nodash}} in the tmp_paths.
        for pathkey, pathval in self.tmp_paths.items():
            rendered_pathval = self.render_template(
                '',
                pathval,
                context
            )
            self.tmp_paths[pathkey] = rendered_pathval

    def create_tmpdirs(self):
        print("creating tmpdirs...")
        for tdir in self.tmpdirs:
            tmp_dir_path = self.tmp_paths[tdir]
            print("{}=>{}".format(tdir, tmp_dir_path))
            makedirs(tmp_dir_path)

    def _render_input_metadata(self, metadata, context):
        attr = ""
        return self.render_template(attr, metadata, context)

    def extract_inputs(self, context):
        print("extracting input files from IMaRS data warehouse...")
        for inpf in self.inputs:
            metadata = self._render_input_metadata(self.inputs[inpf], context)
            out_path = self.tmp_paths[inpf]
            print("{}\n\t->\t{}\n\t->\t{}\n\t->\t".format(
                inpf, metadata, out_path
            ))
            imars_etl.extract(
                sql=metadata,
                output_path=out_path
            )

    def _render_output_metadata(self, metadata, context):
        attr = ""
        for key, val in metadata.items():
            metadata[key] = self.render_template(attr, val, context)
        return metadata

    def load_outputs(self, context):
        print("loading output files into IMaRS data warehouse...")
        for outf in self.outputs:
            load_args = self.outputs[outf]
            output_path = self.tmp_paths[outf]
            load_args['filepath'] = output_path
            load_args = self._render_output_metadata(load_args, context)
            print("{}\n\t->\t{}\n\t->\t{}\n\t->\t".format(
                outf, output_path, load_args
            ))
            load_task(load_args, self)

    def cleanup(self):
        print("cleaning up temporary files...")
        for fkey, tmpf in self.tmp_paths.items():
            print("cleanup {} ({})".format(fkey, tmpf))
            _cleanup_tmp_file(tmpf)
    # =======================================================================
