from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Exclusive(Enum):
    user = "user"
    mcs = "mcs"
    true = "true"
    false = "false"


class GresFlags(Enum):
    disable_binding = "disable-binding"
    enforce_binding = "enforce-binding"


class OpenMode(Enum):
    append = "append"
    truncate = "truncate"


class Error(BaseModel):
    error: Optional[str] = Field(None, description="error message")
    errno: Optional[int] = Field(None, description="error number")


class JobProperties(BaseModel):
    class Config:
        use_enum_values = True

    account: Optional[str] = Field(
        None, description="Charge resources used by this job to specified account."
    )
    account_gather_freqency: Optional[str] = Field(
        None, description="Define the job accounting and profiling sampling intervals."
    )
    argv: Optional[List[str]] = Field(None, description="Arguments to the script.")
    array: Optional[str] = Field(
        None,
        description="Submit a job array, multiple jobs to be executed with identical parameters. The indexes specification identifies what array index values should be used.",
    )
    batch_features: Optional[str] = Field(
        None, description="features required for batch script's node"
    )
    begin_time: Optional[str] = Field(
        None,
        description="Submit the batch script to the Slurm controller immediately, like normal, but tell the controller to defer the allocation of the job until the specified time.",
    )
    burst_buffer: Optional[str] = Field(None, description="Burst buffer specification.")
    cluster_constraints: Optional[str] = Field(
        None,
        description="Specifies features that a federated cluster must have to have a sibling job submitted to it.",
    )
    comment: Optional[str] = Field(None, description="An arbitrary comment.")
    constraints: Optional[str] = Field(
        None, description="node features required by job."
    )
    core_specification: Optional[int] = Field(
        None,
        description="Count of specialized threads per node reserved by the job for system operations and not used by the application.",
    )
    cores_per_socket: Optional[int] = Field(
        None,
        description="Restrict node selection to nodes with at least the specified number of cores per socket.",
    )
    cpu_binding: Optional[str] = Field(None, description="Cpu binding")
    cpu_binding_hint: Optional[str] = Field(None, description="Cpu binding hint")
    cpu_frequency: Optional[str] = Field(
        None,
        description="Request that job steps initiated by srun commands inside this sbatch script be run at some requested frequency if possible, on the CPUs selected for the step on the compute node(s).",
    )
    cpus_per_gpu: Optional[str] = Field(
        None, description="Number of CPUs requested per allocated GPU."
    )
    cpus_per_task: Optional[int] = Field(
        None,
        description="Advise the Slurm controller that ensuing job steps will require ncpus number of processors per task.",
    )
    current_working_directory: Optional[str] = Field(
        None,
        description="Instruct Slurm to connect the batch script's standard output directly to the file name.",
    )
    deadline: Optional[str] = Field(
        None,
        description="Remove the job if no ending is possible before this deadline (start > (deadline - time[-min])).",
    )
    delay_boot: Optional[int] = Field(
        None,
        description="Do not reboot nodes in order to satisfied this job's feature specification if the job has been eligible to run for less than this time period.",
    )
    dependency: Optional[str] = Field(
        None,
        description="Defer the start of this job until the specified dependencies have been satisfied completed.",
    )
    distribution: Optional[str] = Field(
        None, description="Specify alternate distribution methods for remote processes."
    )
    environment: Dict[str, Any] = Field(
        ..., description="Dictionary of environment entries."
    )
    exclusive: Optional[Exclusive] = Field(
        None,
        description='The job allocation can share nodes just other users with the "user" option or with the "mcs" option).',
    )
    get_user_environment: Optional[bool] = Field(
        None, description="Load new login environment for user on job node."
    )
    gres: Optional[str] = Field(
        None,
        description="Specifies a comma delimited list of generic consumable resources.",
    )
    gres_flags: Optional[GresFlags] = Field(
        None, description="Specify generic resource task binding options."
    )
    gpu_binding: Optional[str] = Field(
        None, description="Requested binding of tasks to GPU."
    )
    gpu_frequency: Optional[str] = Field(None, description="Requested GPU frequency.")
    gpus: Optional[str] = Field(None, description="GPUs per job.")
    gpus_per_node: Optional[str] = Field(None, description="GPUs per node.")
    gpus_per_socket: Optional[str] = Field(None, description="GPUs per socket.")
    gpus_per_task: Optional[str] = Field(None, description="GPUs per task.")
    hold: Optional[bool] = Field(
        None,
        description="Specify the job is to be submitted in a held state (priority of zero).",
    )
    kill_on_invalid_dependency: Optional[bool] = Field(
        None,
        description="If a job has an invalid dependency, then Slurm is to terminate it.",
    )
    licenses: Optional[str] = Field(
        None,
        description="Specification of licenses (or other resources available on all nodes of the cluster) which must be allocated to this job.",
    )
    mail_type: Optional[str] = Field(
        None, description="Notify user by email when certain event types occur."
    )
    mail_user: Optional[str] = Field(
        None,
        description="User to receive email notification of state changes as defined by mail_type.",
    )
    mcs_label: Optional[str] = Field(
        None, description="This parameter is a group among the groups of the user."
    )
    memory_binding: Optional[str] = Field(None, description="Bind tasks to memory.")
    memory_per_cpu: Optional[int] = Field(
        None, description="Minimum real memory per cpu (MB)."
    )
    memory_per_gpu: Optional[int] = Field(
        None, description="Minimum memory required per allocated GPU."
    )
    memory_per_node: Optional[int] = Field(
        None, description="Minimum real memory per node (MB)."
    )
    minimum_cpus_per_node: Optional[int] = Field(
        None, description="Minimum number of CPUs per node."
    )
    minimum_nodes: Optional[bool] = Field(
        None,
        description="If a range of node counts is given, prefer the smaller count.",
    )
    name: Optional[str] = Field(
        None, description="Specify a name for the job allocation."
    )
    nice: Optional[str] = Field(
        None,
        description="Run the job with an adjusted scheduling priority within Slurm.",
    )
    no_kill: Optional[bool] = Field(
        None,
        description="Do not automatically terminate a job if one of the nodes it has been allocated fails.",
    )
    nodes: Optional[List[int]] = Field(
        None,
        description="Request that a minimum of minnodes nodes and a maximum node count.",
        max_items=2,
        # min_items=1, XXX
        min_items=2,
    )
    open_mode: Optional[OpenMode] = Field(
        "append",
        description="Open the output and error files using append or truncate mode as specified.",
    )
    partition: Optional[str] = Field(
        None, description="Request a specific partition for the resource allocation."
    )
    priority: Optional[str] = Field(
        None, description="Request a specific job priority."
    )
    qos: Optional[str] = Field(
        None, description="Request a quality of service for the job."
    )
    requeue: Optional[bool] = Field(
        None,
        description="Specifies that the batch job should eligible to being requeue.",
    )
    reservation: Optional[str] = Field(
        None, description="Allocate resources for the job from the named reservation."
    )
    signal: Optional[str] = Field(
        None,
        description="When a job is within sig_time seconds of its end time, send it the signal sig_num.",
        regex="[B:]<sig_num>[@<sig_time>]",
    )
    sockets_per_node: Optional[int] = Field(
        None,
        description="Restrict node selection to nodes with at least the specified number of sockets.",
    )
    spread_job: Optional[bool] = Field(
        None,
        description="Spread the job allocation over as many nodes as possible and attempt to evenly distribute tasks across the allocated nodes.",
    )
    standard_error: Optional[str] = Field(
        None,
        description="Instruct Slurm to connect the batch script's standard error directly to the file name.",
    )
    standard_in: Optional[str] = Field(
        None,
        description="Instruct Slurm to connect the batch script's standard input directly to the file name specified.",
    )
    standard_out: Optional[str] = Field(
        None,
        description="Instruct Slurm to connect the batch script's standard output directly to the file name.",
    )
    tasks: Optional[int] = Field(
        None,
        description="Advises the Slurm controller that job steps run within the allocation will launch a maximum of number tasks and to provide for sufficient resources.",
    )
    tasks_per_core: Optional[int] = Field(
        None, description="Request the maximum ntasks be invoked on each core."
    )
    tasks_per_node: Optional[int] = Field(
        None, description="Request the maximum ntasks be invoked on each node."
    )
    tasks_per_socket: Optional[int] = Field(
        None, description="Request the maximum ntasks be invoked on each socket."
    )
    thread_specification: Optional[int] = Field(
        None,
        description="Count of specialized threads per node reserved by the job for system operations and not used by the application.",
    )
    threads_per_core: Optional[int] = Field(
        None,
        description="Restrict node selection to nodes with at least the specified number of threads per core.",
    )
    time_limit: Optional[int] = Field(None, description="Step time limit.")
    time_minimum: Optional[int] = Field(
        None, description="Minimum run time in minutes."
    )
    wait_all_nodes: Optional[bool] = Field(
        None, description="Do not begin execution until all nodes are ready for use."
    )
    wckey: Optional[str] = Field(None, description="Specify wckey to be used with job.")


class JobSubmission(BaseModel):
    script: str = Field(
        ..., description="Executable script (full contents) to run in batch step"
    )
    job: Optional[JobProperties] = Field(
        None, description="Properties of an array job or non-HetJob"
    )
    jobs: Optional[List[JobProperties]] = Field(
        None, description="Properties of an HetJob"
    )


class JobSubmissionResponse(BaseModel):
    errors: Optional[List[Error]] = Field(None, description="slurm errors")
    job_id: Optional[int] = Field(None, description="new job ID")
    step_id: Optional[str] = Field(None, description="new job step ID")
    job_submit_user_msg: Optional[str] = Field(
        None, description="Message to user from job_submit plugin"
    )


class NodeAllocation(BaseModel):
    memory: Optional[int] = Field(None, description="amount of assigned job memory")
    cpus: Optional[int] = Field(None, description="amount of assigned job CPUs")
    sockets: Optional[Dict[str, Any]] = Field(
        None, description="assignment status of each socket by socket id"
    )
    cores: Optional[Dict[str, Any]] = Field(
        None, description="assignment status of each core by core id"
    )


class JobResources(BaseModel):
    nodes: Optional[str] = Field(None, description="list of assigned job nodes")
    allocated_cpus: Optional[int] = Field(
        None, description="number of assigned job cpus"
    )
    allocated_hosts: Optional[int] = Field(
        None, description="number of assigned job hosts"
    )
    allocated_nodes: Optional[Dict[str, NodeAllocation]] = Field(
        None, description="node allocations"
    )


class JobResponseProperties(BaseModel):
    account: Optional[str] = Field(
        None, description="Charge resources used by this job to specified account"
    )
    accrue_time: Optional[str] = Field(
        None, description="time job is eligible for running"
    )
    admin_comment: Optional[str] = Field(
        None, description="administrator's arbitrary comment"
    )
    array_job_id: Optional[str] = Field(
        None, description="job_id of a job array or 0 if N/A"
    )
    array_task_id: Optional[str] = Field(None, description="task_id of a job array")
    array_max_tasks: Optional[str] = Field(
        None, description="Maximum number of running array tasks"
    )
    array_task_string: Optional[str] = Field(
        None, description="string expression of task IDs in this record"
    )
    association_id: Optional[str] = Field(None, description="association id for job")
    batch_features: Optional[str] = Field(
        None, description="features required for batch script's node"
    )
    batch_flag: Optional[bool] = Field(
        None, description="if batch: queued job with script"
    )
    batch_host: Optional[str] = Field(
        None, description="name of host running batch script"
    )
    flags: Optional[List[str]] = Field(None, description="Job flags")
    burst_buffer: Optional[str] = Field(None, description="burst buffer specifications")
    burst_buffer_state: Optional[str] = Field(
        None, description="burst buffer state info"
    )
    cluster: Optional[str] = Field(
        None, description="name of cluster that the job is on"
    )
    cluster_features: Optional[str] = Field(
        None, description="comma separated list of required cluster features"
    )
    command: Optional[str] = Field(None, description="command to be executed")
    comment: Optional[str] = Field(None, description="arbitrary comment")
    contiguous: Optional[bool] = Field(
        None, description="job requires contiguous nodes"
    )
    core_spec: Optional[str] = Field(None, description="specialized core count")
    thread_spec: Optional[str] = Field(None, description="specialized thread count")
    cores_per_socket: Optional[str] = Field(
        None, description="cores per socket required by job"
    )
    billable_tres: Optional[str] = Field(None, description="billable TRES")
    cpus_per_task: Optional[str] = Field(
        None, description="number of processors required for each task"
    )
    cpu_frequency_minimum: Optional[str] = Field(
        None, description="Minimum cpu frequency"
    )
    cpu_frequency_maximum: Optional[str] = Field(
        None, description="Maximum cpu frequency"
    )
    cpu_frequency_governor: Optional[str] = Field(
        None, description="cpu frequency governor"
    )
    cpus_per_tres: Optional[str] = Field(
        None, description="semicolon delimited list of TRES=# values"
    )
    deadline: Optional[str] = Field(None, description="job start deadline ")
    delay_boot: Optional[str] = Field(None, description="command to be executed")
    dependency: Optional[str] = Field(
        None, description="synchronize job execution with other jobs"
    )
    derived_exit_code: Optional[str] = Field(
        None, description="highest exit code of all job steps"
    )
    eligible_time: Optional[str] = Field(
        None, description="time job is eligible for running"
    )
    end_time: Optional[str] = Field(
        None, description="time of termination, actual or expected"
    )
    excluded_nodes: Optional[str] = Field(
        None, description="comma separated list of excluded nodes"
    )
    exit_code: Optional[int] = Field(None, description="exit code for job")
    features: Optional[str] = Field(
        None, description="comma separated list of required features"
    )
    federation_origin: Optional[str] = Field(None, description="Origin cluster's name")
    federation_siblings_active: Optional[str] = Field(
        None, description="string of active sibling names"
    )
    federation_siblings_viable: Optional[str] = Field(
        None, description="string of viable sibling names"
    )
    gres_detail: Optional[List[str]] = Field(None, description="Job flags")
    group_id: Optional[str] = Field(None, description="group job submitted as")
    job_id: Optional[str] = Field(None, description="job ID")
    job_resources: Optional[JobResources] = None
    job_state: Optional[str] = Field(None, description="state of the job")
    last_sched_evaluation: Optional[str] = Field(
        None, description="last time job was evaluated for scheduling"
    )
    licenses: Optional[str] = Field(None, description="licenses required by the job")
    max_cpus: Optional[str] = Field(
        None, description="maximum number of cpus usable by job"
    )
    max_nodes: Optional[str] = Field(
        None, description="maximum number of nodes usable by job"
    )
    mcs_label: Optional[str] = Field(None, description="mcs_label if mcs plugin in use")
    memory_per_tres: Optional[str] = Field(
        None, description="semicolon delimited list of TRES=# values"
    )
    name: Optional[str] = Field(None, description="name of the job")
    nodes: Optional[str] = Field(None, description="list of nodes allocated to job")
    nice: Optional[str] = Field(None, description="requested priority change")
    tasks_per_core: Optional[str] = Field(
        None, description="number of tasks to invoke on each core"
    )
    tasks_per_socket: Optional[str] = Field(
        None, description="number of tasks to invoke on each socket"
    )
    tasks_per_board: Optional[str] = Field(
        None, description="number of tasks to invoke on each board"
    )
    cpus: Optional[str] = Field(
        None, description="minimum number of cpus required by job"
    )
    node_count: Optional[str] = Field(
        None, description="minimum number of nodes required by job"
    )
    tasks: Optional[str] = Field(None, description="requested task count")
    het_job_id: Optional[str] = Field(None, description="job ID of hetjob leader")
    het_job_id_set: Optional[str] = Field(
        None, description="job IDs for all components"
    )
    het_job_offset: Optional[str] = Field(
        None, description="HetJob component offset from leader"
    )
    partition: Optional[str] = Field(None, description="name of assigned partition")
    memory_per_node: Optional[str] = Field(
        None, description="minimum real memory per node"
    )
    memory_per_cpu: Optional[str] = Field(
        None, description="minimum real memory per cpu"
    )
    minimum_cpus_per_node: Optional[str] = Field(
        None, description="minimum # CPUs per node"
    )
    minimum_tmp_disk_per_node: Optional[str] = Field(
        None, description="minimum tmp disk per node"
    )
    preempt_time: Optional[str] = Field(None, description="preemption signal time")
    pre_sus_time: Optional[str] = Field(
        None, description="time job ran prior to last suspend"
    )
    priority: Optional[str] = Field(None, description="relative priority of the job")
    profile: Optional[List[str]] = Field(None, description="Job profiling requested")
    qos: Optional[str] = Field(None, description="Quality of Service")
    reboot: Optional[bool] = Field(
        None, description="node reboot requested before start"
    )
    required_nodes: Optional[str] = Field(
        None, description="comma separated list of required nodes"
    )
    requeue: Optional[bool] = Field(
        None, description="enable or disable job requeue option"
    )
    resize_time: Optional[str] = Field(None, description="time of latest size change")
    restart_cnt: Optional[str] = Field(None, description="count of job restarts")
    resv_name: Optional[str] = Field(None, description="reservation name")
    shared: Optional[str] = Field(
        None, description="type and if job can share nodes with other jobs"
    )
    show_flags: Optional[List[str]] = Field(None, description="details requested")
    sockets_per_board: Optional[str] = Field(
        None, description="sockets per board required by job"
    )
    sockets_per_node: Optional[str] = Field(
        None, description="sockets per node required by job"
    )
    start_time: Optional[str] = Field(
        None, description="time execution begins, actual or expected"
    )
    state_description: Optional[str] = Field(
        None, description="optional details for state_reason"
    )
    state_reason: Optional[str] = Field(
        None, description="reason job still pending or failed"
    )
    standard_error: Optional[str] = Field(
        None, description="pathname of job's stderr file"
    )
    standard_input: Optional[str] = Field(
        None, description="pathname of job's stdin file"
    )
    standard_output: Optional[str] = Field(
        None, description="pathname of job's stdout file"
    )
    submit_time: Optional[str] = Field(None, description="time of job submission")
    suspend_time: Optional[str] = Field(
        None, description="time job last suspended or resumed"
    )
    system_comment: Optional[str] = Field(
        None, description="slurmctld's arbitrary comment"
    )
    time_limit: Optional[str] = Field(None, description="maximum run time in minutes")
    time_minimum: Optional[str] = Field(None, description="minimum run time in minutes")
    threads_per_core: Optional[str] = Field(
        None, description="threads per core required by job"
    )
    tres_bind: Optional[str] = Field(
        None, description="Task to TRES binding directives"
    )
    tres_freq: Optional[str] = Field(None, description="TRES frequency directives")
    tres_per_job: Optional[str] = Field(
        None, description="semicolon delimited list of TRES=# values"
    )
    tres_per_node: Optional[str] = Field(
        None, description="semicolon delimited list of TRES=# values"
    )
    tres_per_socket: Optional[str] = Field(
        None, description="semicolon delimited list of TRES=# values"
    )
    tres_per_task: Optional[str] = Field(
        None, description="semicolon delimited list of TRES=# values"
    )
    tres_req_str: Optional[str] = Field(None, description="tres reqeusted in the job")
    tres_alloc_str: Optional[str] = Field(None, description="tres used in the job")
    user_id: Optional[str] = Field(None, description="user id the job runs as")
    user_name: Optional[str] = Field(None, description="user the job runs as")
    wckey: Optional[str] = Field(None, description="wckey for job")
    current_working_directory: Optional[str] = Field(
        None, description="pathname of working directory"
    )


class JobsResponse(BaseModel):
    errors: Optional[List[Error]] = Field(None, description="slurm errors")
    jobs: Optional[List[JobResponseProperties]] = Field(
        None, description="job descriptions"
    )
