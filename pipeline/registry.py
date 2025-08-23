# pipeline/registry.py
PIPELINE_REGISTRY = {}

def register(name):
    def decorator(cls):
        PIPELINE_REGISTRY[name] = cls
        return cls
    return decorator

def create_step(name, global_config, params):
    cls = PIPELINE_REGISTRY.get(name)
    
    if cls is None:
        raise ValueError(f"Unknown step: {name}")
    
    step = cls(global_config, **params)
    step.name = name
    return step#cls(global_config, **params)

