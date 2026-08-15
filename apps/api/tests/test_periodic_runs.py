from metaforge_api.infrastructure.periodic_runs import _REGISTRY, register_run


def test_register_run_adds_to_registry():
    @register_run("test_run_type_unique_1")
    async def handler(session, **kwargs):
        return {"ok": True}

    assert _REGISTRY["test_run_type_unique_1"] is handler
    del _REGISTRY["test_run_type_unique_1"]


def test_register_run_returns_original_function_unchanged():
    async def handler(session, **kwargs):
        return {}

    decorated = register_run("test_run_type_unique_2")(handler)
    assert decorated is handler
    del _REGISTRY["test_run_type_unique_2"]
