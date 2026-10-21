"""FIXED selects approved prompts through the same canonical controller."""


async def run_fixed(config, scenario, adapter, store, *, run_id, checker, **kwargs):
    from .controller import execute_run

    if config["method"] != "FIXED":
        raise ValueError("FIXED configuration required")
    return await execute_run(run_id, config, scenario, adapter, store, checker, **kwargs)
