"""The only way the agents can change Run:ai.

The model gives a project and a GPU number. This function runs Run:ai MCP's dry run, shows a person the
quota change and the BNK rate limit it implies, and sends the real update with confirm=true only when that
person types "yes". The model never sees a confirm argument, so it can't approve its own change.
"""
import json
import re

from pydantic import Field

from nat.builder.builder import Builder
from nat.builder.context import Context
from nat.builder.function_info import FunctionInfo
from nat.cli.register_workflow import register_function
from nat.data_models.function import FunctionBaseConfig
from nat.data_models.interactive import HumanPromptText


class ApprovedQuotaChangeConfig(FunctionBaseConfig, name="approved_quota_change"):
    runai_group: str = Field(description="Function group name of the Run:ai MCP client")
    projects: list[str] = Field(description="Run:ai projects the agents may change; any other is refused")
    node_pool: str = Field(default="default", description="Node pool whose GPU quota is changed")
    rps_per_gpu: float = Field(default=20.0, description="BNK requests/s per deserved GPU (tenancy controller policy)")
    max_gpu: float = Field(default=4.0, description="Largest GPU quota the agents may propose")
    gpu_step: float = Field(default=0.5, description="GPU quota must be a whole number of these steps")


def _gpu(snapshot: dict, pool: str) -> float:
    for line in snapshot.get("quota", []):
        if line.get("nodePoolName") == pool:
            return float(line.get("gpuDeserved", 0))
    return 0.0


def _parse(result) -> dict:
    return json.loads(result) if isinstance(result, str) else result


@register_function(config_type=ApprovedQuotaChangeConfig)
async def approved_quota_change(config: ApprovedQuotaChangeConfig, builder: Builder):
    group = await builder.get_function_group(config.runai_group)
    functions = await group.get_all_functions()
    manage = next(f for name, f in functions.items() if name.endswith("manage_org_unit"))

    async def _run(project: str, gpu_deserved: float) -> str:
        """Ask a person to approve setting a Run:ai project's deserved GPU quota. Runs Run:ai's dry run
        first and applies the change only if the person approves. Returns what happened."""
        if project not in config.projects:
            return f"Refused: the agents may only change {', '.join(config.projects)}, not {project}."
        if not 0 < gpu_deserved <= config.max_gpu:
            return f"Refused: GPU quota must be above 0 and at most {config.max_gpu:g}, got {gpu_deserved:g}."
        if abs(gpu_deserved / config.gpu_step - round(gpu_deserved / config.gpu_step)) > 1e-9:
            return (f"Refused: GPU quota must be in steps of {config.gpu_step:g} GPU, got {gpu_deserved:g}. "
                    f"Propose the next step up that covers the traffic.")

        args = {"action": "update", "orgType": "project", "name": project,
                "spec": {"quota": [{"nodePoolName": config.node_pool, "gpuDeserved": gpu_deserved}]}}
        try:
            preview = _parse(await manage.acall_invoke(**args, dryRun=True))
        except Exception as e:  # Run:ai refused the dry run (over the department quota, unknown project)
            return f"Run:ai refused the dry run, nothing was changed: {e}"
        before, after = _gpu(preview["before"], config.node_pool), _gpu(preview["after"], config.node_pool)

        # The question has to stand out from the agents' trace scrolling past it, so frame it.
        rule = "=" * 72
        text = (f"\n\n{rule}\n  YOUR APPROVAL IS NEEDED\n{rule}\n"
                f"Run:ai dry run for project {project}: GPU quota {before:g} -> {after:g} "
                f"(BNK limit {before * config.rps_per_gpu:g} -> {after * config.rps_per_gpu:g} req/s). "
                f"Approve this change? Type yes or no.\n{rule}\n> ")
        manager = Context.get().user_interaction_manager
        response = await manager.prompt_user_input(HumanPromptText(text=text, required=True, placeholder="yes or no"))
        if not re.fullmatch(r"yes", response.content.text.strip().lower()):
            return f"Declined by the operator. Project {project} stays at {before:g} GPU. Do not retry."

        applied = _parse(await manage.acall_invoke(**args, confirm=True))
        return f"Applied: project {project} GPU quota {before:g} -> {_gpu(applied['after'], config.node_pool):g}."

    yield FunctionInfo.from_fn(_run, description=_run.__doc__)
